import csv
import hashlib
import hmac
import io
import json
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import quote
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Request, Response, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartParser
from starlette.datastructures import UploadFile
from .config import Settings
from .db import (database, users, sessions, applications, assignments, objects, profiles,
                 evidence, events, limits, security_log, lab_runs, lab_lock)
from .crypto import Envelope, IntegrityFailure, canonical
from .schemas import Model, Credentials, Registration, SaveProfile, Action, Assignment, LabInput
from .validation import validate, InvalidFile, RULES

PREFIX = '/api/v1'
EDITABLE = ('DRAFT', 'NEEDS_REVISION')
logger = logging.getLogger('veltrix.kyc')

def uid():
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc).isoformat()

class ApiFailure(Exception):
    def __init__(self, status, code, message, fields=None):
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}

def failure(status, code, message, fields=None):
    return JSONResponse({'error': {'code': code, 'message': message, 'field_errors': fields or {}, 'request_id': uid()}},
        status_code=status, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', **({'Retry-After': '60'} if status == 429 else {})})

class BodyLimit:
    """Bound every stream before parsing; only bounded RAM holds incoming plaintext."""
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] in ('GET', 'HEAD', 'OPTIONS'):
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        if headers.get(b'content-encoding', b'identity') != b'identity':
            return await failure(415, 'UNSUPPORTED_ENCODING', 'Content-Encoding tidak didukung.')(scope, receive, send)
        cap = self.max_bytes if scope['path'].endswith('/evidence') else 128 * 1024
        try:
            declared = int(headers.get(b'content-length', b'0'))
            if declared < 0:
                raise ValueError()
        except ValueError:
            return await failure(400, 'INVALID_REQUEST', 'Content-Length tidak valid.')(scope, receive, send)
        if declared > cap:
            return await failure(413, 'REQUEST_TOO_LARGE', 'Ukuran permintaan melebihi batas.')(scope, receive, send)
        chunks, length = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            length += len(chunk)
            if length > cap:
                return await failure(413, 'REQUEST_TOO_LARGE', 'Ukuran permintaan melebihi batas.')(scope, receive, send)
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
    engine = database(settings.database_url)
    envelope = Envelope(settings.kek)
    passwords = PasswordHasher()
    dummy_hash = passwords.hash(secrets.token_urlsafe(32))
    # Request cap is strictly lower than spool threshold: no upload rollover to disk.
    MultiPartParser.spool_max_size = settings.max_request_bytes + 1

    @asynccontextmanager
    async def lifespan(_):
        # Fail early for missing schema or wrong KEK; never generate replacement keys here.
        from .provision import check_keys
        check_keys(engine, settings)
        yield
        engine.dispose()

    app = FastAPI(title='VELTRIX BankKYC API', version='2.0.0', lifespan=lifespan)
    app.state.engine, app.state.envelope, app.state.settings = engine, envelope, settings
    app.add_middleware(BodyLimit, max_bytes=settings.max_request_bytes)

    def audit(action, actor_id=None, resource_id=None):
        try:
            with engine.begin() as connection:
                connection.execute(insert(security_log).values(id=uid(), at=now(), actor_id=actor_id, action=action, resource_id=resource_id))
        except SQLAlchemyError:
            logger.error('Security audit storage unavailable')

    def csrf_valid(token):
        try:
            nonce, expiry, signature = token.split('.')
            expected = hmac.digest(settings.auth_secret, ('csrf:' + nonce + '.' + expiry).encode(), 'sha256').hex()
            return int(expiry) > time.time() and hmac.compare_digest(expected, signature)
        except (ValueError, AttributeError):
            return False

    def new_csrf(response):
        content = secrets.token_urlsafe(32) + '.' + str(int(time.time()) + 86400)
        token = content + '.' + hmac.digest(settings.auth_secret, ('csrf:' + content).encode(), 'sha256').hex()
        response.set_cookie('veltrix_csrf', token, max_age=86400, httponly=True, secure=settings.secure_cookie, samesite='strict', path='/')
        return token

    @app.middleware('http')
    async def guards(request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            token = request.cookies.get('veltrix_csrf', '')
            if ((origin and origin not in settings.allowed_origins) or request.headers.get('sec-fetch-site') == 'cross-site'
                or not token or not hmac.compare_digest(token, request.headers.get('x-csrf-token', '')) or not csrf_valid(token)):
                audit('csrf_denied')
                return failure(403, 'CSRF_INVALID', 'Sesi form tidak valid. Muat ulang halaman.')
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.exception_handler(ApiFailure)
    async def api_error(request, exc):
        if exc.status in (403, 404):
            audit('access_denied', getattr(request.state, 'actor_id', None))
        return failure(exc.status, exc.code, exc.message, exc.fields)
    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        fields = {}
        for error in exc.errors():
            fields.setdefault(str(error['loc'][-1]), []).append(error['msg'])
        return failure(422, 'VALIDATION_ERROR', 'Periksa data yang dimasukkan.', fields)
    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        return failure(exc.status_code, 'RESOURCE_NOT_FOUND' if exc.status_code == 404 else 'REQUEST_FAILED', str(exc.detail))
    @app.exception_handler(IntegrityFailure)
    async def integrity_error(request, _):
        audit('integrity_failed', getattr(request.state, 'actor_id', None))
        return failure(500, 'INTEGRITY_CHECK_FAILED', 'Integritas data gagal diperiksa. Berkas belum dapat dipulihkan.')
    @app.exception_handler(OperationalError)
    async def database_error(_, exc):
        if engine.dialect.name == 'sqlite' and 'locked' in str(exc).lower():
            return failure(409, 'VERSION_CONFLICT', 'Data sedang berubah. Muat ulang dan ulangi.')
        return failure(503, 'STORAGE_UNAVAILABLE', 'Database belum dapat diakses.')
    @app.exception_handler(Exception)
    async def internal_error(_, exc):
        logger.error('Request failed: %s', type(exc).__name__)
        return failure(500, 'INTERNAL_ERROR', 'Terjadi kesalahan pada server.')

    def user(request: Request):
        digest = hashlib.sha256(request.cookies.get('veltrix_session', '').encode()).hexdigest()
        with engine.begin() as connection:
            row = connection.execute(select(users).join(sessions, users.c.id == sessions.c.user_id)
                .where(sessions.c.token_hash == digest, sessions.c.expires_at > time.time(), users.c.is_active.is_(True))).mappings().first()
        if row is None:
            raise ApiFailure(401, 'SESSION_EXPIRED', 'Sesi berakhir. Silakan masuk kembali.')
        request.state.actor_id = row['id']
        return {k: row[k] for k in ('id', 'username', 'display_name', 'role')}

    def role(account, *allowed):
        if account['role'] not in allowed:
            raise ApiFailure(403, 'ROLE_FORBIDDEN', 'Peran ini tidak memiliki akses ke tindakan tersebut.')

    def rate_limit(label, subject, cap, seconds):
        bucket = hmac.digest(settings.auth_secret, (label + ':' + subject).encode(), 'sha256').hex()
        timestamp = time.time()
        with engine.begin() as connection:
            row = connection.execute(select(limits).where(limits.c.bucket == bucket).with_for_update()).mappings().first()
            if row is None:
                try:
                    with connection.begin_nested():
                        connection.execute(insert(limits).values(bucket=bucket, window=timestamp, count=0))
                except IntegrityError:
                    pass
            connection.execute(update(limits).where(limits.c.bucket == bucket, limits.c.window < timestamp-seconds).values(window=timestamp, count=0))
            connection.execute(update(limits).where(limits.c.bucket == bucket).values(count=limits.c.count+1))
            total = connection.execute(select(limits.c.count).where(limits.c.bucket == bucket)).scalar_one()
        if total > cap:
            raise ApiFailure(429, 'RATE_LIMITED', 'Terlalu banyak permintaan. Coba lagi nanti.')

    def case(connection, case_id, account, *, owner=False, admin=False, lock=False):
        query = select(applications).where(applications.c.id == case_id)
        if lock:
            query = query.with_for_update()
        row = connection.execute(query).mappings().first()
        visible = row is not None and account['role'] == 'applicant' and row['owner_id'] == account['id']
        if row is not None and not owner:
            if admin and account['role'] == 'admin':
                visible = True
            elif account['role'] == 'reviewer' and row['status'] not in ('DRAFT', 'WITHDRAWN'):
                assigned = connection.execute(select(assignments.c.reviewer_id).where(assignments.c.application_id == case_id)).scalar_one_or_none()
                visible = assigned == account['id']
        if not visible:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Pengajuan tidak ditemukan atau tidak dapat diakses.')
        return dict(row)

    def reserve(connection, row, expected, editable=False):
        if expected != row['version']:
            raise ApiFailure(409, 'VERSION_CONFLICT', 'Pengajuan berubah. Muat ulang sebelum melanjutkan.')
        if editable and row['status'] not in EDITABLE:
            raise ApiFailure(409, 'CASE_READ_ONLY', 'Pengajuan terkunci. Perubahan hanya tersedia saat draf atau revisi.')
        stamp = now()
        changed = connection.execute(update(applications).where(applications.c.id == row['id'], applications.c.version == expected)
            .values(version=expected+1, updated_at=stamp))
        if changed.rowcount != 1:
            raise ApiFailure(409, 'VERSION_CONFLICT', 'Pengajuan berubah. Muat ulang sebelum melanjutkan.')
        row.update(version=expected+1, updated_at=stamp)

    def store_object(connection, row, kind, category, payload_version, payload, private):
        context = dict(id=uid(), application_id=row['id'], owner_id=row['owner_id'], kind=kind,
                       category=category, payload_version=payload_version, key_version=1)
        # Unique wrap nonce constraint + retry: never reuse a KEK nonce.
        for attempt in range(3):
            encrypted = envelope.encrypt(context, payload, private)
            try:
                with connection.begin_nested():
                    connection.execute(insert(objects).values(**context, **encrypted, created_at=now()))
                return context['id']
            except IntegrityError:
                if attempt == 2:
                    raise

    def open_object(connection, object_id, row, *, kind, category, version):
        stored = connection.execute(select(objects).where(objects.c.id == object_id,
            objects.c.application_id == row['id'], objects.c.owner_id == row['owner_id'])).mappings().first()
        if stored is None or stored['kind'] != kind or stored['category'] != category or stored['payload_version'] != version:
            raise IntegrityFailure()
        return envelope.decrypt(stored)

    def add_event(connection, row, account, action, note=None):
        note_id = store_object(connection, row, 'review_note', '', row['version'], note.encode(), {}) if note else None
        connection.execute(insert(events).values(id=uid(), application_id=row['id'], actor_id=account['id'],
            actor_role=account['role'], action=action, at=now(), case_version=row['version'], note_object_id=note_id))

    def present(connection, row, account):
        is_owner = account['role'] == 'applicant' and row['owner_id'] == account['id']
        result = {k: row[k] for k in ('id', 'reference', 'status', 'version', 'created_at', 'updated_at', 'synthetic_acknowledged')}
        result['personal_data_complete'] = connection.execute(select(profiles.c.id).where(profiles.c.application_id == row['id']).limit(1)).first() is not None
        result['evidence'] = []
        for entry in connection.execute(select(evidence).where(evidence.c.application_id == row['id']).order_by(evidence.c.version, evidence.c.created_at)).mappings():
            item = {k: entry[k] for k in ('id', 'category', 'version', 'original_bytes', 'mime_type', 'created_at')}
            item['validation'] = 'format_checked'
            if is_owner:
                meta, _ = open_object(connection, entry['object_id'], row, kind='evidence', category=entry['category'], version=entry['version'])
                item['display_name'] = meta['filename']
            result['evidence'].append(item)
        assigned = connection.execute(select(assignments.c.reviewer_id).where(assignments.c.application_id == row['id'])).scalar_one_or_none()
        if assigned:
            result['assigned_reviewer_id'] = assigned
        result['events'] = []
        for event in connection.execute(select(events).where(events.c.application_id == row['id']).order_by(events.c.case_version)).mappings():
            entry = {k: event[k] for k in ('id', 'at', 'action', 'actor_role')}
            if event['note_object_id'] and account['role'] in ('applicant', 'reviewer'):
                _, payload = open_object(connection, event['note_object_id'], row, kind='review_note', category='', version=event['case_version'])
                entry['note'] = payload.decode()
                result['revision_note'] = entry['note']
            result['events'].append(entry)
        return result

    def latest_profile(connection, row):
        return connection.execute(select(profiles).where(profiles.c.application_id == row['id']).order_by(profiles.c.version.desc()).limit(1)).mappings().first()

    def attachment(payload, filename, mime='application/octet-stream'):
        return Response(payload, media_type=mime, headers={'Content-Disposition': "attachment; filename=\"download\"; filename*=UTF-8''" + quote(filename, safe='')})

    @app.get(PREFIX + '/health')
    def health():
        try:
            with engine.connect() as connection:
                connection.execute(select(users.c.id).limit(1))
        except SQLAlchemyError:
            raise ApiFailure(503, 'STORAGE_UNAVAILABLE', 'Database belum siap. Jalankan migrasi.')
        return {'status': 'ok', 'api': 'bankkyc', 'storage': engine.dialect.name}

    @app.get(PREFIX + '/auth/csrf')
    def csrf(request: Request, response: Response):
        token = request.cookies.get('veltrix_csrf', '')
        return {'token': token if csrf_valid(token) else new_csrf(response)}

    @app.post(PREFIX + '/auth/register', status_code=201)
    def register(body: Registration, request: Request):
        rate_limit('register', request.client.host if request.client else 'unknown', 10, 300)
        account = dict(id=uid(), username=body.username, display_name=body.username, role='applicant')
        try:
            with engine.begin() as connection:
                connection.execute(insert(users).values(**account, password_hash=passwords.hash(body.password), is_active=True, created_at=now()))
        except IntegrityError:
            raise ApiFailure(409, 'USERNAME_TAKEN', 'Username sudah digunakan.', {'username': ['Pilih username lain.']})
        return account

    @app.post(PREFIX + '/auth/login')
    def login(body: Credentials, request: Request, response: Response):
        rate_limit('login-ip', request.client.host if request.client else 'unknown', 30, 300)
        rate_limit('login-name', body.username, 10, 300)
        with engine.begin() as connection:
            row = connection.execute(select(users).where(users.c.username == body.username)).mappings().first()
            try:
                passwords.verify(row['password_hash'] if row else dummy_hash, body.password)
            except (VerificationError, InvalidHashError):
                raise ApiFailure(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.')
            if not row or not row['is_active']:
                raise ApiFailure(401, 'INVALID_CREDENTIALS', 'Username atau password tidak sesuai.')
            if passwords.check_needs_rehash(row['password_hash']):
                connection.execute(update(users).where(users.c.id == row['id']).values(password_hash=passwords.hash(body.password)))
            old = hashlib.sha256(request.cookies.get('veltrix_session', '').encode()).hexdigest()
            connection.execute(delete(sessions).where((sessions.c.token_hash == old) | (sessions.c.expires_at < time.time())))
            token = secrets.token_urlsafe(32)
            connection.execute(insert(sessions).values(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=row['id'], created_at=time.time(), expires_at=time.time()+settings.session_seconds))
        response.set_cookie('veltrix_session', token, max_age=settings.session_seconds, httponly=True,
                            secure=settings.secure_cookie, samesite='lax', path='/')
        new_csrf(response)
        return {k: row[k] for k in ('id', 'username', 'display_name', 'role')}

    @app.get(PREFIX + '/auth/me')
    def me(account=Depends(user)):
        return account

    @app.post(PREFIX + '/auth/logout', status_code=204)
    def logout(request: Request):
        token = hashlib.sha256(request.cookies.get('veltrix_session', '').encode()).hexdigest()
        with engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == token))
        response = Response(status_code=204)
        response.delete_cookie('veltrix_session', path='/')
        response.delete_cookie('veltrix_csrf', path='/')
        return response

    @app.get(PREFIX + '/applications')
    def list_cases(account=Depends(user)):
        role(account, 'applicant', 'reviewer')
        with engine.connect() as connection:
            query = select(applications)
            if account['role'] == 'applicant':
                query = query.where(applications.c.owner_id == account['id'])
            else:
                query = query.join(assignments).where(assignments.c.reviewer_id == account['id'], applications.c.status.not_in(('DRAFT', 'WITHDRAWN')))
            entries = [present(connection, row, account) for row in connection.execute(query.order_by(applications.c.updated_at.desc())).mappings()]
        return {'items': entries, 'total': len(entries)}

    @app.post(PREFIX + '/applications', status_code=201)
    def create_case(body: Model, account=Depends(user)):
        role(account, 'applicant')
        rate_limit('create', account['id'], 20, 60)
        row = dict(id=uid(), reference='VTX-' + datetime.now(timezone.utc).strftime('%Y') + '-' + secrets.token_hex(8).upper(),
            owner_id=account['id'], status='DRAFT', version=1, created_at=now(), updated_at=now(), synthetic_acknowledged=False)
        with engine.begin() as connection:
            if connection.execute(select(func.count()).select_from(applications).where(applications.c.owner_id == account['id'])).scalar_one() >= 100:
                raise ApiFailure(409, 'CAPACITY_REACHED', 'Batas 100 pengajuan per akun tercapai.')
            connection.execute(insert(applications).values(**row))
            add_event(connection, row, account, 'Pengajuan dibuat')
            return present(connection, row, account)

    @app.get(PREFIX + '/applications/{case_id}')
    def case_detail(case_id: str, account=Depends(user)):
        with engine.connect() as connection:
            return present(connection, case(connection, case_id, account), account)

    @app.get(PREFIX + '/applications/{case_id}/personal-data')
    def get_profile(case_id: str, account=Depends(user)):
        with engine.connect() as connection:
            row = case(connection, case_id, account, owner=True)
            entry = latest_profile(connection, row)
            if not entry:
                return {'profile': None}
            _, payload = open_object(connection, entry['object_id'], row, kind='personal_data', category='', version=entry['version'])
            return {'profile': json.loads(payload)}

    @app.put(PREFIX + '/applications/{case_id}/personal-data')
    def save_profile(case_id: str, body: SaveProfile, account=Depends(user)):
        with engine.begin() as connection:
            row = case(connection, case_id, account, owner=True, lock=True)
            reserve(connection, row, body.version, editable=True)
            previous = latest_profile(connection, row)
            payload_version = previous['version'] + 1 if previous else 1
            object_id = store_object(connection, row, 'personal_data', '', payload_version, canonical(body.profile.model_dump()), {'mime_type': 'application/json'})
            connection.execute(insert(profiles).values(id=uid(), application_id=case_id, version=payload_version, object_id=object_id, created_at=now()))
            add_event(connection, row, account, 'Data pribadi diperbarui')
            return present(connection, row, account)

    @app.post(PREFIX + '/applications/{case_id}/evidence', status_code=201, openapi_extra={
        'requestBody': {'required': True, 'content': {'multipart/form-data': {'schema': {
            'type': 'object', 'required': ['category', 'version', 'file'], 'properties': {
                'category': {'type': 'string', 'enum': ['identity', 'document', 'video']},
                'version': {'type': 'integer', 'minimum': 1}, 'file': {'type': 'string', 'format': 'binary'}}}}}}})
    async def upload(case_id: str, request: Request, account=Depends(user)):
        # Ownership and edit scope checked before multipart parsing and repeated in transaction.
        with engine.connect() as connection:
            existing = case(connection, case_id, account, owner=True)
            if existing['status'] not in EDITABLE:
                raise ApiFailure(409, 'CASE_READ_ONLY', 'Pengajuan terkunci.')
        rate_limit('upload', account['id'], 60, 60)
        async with request.form(max_files=1, max_fields=2, max_part_size=2048) as form:
            pairs = list(form.multi_items())
            if len(pairs) != 3 or set(form) != {'category', 'version', 'file'}:
                raise ApiFailure(422, 'INVALID_UPLOAD', 'Kirim tepat satu file, kategori, dan versi.')
            category, file = form['category'], form['file']
            if category not in RULES or not isinstance(file, UploadFile):
                raise ApiFailure(422, 'INVALID_UPLOAD', 'Kategori atau file tidak valid.')
            try:
                text_version = form['version']
                if not isinstance(text_version, str) or not text_version.isascii() or not text_version.isdecimal():
                    raise ValueError()
                expected = int(text_version)
                if expected < 1:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ApiFailure(422, 'VALIDATION_ERROR', 'Versi pengajuan tidak valid.')
            filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
            filename = ''.join(c for c in filename if ord(c) >= 32 and ord(c) != 127)[:255]
            cap = RULES[category][1]
            data = await file.read(cap + 1)
            if len(data) > cap:
                raise ApiFailure(413, 'FILE_TOO_LARGE', 'Ukuran file melebihi batas kategori.')
            try:
                mime = validate(data, filename, category, settings.ffprobe)
            except InvalidFile as exc:
                raise ApiFailure(422, 'INVALID_UPLOAD', str(exc))
            except RuntimeError:
                raise ApiFailure(503, 'VALIDATOR_UNAVAILABLE', 'Pemeriksa video belum terpasang. Pasang FFmpeg/ffprobe.')
            with engine.begin() as connection:
                row = case(connection, case_id, account, owner=True, lock=True)
                reserve(connection, row, expected, editable=True)
                count = connection.execute(select(func.count()).select_from(evidence).where(evidence.c.application_id == case_id)).scalar_one()
                if count >= 100:
                    raise ApiFailure(409, 'CAPACITY_REACHED', 'Batas 100 versi berkas per pengajuan tercapai.')
                payload_version = (connection.execute(select(func.max(evidence.c.version)).where(evidence.c.application_id == case_id, evidence.c.category == category)).scalar_one() or 0) + 1
                object_id = store_object(connection, row, 'evidence', category, payload_version, data, {'filename': filename, 'mime_type': mime})
                connection.execute(insert(evidence).values(id=uid(), application_id=case_id, category=category, version=payload_version,
                    object_id=object_id, original_bytes=len(data), mime_type=mime, created_at=now()))
                add_event(connection, row, account, f'Bukti {category} versi {payload_version} ditambahkan')
                return present(connection, row, account)

    @app.get(PREFIX + '/applications/{case_id}/evidence/{evidence_id}/download')
    def download_evidence(case_id: str, evidence_id: str, account=Depends(user)):
        rate_limit('retrieve', account['id'], 120, 60)
        with engine.connect() as connection:
            row = case(connection, case_id, account, owner=True)
            entry = connection.execute(select(evidence).where(evidence.c.id == evidence_id, evidence.c.application_id == case_id)).mappings().first()
            if not entry:
                raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Berkas tidak ditemukan.')
            meta, data = open_object(connection, entry['object_id'], row, kind='evidence', category=entry['category'], version=entry['version'])
        audit('evidence_download', account['id'], evidence_id)
        return attachment(data, meta['filename'], meta['mime_type'])

    @app.get(PREFIX + '/applications/{case_id}/personal-data/download')
    def download_profile(case_id: str, account=Depends(user)):
        with engine.connect() as connection:
            row = case(connection, case_id, account, owner=True)
            entry = latest_profile(connection, row)
            if not entry:
                raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Profil belum tersedia.')
            _, data = open_object(connection, entry['object_id'], row, kind='personal_data', category='', version=entry['version'])
        audit('profile_download', account['id'], case_id)
        return attachment(data, 'profil-dummy.json')

    @app.post(PREFIX + '/applications/{case_id}/actions')
    def action(case_id: str, body: Action, account=Depends(user)):
        with engine.begin() as connection:
            row = case(connection, case_id, account, lock=True)
            reserve(connection, row, body.version)
            allowed = {}
            if account['role'] == 'applicant':
                if row['status'] == 'DRAFT':
                    allowed = {'submit': 'SUBMITTED', 'withdraw': 'WITHDRAWN'}
                elif row['status'] == 'NEEDS_REVISION':
                    allowed = {'resubmit': 'RESUBMITTED', 'withdraw': 'WITHDRAWN'}
            elif account['role'] == 'reviewer':
                if row['status'] in ('SUBMITTED', 'RESUBMITTED'):
                    allowed = {'start-review': 'UNDER_REVIEW'}
                elif row['status'] == 'UNDER_REVIEW':
                    allowed = {'request-revision': 'NEEDS_REVISION', 'accept': 'ACCEPTED_DEMO', 'reject': 'REJECTED_DEMO'}
            if body.action not in allowed:
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Tindakan tidak tersedia pada status saat ini.')
            if body.action in ('submit', 'resubmit'):
                categories = set(connection.execute(select(evidence.c.category).where(evidence.c.application_id == case_id)).scalars())
                if latest_profile(connection, row) is None or categories != set(RULES) or body.synthetic_acknowledged is not True:
                    raise ApiFailure(422, 'CASE_INCOMPLETE', 'Lengkapi empat kategori dan konfirmasi penggunaan data sintetis.')
                row['synthetic_acknowledged'] = True
            if body.action in ('request-revision', 'reject') and (not body.note or len(body.note.strip()) < 10):
                raise ApiFailure(422, 'NOTE_REQUIRED', 'Tulis catatan operasional 10–500 karakter.')
            row['status'] = allowed[body.action]
            connection.execute(update(applications).where(applications.c.id == case_id).values(status=row['status'], synthetic_acknowledged=row['synthetic_acknowledged']))
            labels = {'submit': 'Pengajuan dikirim', 'resubmit': 'Pengajuan dikirim ulang', 'withdraw': 'Pengajuan ditarik',
                'start-review': 'Tinjauan metadata dimulai', 'request-revision': 'Revisi diminta', 'accept': 'Pengajuan diterima', 'reject': 'Pengajuan ditolak'}
            add_event(connection, row, account, labels[body.action], body.note if body.action in ('request-revision', 'reject') else None)
            return present(connection, row, account)

    @app.get(PREFIX + '/admin/assignments')
    def list_assignments(account=Depends(user)):
        role(account, 'admin')
        with engine.connect() as connection:
            entries = [present(connection, row, account) for row in connection.execute(select(applications)
                .where(applications.c.status.not_in(('DRAFT', 'WITHDRAWN'))).order_by(applications.c.updated_at.desc())).mappings()]
            reviewers = [dict(row) for row in connection.execute(select(users.c.id, users.c.display_name).where(users.c.role == 'reviewer', users.c.is_active.is_(True))).mappings()]
        return {'items': entries, 'reviewers': reviewers}

    @app.put(PREFIX + '/admin/assignments/{case_id}')
    def assign(case_id: str, body: Assignment, account=Depends(user)):
        role(account, 'admin')
        with engine.begin() as connection:
            row = case(connection, case_id, account, admin=True, lock=True)
            reserve(connection, row, body.version)
            if row['status'] not in ('SUBMITTED', 'RESUBMITTED'):
                raise ApiFailure(409, 'ASSIGNMENT_LOCKED', 'Penugasan hanya dapat diubah sebelum tinjauan dimulai.')
            reviewer = connection.execute(select(users.c.id).where(users.c.id == body.reviewer_id, users.c.role == 'reviewer', users.c.is_active.is_(True))).first()
            if not reviewer:
                raise ApiFailure(422, 'INVALID_REVIEWER', 'Pilih reviewer aktif.')
            connection.execute(delete(assignments).where(assignments.c.application_id == case_id))
            connection.execute(insert(assignments).values(application_id=case_id, reviewer_id=body.reviewer_id, assigned_by=account['id'], assigned_at=now()))
            add_event(connection, row, account, 'Reviewer ditugaskan')
            return present(connection, row, account)

    def lab_result(connection, result_id, account):
        result = connection.execute(select(lab_runs.c.result).where(lab_runs.c.id == result_id, lab_runs.c.user_id == account['id'])).scalar_one_or_none()
        if result is None:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Hasil lab tidak ditemukan.')
        return json.loads(result)

    @app.get(PREFIX + '/lab/runs')
    def list_lab(account=Depends(user)):
        role(account, 'evaluator')
        with engine.connect() as connection:
            return [json.loads(r) for r in connection.execute(select(lab_runs.c.result).where(lab_runs.c.user_id == account['id']).order_by(lab_runs.c.created_at.desc())).scalars()]

    @app.post(PREFIX + '/lab/runs', status_code=201)
    def run_lab(body: LabInput, account=Depends(user)):
        role(account, 'evaluator')
        rate_limit('lab', account['id'], 5, 60)
        lock_id = uid()
        with engine.begin() as connection:
            acquired = connection.execute(update(lab_lock).where(lab_lock.c.id == 1, lab_lock.c.expires_at < time.time())
                .values(owner=lock_id, expires_at=time.time()+300))
            if acquired.rowcount != 1:
                raise ApiFailure(429, 'LAB_BUSY', 'Eksperimen lain sedang berjalan. Coba lagi nanti.')
        try:
            from .lab import measure
            result = measure(body, settings)
            result.update(id=uid(), created_at=now())
            result['environment']['storage'] = engine.dialect.name
            with engine.begin() as connection:
                connection.execute(insert(lab_runs).values(id=result['id'], user_id=account['id'], created_at=result['created_at'], result=json.dumps(result)))
            return result
        finally:
            with engine.begin() as connection:
                connection.execute(update(lab_lock).where(lab_lock.c.id == 1, lab_lock.c.owner == lock_id).values(expires_at=0, owner=None))

    @app.get(PREFIX + '/lab/runs/{result_id}')
    def get_lab(result_id: str, account=Depends(user)):
        role(account, 'evaluator')
        with engine.connect() as connection:
            return lab_result(connection, result_id, account)

    @app.get(PREFIX + '/lab/runs/{result_id}/export')
    def export_lab(result_id: str, account=Depends(user)):
        role(account, 'evaluator')
        with engine.connect() as connection:
            result = lab_result(connection, result_id, account)
        buffer = io.StringIO(newline='')
        keys = ['trial', 'algorithm', 'execution_order', 'encrypt_ns', 'decrypt_ns', 'correctness_ns', 'overhead_bytes', 'round_trip_ok']
        writer = csv.writer(buffer)
        writer.writerow(['mode', 'fixture', 'fixture_sha256', 'input_bytes', 'repetitions', 'warmups', 'methodology', 'suite', 'rc4_drop', 'timer_scope', *keys])
        for sample in result['samples']:
            writer.writerow(['LIVE', result['fixture'], result['fixture_sha256'], result['input_bytes'], result['repetitions'], result['warmups'], result['methodology_version'], result['suite'], 3072, result['environment']['timer_scope'], *[sample[k] for k in keys]])
        return attachment(buffer.getvalue().encode(), 'veltrix-lab-live.csv', 'text/csv; charset=utf-8')
    return app
