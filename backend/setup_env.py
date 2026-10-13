"""Initialize local configuration once. Never overwrite an existing secret."""
import base64
import secrets
from pathlib import Path
root = Path(__file__).resolve().parent
path = root / '.env'
if path.exists():
    print('backend/.env already exists; kept unchanged.')
else:
    path.write_text('VELTRIX_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode()
        + '\nCOOKIE_SECURE=false\nALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000\n', encoding='utf-8')
    path.chmod(0o600)
    print('Created backend/.env. Keep this secret and back it up with your database.')
frontend_env = root.parent / 'frontend' / '.env.local'
if not frontend_env.exists():
    frontend_env.write_text('NEXT_PUBLIC_API_MODE=live\nAPI_ORIGIN=http://127.0.0.1:8000\n', encoding='utf-8')
    print('Created frontend/.env.local in live mode.')
