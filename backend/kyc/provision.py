import hmac
import secrets
import uuid
from datetime import datetime, timezone
from argon2 import PasswordHasher
from sqlalchemy import select, insert, update, delete
from .db import key_state, users, sessions

def fingerprints(settings):
    return {'kek_fingerprint': hmac.digest(settings.kek, b'VELTRIX/KEK/check/v1', 'sha256').hex(),
            'auth_fingerprint': hmac.digest(settings.auth_secret, b'VELTRIX/auth/check/v1', 'sha256').hex()}

def initialize_keys(engine, settings):
    with engine.begin() as connection:
        if connection.execute(select(key_state.c.id)).first() is None:
            connection.execute(insert(key_state).values(id=1, **fingerprints(settings)))
    check_keys(engine, settings)

def check_keys(engine, settings):
    with engine.connect() as connection:
        row = connection.execute(select(key_state).where(key_state.c.id == 1)).mappings().first()
    if not row or any(not hmac.compare_digest(row[k], v) for k, v in fingerprints(settings).items()):
        raise RuntimeError('Configured BankKYC keys do not match this database. Restore the original .env backup.')

def create_user(engine, username, password, role='applicant', display_name=None):
    from .schemas import Registration
    credentials = Registration(username=username, password=password)
    if role not in ('applicant', 'reviewer', 'admin', 'evaluator'):
        raise ValueError('Invalid role')
    with engine.begin() as connection:
        account = dict(id=str(uuid.uuid4()), username=credentials.username, display_name=display_name or username, role=role)
        connection.execute(insert(users).values(**account, password_hash=PasswordHasher().hash(credentials.password), is_active=True,
            created_at=datetime.now(timezone.utc).isoformat()))
    return account
