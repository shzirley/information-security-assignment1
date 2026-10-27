"""Local operator commands; no role escalation API and no shared default passwords."""
import argparse
import getpass
import json
import os
import secrets
import sqlite3
import subprocess
import sys
from pathlib import Path
from sqlalchemy import select, update, delete, insert, func
from kyc.config import Settings, ROOT
from kyc.db import database, users, sessions, applications, objects, evidence, profiles, events, assignments, security_log
from kyc.migrate import migrate
from kyc.provision import check_keys, create_user
from kyc.main import now, uid

parser = argparse.ArgumentParser(description='VELTRIX BankKYC operations')
commands = parser.add_subparsers(dest='command', required=True)
commands.add_parser('migrate')
create = commands.add_parser('create-user')
create.add_argument('username')
create.add_argument('--role', choices=['applicant', 'reviewer', 'admin', 'evaluator'], default='applicant')
create.add_argument('--display-name')
commands.add_parser('demo-users', help='Explicit local demo only, random credentials saved on this computer')
disable = commands.add_parser('disable-user')
disable.add_argument('username')
backup = commands.add_parser('backup')
backup.add_argument('destination', help='New output path; never overwrites an existing backup')
cleanup = commands.add_parser('cleanup-case')
cleanup.add_argument('case_id')
cleanup.add_argument('--apply', action='store_true')
commands.add_parser('openapi')
args = parser.parse_args()
settings = Settings.from_env()
engine = database(settings.database_url)
if args.command == 'migrate':
    migrate(engine, settings)
    print('Database migration complete.')
    sys.exit(0)
check_keys(engine, settings)
if args.command == 'create-user':
    password = getpass.getpass('Password (min. 8 characters): ')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match.')
    account = create_user(engine, args.username, password, args.role, args.display_name)
    print('Created', account['username'], 'role:', account['role'])
elif args.command == 'demo-users':
    if os.getenv('APP_ENV') != 'demo':
        raise SystemExit('Demo users require APP_ENV=demo. Do not run on production.')
    path = ROOT / 'data' / 'demo-accounts.txt'
    lines = []
    for name, role in [('demo_user', 'applicant'), ('reviewer_demo', 'reviewer'), ('reviewer_other', 'reviewer'), ('admin_demo', 'admin'), ('evaluator_demo', 'evaluator')]:
        with engine.connect() as connection:
            exists = connection.execute(select(users.c.id).where(users.c.username == name)).first()
        if exists:
            continue
        password = secrets.token_urlsafe(15)
        create_user(engine, name, password, role)
        lines.append(f'{role:10} username={name:16} password={password}')
    if lines:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')
        path.chmod(0o600)
    if path.exists():
        print('LOCAL DEMO ACCOUNTS (also saved in backend/data/demo-accounts.txt):')
        print(path.read_text(encoding='utf-8'))
    else:
        print('Accounts already exist; existing passwords were not changed.')
elif args.command == 'disable-user':
    with engine.begin() as connection:
        user_id = connection.execute(select(users.c.id).where(users.c.username == args.username)).scalar_one()
        connection.execute(update(users).where(users.c.id == user_id).values(is_active=False))
        connection.execute(delete(sessions).where(sessions.c.user_id == user_id))
        connection.execute(insert(security_log).values(id=uid(), at=now(), actor_id=user_id, action='operator_disabled_user'))
    print('Account disabled; sessions revoked.')
elif args.command == 'backup':
    destination = Path(args.destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SystemExit('Backup destination already exists; choose a new path.')
    if engine.dialect.name != 'sqlite':
        raise SystemExit('For MySQL use mysqldump --single-transaction --hex-blob (see README).')
    # SQLite backup API is consistent even with a live WAL; copying .db alone is unsafe.
    destination.touch(exist_ok=False)
    source = sqlite3.connect(engine.url.database)
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()
    destination.chmod(0o600)
    print('Database backup saved. Copy backend/.env separately to a protected location.')
elif args.command == 'cleanup-case':
    with engine.begin() as connection:
        row = connection.execute(select(applications).where(applications.c.id == args.case_id).with_for_update()).mappings().first()
        if row is None:
            raise SystemExit('Case does not exist.')
        count = connection.execute(select(func.count()).select_from(objects).where(objects.c.application_id == args.case_id)).scalar_one()
        print(json.dumps({'case_id': args.case_id, 'encrypted_objects': count, 'apply': args.apply}))
        if args.apply:
            if os.getenv('APP_ENV') != 'demo':
                raise SystemExit('Cleanup is restricted to APP_ENV=demo.')
            connection.execute(delete(applications).where(applications.c.id == args.case_id))
            connection.execute(insert(security_log).values(id=uid(), at=now(), action='operator_case_cleanup', resource_id=args.case_id))
            print('Case and all related versions/events/assignments removed. Existing backups are unchanged.')
elif args.command == 'openapi':
    from kyc.main import create_app
    output = ROOT / 'openapi.json'
    output.write_text(json.dumps(create_app(settings).openapi(), indent=2), encoding='utf-8')
    print('Wrote backend/openapi.json')
engine.dispose()
