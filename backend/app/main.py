import csv
import hashlib
import hmac
import io
import json
import logging
import mimetypes
import platform
from importlib.metadata import version
import secrets
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from contextlib import asynccontextmanager

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Request, Response, Depends, UploadFile, File, Form, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError as DatabaseIntegrityError
from starlette.formparsers import MultiPartParser
from starlette.exceptions import HTTPException

from .config import Settings
from .crypto import Crypto, ALGORITHMS, ARC4_DROP, IntegrityError, canonical
from .db import database, users, sessions, items, versions, benchmarks, downloads, limits
from .schemas import (Credentials, Registration, PersonalFields, Decrypt, BenchmarkInput,
                      DownloadInput, DownloadResults, Algorithm, Category)

PREFIX = '/api/v1'
EXTENSIONS = {'identity': ['jpg', 'jpeg', 'png'], 'document': ['pdf', 'doc', 'docx', 'xls', 'xlsx'], 'video': ['mp4']}
logger = logging.getLogger('veltrix')

class ApiFailure(Exception):
    def __init__(self, status, code, message, fields=None):
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}

def failure(status, code, message, fields=None):
    return JSONResponse({'error': {'code': code, 'message': message,
        'field_errors': fields or {}, 'request_id': str(uuid.uuid4())}}, status_code=status,
        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

def now():
    return datetime.now(timezone.utc).isoformat()

def identifier():
    return str(uuid.uuid4())

class BodyLimit:
    """Bound body before multipart parsing; never spool plaintext uploads to disk."""
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] in ('GET', 'HEAD'):
            return await self.app(scope, receive, send)
        limit = self.max_bytes if scope['path'] == PREFIX + '/vault/files' else 128_000
        chunks, length = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            length += len(chunk)
            if length > limit:
                return await failure(413, 'FILE_TOO_LARGE', 'Ukuran permintaan melebihi batas.')(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)

