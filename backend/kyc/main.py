import base64
import binascii
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
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from threading import BoundedSemaphore
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Request, Response, Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartParser
from starlette.datastructures import UploadFile
from .config import Settings
from .db import (database, users, sessions, applications, assignments, objects, profiles,
                 evidence, evidence_types, events, limits, security_log, lab_runs, lab_lock,
                 review_records, document_analyses, user_public_keys, share_requests, share_items)
from .crypto import Envelope, IntegrityFailure, canonical
from .schemas import (Model, Credentials, Registration, SaveProfile, Action, Assignment, LabInput, ReviewChecks,
                      PublicKeyRegistration, ShareRequestCreate, ShareApprove, ShareOpen)
from .sharing_crypto import (public_key_details, package_key, wrap_key, unwrap_key,
                             encrypt_item, decrypt_item)
from .analysis_worker import AnalysisWorker
from .review import (DEFAULT_TYPES, ACCEPTED_TYPES, REQUIRED, PROFILE_FIELDS, ACTIVE_REVIEW,
                     DOCX, PREVIEW_MIME, classified_evidence, current_evidence, review_slot, passed, valid_reason, docx_preview, pdf_page_preview)
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
    analysis_worker = AnalysisWorker()
    analysis_slots = BoundedSemaphore(1)
    preview_slots = BoundedSemaphore(2)
    passwords = PasswordHasher()
    dummy_hash = passwords.hash(secrets.token_urlsafe(32))
    # Request cap is strictly lower than spool threshold: no upload rollover to disk.
    MultiPartParser.spool_max_size = settings.max_request_bytes + 1

    @asynccontextmanager
    async def lifespan(_):
        # Fail early for missing schema or wrong KEK; never generate replacement keys here.
        from .provision import check_keys
        check_keys(engine, settings)
        try:
            yield
        finally:
            analysis_worker.close()
            engine.dispose()

    app = FastAPI(title='VELTRIX BankKYC API', version='2.0.0', lifespan=lifespan)
    app.state.engine, app.state.envelope, app.state.settings = engine, envelope, settings
    app.add_middleware(BodyLimit, max_bytes=settings.max_request_bytes)

    def audit(action, actor_id=None, resource_id=None, *, case_id=None, evidence_id=None, outcome=None):
        try:
            with engine.begin() as connection:
                connection.execute(insert(security_log).values(id=uid(), at=now(), actor_id=actor_id, action=action, resource_id=resource_id, application_id=case_id, evidence_id=evidence_id, outcome=outcome))
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
            audit('access_denied', getattr(request.state, 'actor_id', None), outcome='denied')
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
        for entry in connection.execute(classified_evidence(row['id']).order_by(evidence.c.version, evidence.c.created_at)).mappings():
            item = {k: entry[k] for k in ('id', 'category', 'version', 'original_bytes', 'mime_type', 'created_at', 'document_type')}
            item['required'] = review_slot(entry) in REQUIRED
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
                if event['action'] in ('Revisi diminta', 'Pengajuan ditolak', 'Pengajuan ditolak (simulasi)'):
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
                'document_type': {'type': 'string', 'enum': sorted(set(DEFAULT_TYPES.values()) | {'kk_optional'})},
                'version': {'type': 'integer', 'minimum': 1}, 'file': {'type': 'string', 'format': 'binary'}}}}}}})
    async def upload(case_id: str, request: Request, account=Depends(user)):
        # Ownership and edit scope checked before multipart parsing and repeated in transaction.
        with engine.connect() as connection:
            existing = case(connection, case_id, account, owner=True)
            if existing['status'] not in EDITABLE:
                raise ApiFailure(409, 'CASE_READ_ONLY', 'Pengajuan terkunci.')
        rate_limit('upload', account['id'], 60, 60)
        async with request.form(max_files=1, max_fields=3, max_part_size=2048) as form:
            pairs = list(form.multi_items())
            if len(pairs) != len(form) or set(form) not in ({'category', 'version', 'file'}, {'category', 'version', 'file', 'document_type'}):
                raise ApiFailure(422, 'INVALID_UPLOAD', 'Kirim tepat satu file, kategori, dan versi.')
            category, file = form['category'], form['file']
            if not isinstance(category, str) or category not in RULES or not isinstance(file, UploadFile):
                raise ApiFailure(422, 'INVALID_UPLOAD', 'Kategori atau file tidak valid.')
            document_type = form.get('document_type', DEFAULT_TYPES[category])
            if not isinstance(document_type, str) or document_type not in ACCEPTED_TYPES[category]:
                raise ApiFailure(422, 'INVALID_DOCUMENT_TYPE', 'Jenis dokumen tidak cocok dengan kategori.')
            validation_category = 'identity' if document_type == 'kk_optional' else category
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
            cap = RULES[validation_category][1]
            data = await file.read(cap + 1)
            if len(data) > cap:
                raise ApiFailure(413, 'FILE_TOO_LARGE', 'Ukuran file melebihi batas kategori.')
            try:
                mime = validate(data, filename, validation_category, settings.ffprobe)
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
                object_id = store_object(connection, row, 'evidence', category, payload_version, data, {'filename': filename, 'mime_type': mime, 'document_type': document_type})
                evidence_id = uid()
                connection.execute(insert(evidence).values(id=evidence_id, application_id=case_id, category=category, version=payload_version,
                    object_id=object_id, original_bytes=len(data), mime_type=mime, created_at=now()))
                connection.execute(insert(evidence_types).values(evidence_id=evidence_id, document_type=document_type))
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

    def reviewer_case(connection, case_id, account, *, lock=False, writing=False):
        role(account, 'reviewer')
        row = case(connection, case_id, account, lock=lock)
        allowed = ('UNDER_REVIEW',) if writing else ACTIVE_REVIEW
        if row['status'] not in allowed:
            raise ApiFailure(409, 'REVIEW_NOT_ACTIVE', 'Tinjauan konten belum aktif.')
        return row

    def reviewer_evidence(connection, row, evidence_id):
        for entry in current_evidence(connection, row['id']).values():
            if entry['id'] == evidence_id:
                return entry
        raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Versi bukti aktif tidak ditemukan.')

    def open_evidence(connection, row, entry):
        meta, data = open_object(connection, entry['object_id'], row, kind='evidence',
                                 category=entry['category'], version=entry['version'])
        if (meta.get('mime_type') != entry['mime_type'] or len(data) != entry['original_bytes']
                or not (meta.get('document_type') == entry['document_type']
                        or ('document_type' not in meta and entry['document_type'] in
                            ('ktp', 'legacy_supporting_document', 'verification_video')))):
            raise IntegrityFailure()
        return data

    def review_profile_data(connection, row, entry):
        if entry is None:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Profil belum tersedia.')
        _, data = open_object(connection, entry['object_id'], row, kind='personal_data',
                              category='', version=entry['version'])
        return json.loads(data)

    def add_security_event(connection, action, account, case_id, *, evidence_id=None, outcome='success'):
        connection.execute(insert(security_log).values(id=uid(), at=now(), actor_id=account['id'],
                                                        action=action, resource_id=evidence_id or case_id,
                                                        application_id=case_id, evidence_id=evidence_id, outcome=outcome))

    @app.get(PREFIX + '/applications/{case_id}/review/profile')
    def reviewer_profile(case_id: str, account=Depends(user)):
        rate_limit('review_profile', account['id'], 120, 60)
        with engine.connect() as connection:
            row = reviewer_case(connection, case_id, account, lock=True)
            data = review_profile_data(connection, row, latest_profile(connection, row))
        audit('REVIEW_PROFILE_READ', account['id'], case_id, case_id=case_id, outcome='success')
        return {'profile': {key: data[key] for key in PROFILE_FIELDS}}

    @app.get(PREFIX + '/applications/{case_id}/evidence/{evidence_id}/review-preview')
    def review_preview(case_id: str, evidence_id: str, page: int | None = Query(None, ge=1, le=500), account=Depends(user)):
        rate_limit('review_preview', account['id'], 30, 60)
        if not preview_slots.acquire(blocking=False):
            raise ApiFailure(429, 'PREVIEW_BUSY', 'Pratinjau sedang sibuk. Coba lagi.')
        try:
            with engine.connect() as connection:
                row = reviewer_case(connection, case_id, account, lock=True)
                entry = reviewer_evidence(connection, row, evidence_id)
                mime = entry['mime_type']
                if mime not in PREVIEW_MIME:
                    raise ApiFailure(415, 'PREVIEW_UNSUPPORTED', 'Format pratinjau tidak didukung.')
                data = open_evidence(connection, row, entry)
            if page is not None:
                if mime != 'application/pdf':
                    raise ApiFailure(415, 'PREVIEW_UNSUPPORTED', 'Nomor halaman hanya tersedia untuk PDF.')
                try:
                    rendered = pdf_page_preview(data, page)
                except Exception:
                    raise ApiFailure(422, 'PREVIEW_UNAVAILABLE', 'Halaman PDF belum dapat ditampilkan.')
                if rendered is None:
                    raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Halaman PDF tidak ditemukan.')
                png, total = rendered
                audit('CONTENT_PREVIEWED', account['id'], evidence_id, case_id=case_id, evidence_id=evidence_id, outcome='success')
                return {'page': page, 'pages': total, 'image_base64': base64.b64encode(png).decode('ascii')}
            headers = {'Content-Disposition': 'inline', 'Content-Security-Policy': "sandbox; default-src 'none'"}
            if mime == DOCX:
                data, mime = docx_preview(data), 'text/plain'
            audit('CONTENT_PREVIEWED', account['id'], evidence_id, case_id=case_id, evidence_id=evidence_id, outcome='success')
            return Response(data, media_type=mime, headers=headers)
        finally:
            preview_slots.release()

    def saved_review(connection, row, account, version):
        record = connection.execute(select(review_records).where(
            review_records.c.application_id == row['id'], review_records.c.case_version == version,
            review_records.c.reviewer_id == account['id'])).mappings().first()
        if record is None:
            return None
        private, payload = open_object(connection, record['object_id'], row, kind='review_check',
                                       category='', version=version)
        if private.get('reviewer_id') != account['id']:
            raise IntegrityFailure()
        return json.loads(payload)

    @app.get(PREFIX + '/applications/{case_id}/review/checks')
    def get_review_checks(case_id: str, account=Depends(user)):
        with engine.connect() as connection:
            row = reviewer_case(connection, case_id, account)
            return {'version': row['version'], 'review': saved_review(connection, row, account, row['version'])}

    @app.post(PREFIX + '/applications/{case_id}/review/checks')
    def save_review_checks(case_id: str, body: ReviewChecks, account=Depends(user)):
        with engine.begin() as connection:
            row = reviewer_case(connection, case_id, account, lock=True, writing=True)
            reserve(connection, row, body.version)
            current = current_evidence(connection, case_id)
            latest = {item['id']: (slot, item) for slot, item in current.items()}
            checks = [item.model_dump() for item in body.checks]
            checked = set()
            for check in checks:
                slot, item = latest.get(check['evidence_id'], (None, None))
                if item is None or item['version'] != check['evidence_version']:
                    raise ApiFailure(409, 'EVIDENCE_VERSION_CONFLICT', 'Bukti berubah. Muat ulang tinjauan.')
                if slot in checked or not valid_reason(check):
                    raise ApiFailure(422, 'INVALID_REVIEW_CHECKS', 'Checklist dan kode alasan harus konsisten.')
                if not passed(check) and not check['note']:
                    raise ApiFailure(422, 'NOTE_REQUIRED', 'Isi alasan untuk bukti yang perlu ditinjau ulang.')
                checked.add(slot)
            if not REQUIRED <= checked:
                raise ApiFailure(422, 'REVIEW_CHECKS_REQUIRED', 'Periksa setiap bukti wajib versi terbaru.')
            payload = {'checks': checks}
            object_id = store_object(connection, row, 'review_check', '', row['version'],
                                     canonical(payload), {'reviewer_id': account['id']})
            connection.execute(insert(review_records).values(application_id=case_id, case_version=row['version'],
                                                              reviewer_id=account['id'], object_id=object_id))
            add_event(connection, row, account, 'Checklist bukti disimpan')
            add_security_event(connection, 'REVIEW_CHECKS_SAVED', account, case_id)
            return {'version': row['version'], 'review': payload}

    def analysis_query(entry, profile_entry):
        return (document_analyses.c.evidence_id == entry['id'],
                document_analyses.c.profile_id == profile_entry['id'])

    def analysis_binding(entry, profile_entry):
        return {'evidence_id': entry['id'], 'profile_id': profile_entry['id'],
                'document_type': entry['document_type']}

    def read_analysis(connection, row, entry, profile_entry):
        record = connection.execute(select(document_analyses).where(*analysis_query(entry, profile_entry))).mappings().first()
        if record is None:
            return None
        private, payload = open_object(connection, record['object_id'], row, kind='document_analysis',
                                       category=entry['category'], version=entry['version'])
        binding = analysis_binding(entry, profile_entry)
        if record['evidence_version'] != entry['version'] or any(private.get(key) != value for key, value in binding.items()):
            raise IntegrityFailure()
        return json.loads(payload)

    @app.get(PREFIX + '/applications/{case_id}/evidence/{evidence_id}/analysis')
    def get_analysis(case_id: str, evidence_id: str, account=Depends(user)):
        rate_limit('analysis_get', account['id'], 120, 60)
        with engine.connect() as connection:
            row = reviewer_case(connection, case_id, account)
            entry = reviewer_evidence(connection, row, evidence_id)
            result = read_analysis(connection, row, entry, latest_profile(connection, row))
            if result is None:
                raise ApiFailure(404, 'ANALYSIS_NOT_FOUND', 'Analisis versi bukti dan profil ini belum tersedia.')
            return result

    @app.post(PREFIX + '/applications/{case_id}/evidence/{evidence_id}/analysis')
    def post_analysis(case_id: str, evidence_id: str, account=Depends(user)):
        rate_limit('analysis_post', account['id'], 12, 60)
        if not analysis_slots.acquire(blocking=False):
            raise ApiFailure(429, 'ANALYSIS_BUSY', 'Analisis sedang berjalan. Coba lagi.')
        try:
            with engine.connect() as connection:
                row = reviewer_case(connection, case_id, account)
                entry = reviewer_evidence(connection, row, evidence_id)
                if review_slot(entry) not in ('ktp', 'account_opening_form'):
                    raise ApiFailure(415, 'ANALYSIS_UNSUPPORTED', 'Analisis tersedia untuk KTP dan formulir.')
                profile_entry = latest_profile(connection, row)
                submitted = review_profile_data(connection, row, profile_entry)
                cached = read_analysis(connection, row, entry, profile_entry)
                if cached is not None and cached['status'] == 'COMPLETED':
                    return cached
                data = open_evidence(connection, row, entry)
            result = analysis_worker.run(content_bytes=data, mime_type=entry['mime_type'],
                                         document_type=review_slot(entry), submitted_form=submitted,
                                         evidence_id=evidence_id, evidence_version=entry['version'])
            if not result or result.get('status') != 'COMPLETED' or not result.get('extracted_fields'):
                result = {'status': 'FAILED', 'engine': (result or {}).get('engine', 'none'),
                          'model_version': (result or {}).get('model_version', 'none'),
                          'checks': [], 'extracted_fields': {},
                          'error': 'Analisis tidak dapat membaca dokumen. Lanjutkan pemeriksaan manual.'}
            result.update(evidence_id=evidence_id, evidence_version=entry['version'], manual_review_required=True,
                          expected_document_type=entry['document_type'], processed_at=now())
            result.setdefault('document_type', 'unknown')
            with engine.begin() as connection:
                current = reviewer_case(connection, case_id, account, lock=True)
                if current['version'] != row['version']:
                    raise ApiFailure(409, 'VERSION_CONFLICT', 'Pengajuan berubah saat analisis. Muat ulang.')
                previous = connection.execute(select(document_analyses).where(*analysis_query(entry, profile_entry))).mappings().first()
                if previous is not None and previous['status'] == 'COMPLETED':
                    return read_analysis(connection, current, entry, profile_entry)
                object_id = store_object(connection, current, 'document_analysis', entry['category'], entry['version'],
                                         canonical(result), analysis_binding(entry, profile_entry))
                values = dict(object_id=object_id, status=result['status'], processed_at=result['processed_at'])
                if previous is None:
                    connection.execute(insert(document_analyses).values(
                        evidence_id=evidence_id, profile_id=profile_entry['id'], evidence_version=entry['version'], **values))
                else:
                    connection.execute(update(document_analyses).where(*analysis_query(entry, profile_entry)).values(**values))
                    connection.execute(delete(objects).where(objects.c.id == previous['object_id']))
                outcome = 'DOCUMENT_ANALYZED' if result['status'] == 'COMPLETED' else 'DOCUMENT_ANALYSIS_FAILED'
                add_security_event(connection, outcome, account, case_id, evidence_id=evidence_id,
                                   outcome='success' if result['status'] == 'COMPLETED' else 'failed')
            return result
        finally:
            analysis_slots.release()

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
                slots = current_evidence(connection, case_id)
                if latest_profile(connection, row) is None or not REQUIRED <= slots.keys() or body.synthetic_acknowledged is not True:
                    raise ApiFailure(422, 'CASE_INCOMPLETE', 'Lengkapi profil, KTP dummy, formulir pembukaan rekening, video, dan konfirmasi data sintetis.')
                row['synthetic_acknowledged'] = True
            decision = body.action in ('request-revision', 'accept', 'reject')
            if decision:
                review = saved_review(connection, row, account, body.version)
                if review is None:
                    raise ApiFailure(422, 'REVIEW_CHECKS_REQUIRED', 'Simpan checklist bukti sebelum membuat keputusan.')
                has_issue = any(not passed(check) for check in review['checks'])
                if (body.action == 'accept') == has_issue:
                    raise ApiFailure(422, 'DECISION_CHECKS_MISMATCH', 'Keputusan harus sesuai hasil checklist.')
                if not body.note or len(body.note) < 10:
                    raise ApiFailure(422, 'NOTE_REQUIRED', 'Tulis alasan keputusan 10–500 karakter.')
                add_security_event(connection, 'REVIEW_DECISION_RECORDED', account, row['id'])
            row['status'] = allowed[body.action]
            connection.execute(update(applications).where(applications.c.id == case_id).values(status=row['status'], synthetic_acknowledged=row['synthetic_acknowledged']))
            labels = {'submit': 'Pengajuan dikirim', 'resubmit': 'Pengajuan dikirim ulang', 'withdraw': 'Pengajuan ditarik',
                'start-review': 'Tinjauan dokumen dimulai', 'request-revision': 'Revisi diminta', 'accept': 'Pengajuan diterima (simulasi)', 'reject': 'Pengajuan ditolak (simulasi)'}
            add_event(connection, row, account, labels[body.action], body.note if decision else None)
            return present(connection, row, account)

    # Assignment 2: all share routes require an authenticated applicant. Sensitive
    # copies are bound to one request and can only be opened with the caller's key.
    SHARE_KINDS = {'profile', 'identity', 'document', 'video', 'kk'}

    def active_public_key(connection, user_id):
        return connection.execute(select(user_public_keys).where(
            user_public_keys.c.user_id == user_id, user_public_keys.c.revoked_at.is_(None))).mappings().first()

    def share_event(connection, name, account, request_id, outcome='success'):
        connection.execute(insert(security_log).values(
            id=uid(), at=now(), actor_id=account['id'], action=name,
            resource_id=request_id, outcome=outcome))

    def share_record(connection, request_id, account, side, *, lock=False):
        role(account, 'applicant')
        query = select(share_requests).where(share_requests.c.id == request_id)
        if lock:
            query = query.with_for_update()
        row = connection.execute(query).mappings().first()
        party = 'owner_id' if side == 'owner' else 'requester_id'
        if row is None or row[party] != account['id']:
            raise ApiFailure(404, 'RESOURCE_NOT_FOUND', 'Permintaan tidak ditemukan.')
        return dict(row)

    def expire_share(connection, row, account):
        if row['status'] == 'APPROVED' and row['expires_at'] and row['expires_at'] <= now():
            connection.execute(delete(share_items).where(share_items.c.request_id == row['id']))
            connection.execute(update(share_requests).where(share_requests.c.id == row['id']).values(
                status='EXPIRED', wrapped_share_key=None, wrap_nonce=None, wrap_tag=None))
            row.update(status='EXPIRED', wrapped_share_key=None, wrap_nonce=None, wrap_tag=None)
            share_event(connection, 'SHARE_EXPIRED', account, row['id'])
        return row

    def refresh_share_expiry(request_id, account, side):
        # Commit expiry/shredding before a later request can fail its own transaction.
        with engine.begin() as connection:
            expire_share(connection, share_record(connection, request_id, account, side, lock=True), account)

    def share_projection(connection, row):
        requester = connection.execute(select(users.c.username).where(users.c.id == row['requester_id'])).scalar_one()
        owner = connection.execute(select(users.c.username).where(users.c.id == row['owner_id'])).scalar_one()
        key = connection.execute(select(user_public_keys.c.fingerprint).where(
            user_public_keys.c.id == row['requester_key_id'])).scalar_one_or_none() if row['requester_key_id'] else None
        if key is None:
            active = active_public_key(connection, row['requester_id'])
            key = active['fingerprint'] if active else None
        return {'id': row['id'], 'requester_username': requester, 'owner_username': owner,
                'purpose': row['purpose'], 'requested_items': row['requested_items'].split(','),
                'status': row['status'], 'application_id': row['application_id'],
                'requester_key_fingerprint': key[:16] if key else None,
                'created_at': row['created_at'], 'decided_at': row['decided_at'], 'expires_at': row['expires_at']}

    @app.get(PREFIX + '/keys/me')
    def get_my_key(account=Depends(user)):
        role(account, 'applicant')
        with engine.connect() as connection:
            key = active_public_key(connection, account['id'])
            return {'key': ({'public_key_pem': key['public_key_pem'], 'fingerprint': key['fingerprint'][:16],
                             'created_at': key['created_at']} if key else None)}

    @app.put(PREFIX + '/keys/me')
    def put_my_key(body: PublicKeyRegistration, account=Depends(user)):
        role(account, 'applicant')
        try:
            pem, fingerprint = public_key_details(body.public_key_pem)
        except (ValueError, IndexError, TypeError):
            raise ApiFailure(422, 'INVALID_PUBLIC_KEY', 'Gunakan public key RSA SPKI minimal 2048 bit.')
        with engine.begin() as connection:
            connection.execute(select(users.c.id).where(users.c.id == account['id']).with_for_update()).first()
            connection.execute(update(user_public_keys).where(
                user_public_keys.c.user_id == account['id'], user_public_keys.c.revoked_at.is_(None)).values(revoked_at=now()))
            connection.execute(insert(user_public_keys).values(id=uid(), user_id=account['id'],
                public_key_pem=pem, fingerprint=fingerprint, created_at=now()))
        return {'public_key_pem': pem, 'fingerprint': fingerprint[:16]}

    @app.post(PREFIX + '/share-requests', status_code=201)
    def create_share_request(body: ShareRequestCreate, account=Depends(user)):
        role(account, 'applicant')
        rate_limit('share_request', account['id'], 10, 3600)
        if len(set(body.items)) != len(body.items):
            raise ApiFailure(422, 'INVALID_ITEMS', 'Jenis dokumen tidak boleh berulang.')
        with engine.begin() as connection:
            if active_public_key(connection, account['id']) is None:
                raise ApiFailure(422, 'PUBLIC_KEY_REQUIRED', 'Buat kunci publik terlebih dahulu.')
            owner = connection.execute(select(users).where(users.c.username == body.owner_username,
                users.c.role == 'applicant', users.c.is_active.is_(True))).mappings().first()
            if owner is None or owner['id'] == account['id']:
                raise ApiFailure(422, 'INVALID_OWNER', 'Pilih pemohon lain yang aktif.')
            row = dict(id=uid(), requester_id=account['id'], owner_id=owner['id'], purpose=body.purpose,
                requested_items=','.join(body.items), status='PENDING', created_at=now())
            connection.execute(insert(share_requests).values(**row))
            share_event(connection, 'SHARE_REQUESTED', account, row['id'])
            return share_projection(connection, {**row, 'application_id': None,
                'requester_key_id': None, 'decided_at': None, 'expires_at': None})

    @app.get(PREFIX + '/share-requests')
    def list_share_requests(box: str = Query(..., pattern='^(incoming|outgoing)$'), account=Depends(user)):
        role(account, 'applicant')
        side = share_requests.c.owner_id if box == 'incoming' else share_requests.c.requester_id
        with engine.begin() as connection:
            rows = connection.execute(select(share_requests).where(side == account['id']).order_by(
                share_requests.c.created_at.desc())).mappings().all()
            return {'items': [share_projection(connection, expire_share(connection, dict(row), account)) for row in rows]}

    @app.post(PREFIX + '/share-requests/{request_id}/reject')
    def reject_share(request_id: str, account=Depends(user)):
        with engine.begin() as connection:
            row = share_record(connection, request_id, account, 'owner', lock=True)
            if row['status'] != 'PENDING':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Permintaan tidak lagi menunggu keputusan.')
            connection.execute(update(share_requests).where(share_requests.c.id == request_id).values(
                status='REJECTED', decided_at=now()))
            share_event(connection, 'SHARE_REJECTED', account, request_id)
            return {'status': 'REJECTED'}

    @app.post(PREFIX + '/share-requests/{request_id}/cancel')
    def cancel_share(request_id: str, account=Depends(user)):
        with engine.begin() as connection:
            row = share_record(connection, request_id, account, 'requester', lock=True)
            if row['status'] != 'PENDING':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Permintaan tidak dapat dibatalkan.')
            connection.execute(update(share_requests).where(share_requests.c.id == request_id).values(
                status='CANCELLED', decided_at=now()))
            share_event(connection, 'SHARE_CANCELLED', account, request_id)
            return {'status': 'CANCELLED'}

    @app.post(PREFIX + '/share-requests/{request_id}/approve')
    def approve_share(request_id: str, body: ShareApprove, account=Depends(user)):
        if len(set(body.items)) != len(body.items):
            raise ApiFailure(422, 'INVALID_ITEMS', 'Jenis dokumen tidak boleh berulang.')
        with engine.begin() as connection:
            row = share_record(connection, request_id, account, 'owner', lock=True)
            if row['status'] != 'PENDING':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Permintaan tidak lagi menunggu keputusan.')
            if not set(body.items) <= set(row['requested_items'].split(',')):
                raise ApiFailure(422, 'INVALID_ITEMS', 'Hanya dokumen yang diminta dapat dibagikan.')
            application = case(connection, body.application_id, account, owner=True)
            # Drafts are allowed: co-signers check each other's documents before submitting.
            if application['status'] == 'WITHDRAWN':
                raise ApiFailure(409, 'CASE_NOT_SHAREABLE', 'Pengajuan yang ditarik tidak dapat dibagikan.')
            public = active_public_key(connection, row['requester_id'])
            if public is None:
                raise ApiFailure(409, 'PUBLIC_KEY_REQUIRED', 'Peminta perlu membuat kunci publik baru.')
            current = current_evidence(connection, application['id'])
            payloads = []
            for kind in body.items:
                if kind == 'profile':
                    profile_entry = latest_profile(connection, application)
                    if profile_entry is None:
                        raise ApiFailure(422, 'ITEM_UNAVAILABLE', 'Profil tidak tersedia.')
                    data = canonical(review_profile_data(connection, application, profile_entry))
                    mime = 'application/json'
                else:
                    subtype = {'identity': 'ktp', 'document': 'account_opening_form',
                               'video': 'verification_video', 'kk': 'kk_optional'}[kind]
                    entry = current.get(subtype)
                    if entry is None:
                        raise ApiFailure(422, 'ITEM_UNAVAILABLE', 'Dokumen yang dipilih tidak tersedia.')
                    data, mime = open_evidence(connection, application, entry), entry['mime_type']
                payloads.append((kind, mime, data))
            share_key = secrets.token_bytes(32)
            wrapped, nonce, tag = wrap_key(settings.kek, row['id'], row['owner_id'], row['requester_id'], share_key)
            for kind, mime, data in payloads:
                item_id = uid()
                item_nonce, ciphertext = encrypt_item(row, item_id, kind, share_key, data)
                connection.execute(insert(share_items).values(id=item_id, request_id=row['id'], kind=kind,
                    mime_type=mime, display_name=kind, original_bytes=len(data), nonce=item_nonce, ciphertext=ciphertext))
            expiry = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            connection.execute(update(share_requests).where(share_requests.c.id == row['id']).values(
                status='APPROVED', application_id=application['id'], requester_key_id=public['id'],
                wrapped_share_key=wrapped, wrap_nonce=nonce, wrap_tag=tag, decided_at=now(), expires_at=expiry))
            share_event(connection, 'SHARE_APPROVED', account, row['id'])
            return {'status': 'APPROVED', 'expires_at': expiry,
                    'package': package_key(row['id'], share_key, public['public_key_pem'], public['fingerprint'])}

    @app.post(PREFIX + '/share-requests/{request_id}/revoke')
    def revoke_share(request_id: str, account=Depends(user)):
        refresh_share_expiry(request_id, account, 'owner')
        with engine.begin() as connection:
            row = expire_share(connection, share_record(connection, request_id, account, 'owner', lock=True), account)
            if row['status'] != 'APPROVED':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Akses tidak aktif.')
            connection.execute(delete(share_items).where(share_items.c.request_id == request_id))
            connection.execute(update(share_requests).where(share_requests.c.id == request_id).values(
                status='REVOKED', wrapped_share_key=None, wrap_nonce=None, wrap_tag=None))
            share_event(connection, 'SHARE_REVOKED', account, request_id)
            return {'status': 'REVOKED'}

    @app.get(PREFIX + '/share-requests/{request_id}/package')
    def get_share_package(request_id: str, account=Depends(user)):
        refresh_share_expiry(request_id, account, 'owner')
        with engine.begin() as connection:
            row = expire_share(connection, share_record(connection, request_id, account, 'owner', lock=True), account)
            if row['status'] != 'APPROVED':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Akses tidak aktif.')
            public = active_public_key(connection, row['requester_id'])
            if public is None:
                raise ApiFailure(409, 'PUBLIC_KEY_REQUIRED', 'Peminta perlu membuat kunci publik baru.')
            try:
                share_key = unwrap_key(settings.kek, row)
            except (ValueError, KeyError):
                raise IntegrityFailure()
            if row['requester_key_id'] != public['id']:
                connection.execute(update(share_requests).where(share_requests.c.id == request_id).values(requester_key_id=public['id']))
            return {'package': package_key(request_id, share_key, public['public_key_pem'], public['fingerprint']),
                    'key_fp': public['fingerprint'][:16]}

    @app.get(PREFIX + '/share-requests/{request_id}/items')
    def list_share_items(request_id: str, account=Depends(user)):
        refresh_share_expiry(request_id, account, 'requester')
        with engine.begin() as connection:
            row = expire_share(connection, share_record(connection, request_id, account, 'requester', lock=True), account)
            if row['status'] != 'APPROVED':
                raise ApiFailure(409, 'INVALID_TRANSITION', 'Akses tidak aktif.')
            items = connection.execute(select(share_items.c.id, share_items.c.kind, share_items.c.mime_type,
                share_items.c.display_name, share_items.c.original_bytes).where(
                share_items.c.request_id == request_id)).mappings().all()
            return {'items': [dict(item) for item in items], 'expires_at': row['expires_at']}

    @app.post(PREFIX + '/share-requests/{request_id}/items/{item_id}/open')
    def open_share_item(request_id: str, item_id: str, body: ShareOpen, account=Depends(user)):
        role(account, 'applicant')
        rate_limit('share_open', account['id'], 20, 60)
        try:
            refresh_share_expiry(request_id, account, 'requester')
            with engine.begin() as connection:
                row = expire_share(connection, share_record(connection, request_id, account, 'requester', lock=True), account)
                if row['status'] != 'APPROVED':
                    raise ValueError('Unavailable')
                item = connection.execute(select(share_items).where(share_items.c.id == item_id,
                    share_items.c.request_id == request_id)).mappings().first()
                if item is None:
                    raise ValueError('Unavailable')
                key = base64.b64decode(body.share_key, validate=True)
                data = decrypt_item(row, item, key)
                if len(data) != item['original_bytes']:
                    raise ValueError('Corrupt copy')
                share_event(connection, 'SHARE_OPENED', account, request_id)
                return Response(data, media_type=item['mime_type'], headers={'Content-Disposition': 'inline',
                    'Content-Security-Policy': "sandbox; default-src 'none'"})
        except (ApiFailure, ValueError, KeyError, TypeError, binascii.Error):
            audit('SHARE_OPEN_FAILED', account['id'], request_id, outcome='failed')
            raise ApiFailure(403, 'SHARE_OPEN_DENIED', 'Kunci tidak valid atau akses tidak tersedia.')

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
