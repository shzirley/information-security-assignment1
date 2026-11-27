"""Caca's Assignment 3 schema and API-boundary checks (synthetic users only)."""
import base64
import secrets

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from test_bankkyc import P, login, mutate, system
from kyc.config import Settings
from kyc.db import (database, metadata, users, user_signing_keys,
    signing_key_challenges, pki_authority, signature_sessions, document_signatures)
from kyc.migrate import migrate


NEW_TABLES = (user_signing_keys, signing_key_challenges, pki_authority,
              signature_sessions, document_signatures)


def test_0004_fresh_install_and_upgrade_from_assignment_2(tmp_path):
    settings = Settings('sqlite:///' + str(tmp_path / 'fresh.db'),
                        secrets.token_bytes(32), secrets.token_bytes(32))
    engine = database(settings.database_url)
    migrate(engine, settings)
    with database(settings.database_url).connect() as connection:
        assert all(t.name in connection.dialect.get_table_names(connection) for t in NEW_TABLES)

    upgrade_url = 'sqlite:///' + str(tmp_path / 'upgrade.db')
    engine = database(upgrade_url)
    config = Config(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '0003_data_sharing')
        # 0001 creates live metadata; emulate a real database from Assignment 2.
        for table in reversed(NEW_TABLES):
            table.drop(connection, checkfirst=True)
        connection.execute(users.insert().values(id='old-applicant', username='old_applicant',
            display_name='old_applicant', password_hash='synthetic', role='applicant',
            is_active=True, created_at='2026-01-01T00:00:00+00:00'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        assert connection.execute(select(users.c.username).where(users.c.id == 'old-applicant')).scalar_one() == 'old_applicant'
        assert all(t.name in connection.dialect.get_table_names(connection) for t in NEW_TABLES)
    engine.dispose()


def test_signing_challenge_is_private_and_random(system):
    _, app, client, _ = system
    assert client.get(P + '/signing-keys/me').status_code == 401
    login(client, 'owner')
    assert client.get(P + '/signing-keys/me').json() == {'active': None, 'history': []}
    first = mutate(client, 'POST', '/signing-keys/challenge')
    second = mutate(client, 'POST', '/signing-keys/challenge')
    assert first.status_code == second.status_code == 201
    assert first.json()['challenge'] != second.json()['challenge']
    assert len(base64.b64decode(first.json()['challenge'])) == 32
    with app.state.engine.connect() as connection:
        assert connection.execute(select(signing_key_challenges.c.id)).first() is not None
    login(client, 'reviewer')
    assert mutate(client, 'POST', '/signing-keys/challenge').status_code == 403


def test_partial_unique_signing_key_index_is_sqlite_only():
    from sqlalchemy import create_mock_engine
    from sqlalchemy.schema import CreateIndex
    for dialect, expected in (('sqlite://', True), ('mysql+pymysql://', False)):
        statements = []
        engine = create_mock_engine(dialect, lambda sql, *a, **k: statements.append(sql))
        metadata.create_all(engine, tables=[user_signing_keys], checkfirst=False)
        created = [s.element.name for s in statements if isinstance(s, CreateIndex)]
        assert ('uq_user_signing_keys_active' in created) is expected