def create_app(settings: Settings):
    if settings.database_url.startswith('sqlite:///'):
        db_path = settings.database_url.removeprefix('sqlite:///')
        if db_path != ':memory:':
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = database(settings.database_url)
    crypto = Crypto(settings.master_key)
    passwords = PasswordHasher()
    dummy_hash = passwords.hash(secrets.token_urlsafe(24))
    MultiPartParser.spool_max_size = settings.max_file_bytes + 65_536

    @asynccontextmanager
    async def lifespan(_):
        yield
        engine.dispose()
    app = FastAPI(title='VELTRIX API', version='1.0.0', lifespan=lifespan)
    app.state.engine, app.state.crypto = engine, crypto
    app.add_middleware(BodyLimit, max_bytes=settings.max_file_bytes + 65_536)

    def csrf_valid(token):
        try:
            nonce, expiry, signature = token.split('.')
            expected = hmac.digest(settings.master_key, ('csrf:' + nonce + '.' + expiry).encode(), 'sha256').hex()
            return int(expiry) > time.time() and hmac.compare_digest(expected, signature)
        except (ValueError, AttributeError):
            return False

    @app.middleware('http')
    async def guards(request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            token = request.cookies.get('veltrix_csrf', '')
            if ((origin and origin not in settings.allowed_origins)
                or request.headers.get('sec-fetch-site') == 'cross-site'
                or not token or not hmac.compare_digest(token, request.headers.get('x-csrf-token', ''))
                or not csrf_valid(token)):
                return failure(403, 'CSRF_INVALID', 'Sesi form tidak valid. Muat ulang halaman.')
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.exception_handler(ApiFailure)
    async def api_error(_, exc):
        return failure(exc.status, exc.code, exc.message, exc.fields)
    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        fields = {}
        for error in exc.errors():
            key = str(error['loc'][-1])
            fields.setdefault(key, []).append(error['msg'])
        return failure(422, 'VALIDATION_ERROR', 'Periksa data yang dimasukkan.', fields)
    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return failure(exc.status_code, 'RESOURCE_NOT_FOUND' if exc.status_code == 404 else 'REQUEST_FAILED', str(exc.detail))
    @app.exception_handler(IntegrityError)
    async def crypto_error(_, exc):
        return failure(409, 'INTEGRITY_FAILED', 'Integritas data gagal diperiksa. Data tidak dapat dibuka.')
    @app.exception_handler(Exception)
    async def internal_error(_, exc):
        logger.error('Request failed: %s', type(exc).__name__)
        return failure(500, 'INTERNAL_ERROR', 'Terjadi kesalahan pada server.')

    def user(request: Request):
        token = request.cookies.get('veltrix_session', '')
        digest = hashlib.sha256(token.encode()).hexdigest()
        with engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.expires < time.time()))
            row = connection.execute(select(users.c.id, users.c.username).join(sessions, users.c.id == sessions.c.user_id)
                .where(sessions.c.token_hash == digest, sessions.c.expires > time.time())).mappings().first()
        if row is None:
            raise ApiFailure(401, 'SESSION_EXPIRED', 'Sesi berakhir. Silakan masuk kembali.')
        return dict(row)

    def rate_limit(label, subject, count, seconds):
        bucket = hmac.digest(settings.master_key, (label + ':' + subject).encode(), 'sha256').hex()
        timestamp = time.time()
        with engine.begin() as connection:
            connection.execute(delete(limits).where(limits.c.window < timestamp - 3600))
            # Insert race is handled by retrying with the existing row.
            row = connection.execute(select(limits).where(limits.c.bucket == bucket).with_for_update()).mappings().first()
            if row is None:
                try:
                    with connection.begin_nested():
                        connection.execute(insert(limits).values(bucket=bucket, window=timestamp, count=0))
                except DatabaseIntegrityError:
                    pass
            connection.execute(update(limits).where(limits.c.bucket == bucket, limits.c.window < timestamp - seconds)
                .values(window=timestamp, count=0))
            connection.execute(update(limits).where(limits.c.bucket == bucket).values(count=limits.c.count + 1))
            total = connection.execute(select(limits.c.count).where(limits.c.bucket == bucket)).scalar_one()
        if total > count:
            raise ApiFailure(429, 'RATE_LIMITED', 'Terlalu banyak permintaan. Coba lagi nanti.')

    def owned(connection, item_id, owner, kind=None):
        clause = [items.c.id == item_id, items.c.user_id == owner]
        if kind:
            clause.append(items.c.kind == kind)
        row = connection.execute(select(items).where(*clause)).mappings().first()
        if row is None:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Data tidak ditemukan atau tidak dapat diakses.')
        return row

    def item_metadata(row):
        return json.loads(crypto.decrypt(row['metadata_cipher'], 'AES', row['id'] + ':metadata'))

    def present(connection, row):
        stored = connection.execute(select(versions).where(versions.c.item_id == row['id'])).mappings().all()
        cipher_versions = [crypto.version(next(v['envelope'] for v in stored if v['algorithm'] == a), a) for a in ALGORITHMS]
        if row['kind'] == 'personal_data':
            return {'id': row['id'], 'updated_at': row['created_at'], 'status': 'ready', 'versions': cipher_versions}
        result = item_metadata(row)
        return {**result, 'id': row['id'], 'category': row['category'], 'created_at': row['created_at'],
                'status': 'ready', 'versions': cipher_versions,
                'total_stored_bytes': sum(v['stored_bytes'] for v in cipher_versions)}

    def plaintext(connection, row, algorithm='AES'):
        envelope = connection.execute(select(versions.c.envelope).where(versions.c.item_id == row['id'], versions.c.algorithm == algorithm)).scalar_one()
        return crypto.decrypt(envelope, algorithm, row['id'])

    def persist_item(connection, owner, kind, data, meta, category=None, item_id=None):
        item_id = item_id or identifier()
        encrypted = [(a, crypto.encrypt(data, a, item_id)) for a in ALGORITHMS]
        values = dict(user_id=owner, kind=kind, category=category, created_at=now(),
                      profile_slot=owner if kind == 'personal_data' else None,
                      metadata_cipher=crypto.encrypt(canonical(meta), 'AES', item_id + ':metadata'))
        old = connection.execute(select(items.c.id).where(items.c.id == item_id)).first()
        if old:
            connection.execute(update(items).where(items.c.id == item_id).values(**values))
            connection.execute(delete(versions).where(versions.c.item_id == item_id))
        else:
            connection.execute(insert(items).values(id=item_id, **values))
        connection.execute(insert(versions), [{'item_id': item_id, 'algorithm': a, 'envelope': value} for a, value in encrypted])
        return present(connection, owned(connection, item_id, owner))

    def csv_response(rows, filename):
        buffer = io.StringIO(newline='')
        writer = csv.writer(buffer)
        for row in rows:
            # Neutralize spreadsheet formula injection in user-supplied cells.
            writer.writerow(["'" + cell if isinstance(cell, str) and cell.startswith(('=', '+', '-', '@', '\t', '\r')) else cell for cell in row])
        return Response(buffer.getvalue(), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    @app.get(PREFIX + '/health')
    def health():
        with engine.connect() as connection:
            connection.execute(select(users.c.id).limit(1))
        return {'status': 'ok'}
    @app.get(PREFIX + '/capabilities')
    def capabilities():
        return {'max_file_bytes': settings.max_file_bytes, 'supported_extensions': sum(EXTENSIONS.values(), []),
                'min_repetitions': 10, 'max_repetitions': 30}
    @app.get(PREFIX + '/auth/csrf')
    def csrf(request: Request, response: Response):
        token = request.cookies.get('veltrix_csrf', '')
        if not csrf_valid(token):
            nonce, expiry = secrets.token_urlsafe(32), str(int(time.time()) + 86400)
            content = nonce + '.' + expiry
            token = content + '.' + hmac.digest(settings.master_key, ('csrf:' + content).encode(), 'sha256').hex()
        response.set_cookie('veltrix_csrf', token, max_age=86400, httponly=True,
                            secure=settings.secure_cookie, samesite='strict', path='/')
        return {'token': token}
    @app.post(PREFIX + '/auth/register', status_code=201)
    def register(body: Registration, request: Request):
        rate_limit('register', request.client.host if request.client else 'unknown', 10, 300)
        account = {'id': identifier(), 'username': body.username}
        try:
            with engine.begin() as connection:
                connection.execute(insert(users).values(**account, password_hash=passwords.hash(body.password)))
        except DatabaseIntegrityError:
            raise ApiFailure(409, 'USERNAME_TAKEN', 'Username sudah digunakan.', {'username': ['Pilih username lain.']})
        return account
    @app.post(PREFIX + '/auth/login')
    def login(body: Credentials, request: Request, response: Response):
        rate_limit('login-ip', request.client.host if request.client else 'unknown', 30, 300)
        rate_limit('login-user', body.username, 10, 300)
        with engine.begin() as connection:
            row = connection.execute(select(users).where(users.c.username == body.username)).mappings().first()
            try:
                passwords.verify(row['password_hash'] if row else dummy_hash, body.password)
            except (VerificationError, InvalidHashError):
                raise ApiFailure(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.')
            if row is None:
                raise ApiFailure(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.')
            if passwords.check_needs_rehash(row['password_hash']):
                connection.execute(update(users).where(users.c.id == row['id']).values(password_hash=passwords.hash(body.password)))
            old = request.cookies.get('veltrix_session', '')
            connection.execute(delete(sessions).where(sessions.c.token_hash == hashlib.sha256(old.encode()).hexdigest()))
            token = secrets.token_urlsafe(32)
            connection.execute(insert(sessions).values(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=row['id'], expires=time.time() + settings.session_seconds))
        response.set_cookie('veltrix_session', token, max_age=settings.session_seconds,
                            httponly=True, secure=settings.secure_cookie, samesite='lax', path='/')
        return {'id': row['id'], 'username': row['username']}
    @app.get(PREFIX + '/auth/me')
    def me(account=Depends(user)):
        return account
    @app.post(PREFIX + '/auth/logout', status_code=204)
    def logout(request: Request):
        token = request.cookies.get('veltrix_session', '')
        with engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == hashlib.sha256(token.encode()).hexdigest()))
        response = Response(status_code=204)
        response.delete_cookie('veltrix_session', path='/')
        return response

    @app.get(PREFIX + '/vault/summary')
    def summary(account=Depends(user)):
        with engine.connect() as connection:
            owned_items = connection.execute(select(items).where(items.c.user_id == account['id'])).mappings().all()
            file_items = [present(connection, row) for row in owned_items if row['kind'] == 'file']
        return {'file_count': len(file_items), 'original_bytes': sum(x['original_bytes'] for x in file_items),
                'stored_bytes': sum(x['total_stored_bytes'] for x in file_items),
                'personal_data_exists': any(row['kind'] == 'personal_data' for row in owned_items)}
    @app.get(PREFIX + '/vault/files')
    def list_files(category: Category | None = None, search: str = Query('', max_length=255),
                   page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), account=Depends(user)):
        with engine.connect() as connection:
            clause = [items.c.user_id == account['id'], items.c.kind == 'file']
            if category:
                clause.append(items.c.category == category)
            rows = connection.execute(select(items).where(*clause).order_by(items.c.created_at.desc())).mappings().all()
            # Filenames are encrypted at rest; search only after owner filtering.
            matches = [present(connection, row) for row in rows if search.casefold() in item_metadata(row)['display_name'].casefold()]
        start = (page - 1) * page_size
        return {'items': matches[start:start+page_size], 'total': len(matches), 'page': page, 'page_size': page_size}
    @app.post(PREFIX + '/vault/files', status_code=201)
    def upload(file: UploadFile = File(...), category: Category = Form(...), account=Depends(user)):
        filename = (file.filename or '').replace('\\', '/').split('/')[-1]
        filename = ''.join(c for c in filename if ord(c) >= 32 and ord(c) != 127)[:255]
        extension = filename.rsplit('.', 1)[-1].lower()
        if extension not in EXTENSIONS[category]:
            raise ApiFailure(415, 'UNSUPPORTED_FILE_TYPE', 'Format file tidak sesuai kategori.')
        try:
            data = file.file.read(settings.max_file_bytes + 1)
        finally:
            file.file.close()
        if len(data) > settings.max_file_bytes:
            raise ApiFailure(413, 'FILE_TOO_LARGE', 'Ukuran file melebihi batas 25 MB.')
        if not data:
            raise ApiFailure(422, 'VALIDATION_ERROR', 'File kosong tidak dapat disimpan.')
        # Uploaded bytes are downloads only, never served as executable inline content.
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        with engine.begin() as connection:
            return persist_item(connection, account['id'], 'file', data,
                {'display_name': filename, 'mime_type': mime_type, 'original_bytes': len(data)}, category)
    @app.get(PREFIX + '/vault/files/{item_id}')
    def file_detail(item_id: str, account=Depends(user)):
        with engine.connect() as connection:
            return present(connection, owned(connection, item_id, account['id'], 'file'))
    @app.get(PREFIX + '/vault/files/{item_id}/download')
    def download(item_id: str, algorithm: Algorithm, account=Depends(user)):
        with engine.connect() as connection:
            row = owned(connection, item_id, account['id'], 'file')
            meta = item_metadata(row)
            data = plaintext(connection, row, algorithm)
        return Response(data, media_type=meta['mime_type'], headers={
            'Content-Disposition': "attachment; filename=\"download\"; filename*=UTF-8''" + quote(meta['display_name'], safe='')})
    @app.delete(PREFIX + '/vault/files/{item_id}', status_code=204)
    def delete_file(item_id: str, account=Depends(user)):
        with engine.begin() as connection:
            owned(connection, item_id, account['id'], 'file')
            connection.execute(delete(items).where(items.c.id == item_id))
        return Response(status_code=204)

    @app.get(PREFIX + '/vault/personal-data')
    def profile(account=Depends(user)):
        with engine.connect() as connection:
            row = connection.execute(select(items).where(items.c.profile_slot == account['id'])).mappings().first()
            return present(connection, row) if row else None
    @app.post(PREFIX + '/vault/personal-data', status_code=201)
    def create_profile(body: PersonalFields, account=Depends(user)):
        try:
            with engine.begin() as connection:
                if connection.execute(select(items.c.id).where(items.c.profile_slot == account['id'])).first():
                    raise ApiFailure(409, 'PROFILE_EXISTS', 'Profil sudah ada. Gunakan aksi edit.')
                return persist_item(connection, account['id'], 'personal_data', canonical(body.model_dump()), {})
        except DatabaseIntegrityError:
            raise ApiFailure(409, 'PROFILE_EXISTS', 'Profil sudah ada. Gunakan aksi edit.')
    @app.put(PREFIX + '/vault/personal-data/{item_id}')
    def update_profile(item_id: str, body: PersonalFields, account=Depends(user)):
        with engine.begin() as connection:
            owned(connection, item_id, account['id'], 'personal_data')
            return persist_item(connection, account['id'], 'personal_data', canonical(body.model_dump()), {}, item_id=item_id)
    @app.post(PREFIX + '/vault/personal-data/{item_id}/decrypt')
    def reveal(item_id: str, body: Decrypt, account=Depends(user)):
        with engine.connect() as connection:
            row = owned(connection, item_id, account['id'], 'personal_data')
            return json.loads(plaintext(connection, row, body.algorithm))
    @app.delete(PREFIX + '/vault/personal-data/{item_id}', status_code=204)
    def delete_profile(item_id: str, account=Depends(user)):
        with engine.begin() as connection:
            owned(connection, item_id, account['id'], 'personal_data')
            connection.execute(delete(items).where(items.c.id == item_id))
        return Response(status_code=204)

    def saved_result(table, result_id, owner, connection):
        result = connection.execute(select(table.c.result).where(table.c.id == result_id, table.c.user_id == owner)).scalar_one_or_none()
        if result is None:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Data tidak ditemukan atau tidak dapat diakses.')
        return json.loads(result)

    @app.post(PREFIX + '/benchmarks', status_code=201)
    def benchmark(body: BenchmarkInput, account=Depends(user)):
        rate_limit('benchmark', account['id'], 5, 60)
        with engine.connect() as connection:
            row = owned(connection, body.source.id, account['id'], body.source.type)
            data = plaintext(connection, row)
        samples, orders = [], []
        for repetition in range(-body.warmups + 1, body.repetitions + 1):
            algorithms = list(ALGORITHMS)
            secrets.SystemRandom().shuffle(algorithms)
            if repetition > 0:
                orders.append(','.join(algorithms))
            for algorithm in algorithms:
                sample = crypto.sample(data, algorithm, body.source.id, repetition)
                if repetition > 0:
                    samples.append(sample)
        summaries = []
        for algorithm in ALGORITHMS:
            rows = [s for s in samples if s['algorithm'] == algorithm]
            entry = {'algorithm': algorithm, 'round_trip_successes': sum(s['round_trip_ok'] for s in rows), 'measured_runs': len(rows)}
            for mode in ('encrypt', 'decrypt'):
                values = [s[mode + '_ns'] for s in rows]
                entry.update({f'mean_{mode}_ns': statistics.mean(values), f'median_{mode}_ns': statistics.median(values), f'stddev_{mode}_ns': statistics.stdev(values)})
            summaries.append(entry)
        result = {'id': identifier(), 'source': body.source.model_dump(), 'input_bytes': len(data),
            'repetitions': body.repetitions, 'warmups': body.warmups, 'created_at': now(),
            'environment': {'mode': 'LIVE', 'python': platform.python_version(), 'platform': platform.platform(),
                'timer': 'time.perf_counter_ns', 'timer_resolution_seconds': str(time.get_clock_info('perf_counter').resolution),
                'storage': engine.dialect.name, 'pycryptodome': version('pycryptodome'),
                'machine': platform.machine(), 'processor': platform.processor() or 'not reported', 'algorithms': f'AES-256-CBC, RC4-256 drop={ARC4_DROP}, DES-CBC',
                'core_scope': 'cipher construction + padding/encryption or decryption/unpadding; excludes random, HKDF, HMAC and storage',
                'integrity_scope': 'envelope encoding + HMAC creation + verification + verification HKDF; outside core',
                'execution_order': json.dumps(orders), 'stddev': 'sample (n-1)'},
            'methodology_version': 'veltrix-crypto-v1', 'samples': samples, 'summary': summaries}
        with engine.begin() as connection:
            connection.execute(insert(benchmarks).values(id=result['id'], user_id=account['id'], result=json.dumps(result)))
        return result
    @app.get(PREFIX + '/benchmarks')
    def history(account=Depends(user)):
        with engine.connect() as connection:
            results = [json.loads(row) for row in connection.execute(select(benchmarks.c.result).where(benchmarks.c.user_id == account['id'])).scalars()]
        return sorted(results, key=lambda x: x['created_at'], reverse=True)
    @app.get(PREFIX + '/benchmarks/{result_id}')
    def result(result_id: str, account=Depends(user)):
        with engine.connect() as connection:
            return saved_result(benchmarks, result_id, account['id'], connection)
    @app.get(PREFIX + '/benchmarks/{result_id}/export')
    def export_benchmark(result_id: str, account=Depends(user)):
        with engine.connect() as connection:
            result = saved_result(benchmarks, result_id, account['id'], connection)
        keys = ['algorithm', 'repetition', 'encrypt_ns', 'decrypt_ns', 'integrity_ns', 'correctness_ns', 'ciphertext_bytes', 'stored_bytes', 'round_trip_ok']
        return csv_response([['mode', 'method', 'input_bytes', *keys], *[
            ['LIVE', result['methodology_version'], result['input_bytes'], *[s[k] for k in keys]] for s in result['samples']]], 'veltrix-crypto.csv')
    @app.post(PREFIX + '/download-tests', status_code=201)
    def create_download_test(body: DownloadInput, account=Depends(user)):
        with engine.begin() as connection:
            owned(connection, body.file_id, account['id'], 'file')
            result = {'id': identifier(), **body.model_dump(), 'attempts': [], 'browser': ''}
            connection.execute(insert(downloads).values(id=result['id'], user_id=account['id'], result=json.dumps(result)))
        return {'id': result['id']}
    @app.post(PREFIX + '/download-tests/{result_id}/results')
    def save_download_test(result_id: str, body: DownloadResults, account=Depends(user)):
        with engine.begin() as connection:
            result = saved_result(downloads, result_id, account['id'], connection)
            pairs = [(a.algorithm, a.repetition) for a in body.attempts]
            if len(pairs) != len(set(pairs)) or any(a.repetition > result['repetitions'] for a in body.attempts):
                raise ApiFailure(422, 'VALIDATION_ERROR', 'Sample download duplikat atau di luar batas.')
            result.update(body.model_dump())
            connection.execute(update(downloads).where(downloads.c.id == result_id).values(result=json.dumps(result)))
        return {'id': result_id}
    @app.get(PREFIX + '/download-tests/{result_id}/export')
    def export_download(result_id: str, account=Depends(user)):
        with engine.connect() as connection:
            result = saved_result(downloads, result_id, account['id'], connection)
        keys = ['algorithm', 'repetition', 'elapsed_ms', 'received_bytes', 'success', 'error_code']
        return csv_response([['mode', *keys], *[['CLIENT-MEASURED-LIVE', *[s.get(k) if s.get(k) is not None else '' for k in keys]] for s in result['attempts']]], 'veltrix-download.csv')
    return app
