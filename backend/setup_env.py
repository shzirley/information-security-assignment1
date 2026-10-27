"""Create missing local keys once. Existing values are never overwritten."""
import argparse
import base64
import secrets
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Explicitly connect the frontend to the BankKYC backend')
args = parser.parse_args()
path = root / '.env'
values = dotenv_values(path) if path.exists() else {}
required = ('VELTRIX_KEK_V1_BASE64', 'VELTRIX_AUTH_SECRET_BASE64')
if any(not values.get(name) for name in required) and (root / 'data' / 'bankkyc.db').exists():
    raise SystemExit('Database already exists but keys are missing. Restore the original .env; do not generate new keys.')
additions = {}
for name in required:
    if not values.get(name):
        additions[name] = base64.b64encode(secrets.token_bytes(32)).decode()
for name, value in {'APP_ENV': 'demo', 'COOKIE_SECURE': 'false', 'ALLOWED_ORIGINS': 'http://127.0.0.1:3000,http://localhost:3000'}.items():
    if name not in values:
        additions[name] = value
if additions:
    previous = path.read_text(encoding='utf-8') if path.exists() else ''
    path.write_text(previous.rstrip() + '\n' + ''.join(f'{k}={v}\n' for k, v in additions.items()), encoding='utf-8')
    path.chmod(0o600)
print('BankKYC configuration ready. Keep backend/.env and back it up separately from the database.')
if args.live:
    frontend = root.parent / 'frontend' / '.env.local'
    lines = frontend.read_text(encoding='utf-8').splitlines() if frontend.exists() else []
    lines = [line for line in lines if not line.startswith(('NEXT_PUBLIC_API_MODE=', 'API_ORIGIN='))]
    lines += ['NEXT_PUBLIC_API_MODE=live', 'API_ORIGIN=http://127.0.0.1:8000']
    frontend.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Frontend connected in live mode; restart/rebuild Next.js after configuration changes.')
