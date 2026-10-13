from sqlalchemy import (create_engine, event, MetaData, Table, Column, String,
                        LargeBinary, Float, ForeignKey, Text, UniqueConstraint)
from sqlalchemy.dialects.mysql import LONGBLOB

metadata = MetaData()
blob = LargeBinary().with_variant(LONGBLOB(), 'mysql')
users = Table('users', metadata,
    Column('id', String(36), primary_key=True),
    Column('username', String(24), unique=True, nullable=False),
    Column('password_hash', String(255), nullable=False))
sessions = Table('sessions', metadata,
    Column('token_hash', String(64), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('expires', Float, nullable=False))
items = Table('vault_items', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('kind', String(20), nullable=False),
    Column('profile_slot', String(36), unique=True),
    Column('category', String(20)),
    Column('created_at', String(40), nullable=False),
    Column('metadata_cipher', blob, nullable=False))
versions = Table('encrypted_versions', metadata,
    Column('item_id', String(36), ForeignKey('vault_items.id', ondelete='CASCADE'), primary_key=True),
    Column('algorithm', String(8), primary_key=True),
    Column('envelope', blob, nullable=False))
benchmarks = Table('benchmarks', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('result', Text, nullable=False))
downloads = Table('download_tests', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('result', Text, nullable=False))
limits = Table('rate_limits', metadata,
    Column('bucket', String(64), primary_key=True),
    Column('window', Float, nullable=False), Column('count', Float, nullable=False))

def database(url):
    engine = create_engine(url, **({'connect_args': {'check_same_thread': False, 'timeout': 30}} if url.startswith('sqlite') else {'pool_pre_ping': True}))
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_config(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA secure_delete=ON')
    metadata.create_all(engine)
    return engine
