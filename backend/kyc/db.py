from pathlib import Path
from sqlalchemy import (MetaData, Table, Column, String, Integer, Float, Boolean, Text,
                        LargeBinary, ForeignKey, UniqueConstraint, CheckConstraint, Index,
                        create_engine, event)
from sqlalchemy.dialects.mysql import LONGBLOB, LONGTEXT, BINARY
from sqlalchemy.pool import StaticPool

metadata = MetaData()
blob = LargeBinary().with_variant(LONGBLOB(), 'mysql')
roles = "'applicant','reviewer','admin','evaluator'"
statuses = "'DRAFT','SUBMITTED','UNDER_REVIEW','NEEDS_REVISION','RESUBMITTED','ACCEPTED_DEMO','REJECTED_DEMO','WITHDRAWN'"
users = Table('kyc_users', metadata,
    Column('id', String(36), primary_key=True),
    Column('username', String(24, collation='utf8mb4_bin').with_variant(String(24), 'sqlite'), unique=True, nullable=False),
    Column('display_name', String(100), nullable=False), Column('password_hash', String(255), nullable=False),
    Column('role', String(16), nullable=False), Column('is_active', Boolean, nullable=False),
    Column('created_at', String(40), nullable=False), CheckConstraint(f'role IN ({roles})', name='valid_role'))
sessions = Table('kyc_sessions', metadata,
    Column('token_hash', String(64), primary_key=True),
    Column('user_id', String(36), ForeignKey('kyc_users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('created_at', Float, nullable=False), Column('expires_at', Float, nullable=False, index=True))
applications = Table('applications', metadata,
    Column('id', String(36), primary_key=True), Column('reference', String(40), unique=True, nullable=False),
    Column('owner_id', String(36), ForeignKey('kyc_users.id'), nullable=False),
    Column('status', String(20), nullable=False), Column('version', Integer, nullable=False),
    Column('synthetic_acknowledged', Boolean, nullable=False),
    Column('created_at', String(40), nullable=False), Column('updated_at', String(40), nullable=False),
    CheckConstraint(f'status IN ({statuses})', name='valid_status'),
    CheckConstraint('version >= 1', name='positive_case_version'))
Index('ix_case_owner_updated', applications.c.owner_id, applications.c.updated_at)
Index('ix_case_status_updated', applications.c.status, applications.c.updated_at)
assignments = Table('reviewer_assignments', metadata,
    Column('application_id', String(36), ForeignKey('applications.id', ondelete='CASCADE'), primary_key=True),
    Column('reviewer_id', String(36), ForeignKey('kyc_users.id'), nullable=False, index=True),
    Column('assigned_by', String(36), ForeignKey('kyc_users.id'), nullable=False),
    Column('assigned_at', String(40), nullable=False))
objects = Table('encrypted_objects', metadata,
    Column('id', String(36), primary_key=True),
    Column('application_id', String(36), ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('owner_id', String(36), ForeignKey('kyc_users.id'), nullable=False),
    Column('kind', String(20), nullable=False), Column('category', String(16), nullable=False),
    Column('payload_version', Integer, nullable=False), Column('key_version', Integer, nullable=False),
    Column('header', Text, nullable=False), Column('ciphertext', blob, nullable=False),
    Column('wrapped_keys', LargeBinary(72), nullable=False), Column('wrap_nonce', LargeBinary(12).with_variant(BINARY(12), 'mysql'), nullable=False),
    Column('wrap_tag', LargeBinary(16), nullable=False), Column('created_at', String(40), nullable=False),
    UniqueConstraint('key_version', 'wrap_nonce', name='unique_wrap_nonce'))
profiles = Table('personal_data_versions', metadata,
    Column('id', String(36), primary_key=True),
    Column('application_id', String(36), ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
    Column('version', Integer, nullable=False),
    Column('object_id', String(36), ForeignKey('encrypted_objects.id', ondelete='CASCADE'), unique=True, nullable=False),
    Column('created_at', String(40), nullable=False), UniqueConstraint('application_id', 'version', name='unique_profile_version'))
evidence = Table('evidence_versions', metadata,
    Column('id', String(36), primary_key=True),
    Column('application_id', String(36), ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
    Column('category', String(16), nullable=False), Column('version', Integer, nullable=False),
    Column('object_id', String(36), ForeignKey('encrypted_objects.id', ondelete='CASCADE'), unique=True, nullable=False),
    Column('original_bytes', Integer, nullable=False), Column('mime_type', String(100), nullable=False),
    Column('created_at', String(40), nullable=False),
    CheckConstraint("category IN ('identity','document','video')", name='valid_category'),
    UniqueConstraint('application_id', 'category', 'version', name='unique_evidence_version'))
events = Table('case_events', metadata,
    Column('id', String(36), primary_key=True),
    Column('application_id', String(36), ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('actor_id', String(36), ForeignKey('kyc_users.id'), nullable=False),
    Column('actor_role', String(16), nullable=False), Column('action', String(80), nullable=False),
    Column('at', String(40), nullable=False), Column('case_version', Integer, nullable=False),
    Column('note_object_id', String(36), ForeignKey('encrypted_objects.id', ondelete='CASCADE')),
    UniqueConstraint('application_id', 'case_version', name='unique_case_event_version'))
lab_runs = Table('lab_runs', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', String(36), ForeignKey('kyc_users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('created_at', String(40), nullable=False), Column('result', Text().with_variant(LONGTEXT(), 'mysql'), nullable=False))
lab_lock = Table('lab_lock', metadata,
    Column('id', Integer, primary_key=True), Column('owner', String(36)), Column('expires_at', Float, nullable=False))
limits = Table('kyc_rate_limits', metadata,
    Column('bucket', String(64), primary_key=True), Column('window', Float, nullable=False),
    Column('count', Integer, nullable=False))
security_log = Table('security_events', metadata,
    Column('id', String(36), primary_key=True), Column('at', String(40), nullable=False),
    Column('actor_id', String(36)), Column('action', String(40), nullable=False),
    Column('resource_id', String(36)))

def database(url):
    sqlite = url.startswith('sqlite')
    if url.startswith('sqlite:///') and not url.endswith(':memory:'):
        Path(url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
    options = {'connect_args': {'check_same_thread': False, 'timeout': 30}} if sqlite else {'pool_pre_ping': True}
    if url.endswith(':memory:'):
        options['poolclass'] = StaticPool
    engine = create_engine(url, **options)
    if sqlite:
        @event.listens_for(engine, 'connect')
        def pragmas(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA secure_delete=ON')
            connection.execute('PRAGMA journal_mode=WAL')
    return engine
key_state = Table('kyc_key_state', metadata,
    Column('id', Integer, primary_key=True), Column('kek_fingerprint', String(64), nullable=False),
    Column('auth_fingerprint', String(64), nullable=False))
