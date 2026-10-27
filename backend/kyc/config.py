"""BankKYC settings; separate keys and database from the legacy vault."""
import base64
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    database_url: str
    kek: bytes
    auth_secret: bytes
    secure_cookie: bool = False
    allowed_origins: tuple[str, ...] = ('http://127.0.0.1:3000', 'http://localhost:3000')
    session_seconds: int = 28800
    max_request_bytes: int = 34 * 1024**2
    ffprobe: str = 'ffprobe'

    def __post_init__(self):
        if len(self.kek) != 32 or len(self.auth_secret) != 32 or self.kek == self.auth_secret:
            raise RuntimeError('BankKYC requires two distinct 32-byte keys.')

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / '.env')
        def key(name):
            try:
                value = base64.b64decode(os.environ[name], validate=True)
                if len(value) != 32:
                    raise ValueError()
                return value
            except (KeyError, ValueError) as exc:
                raise RuntimeError(f'{name} missing/invalid. Run python setup_env.py; retain existing keys.') from exc
        return cls(
            os.getenv('KYC_DATABASE_URL', 'sqlite:///' + str(ROOT / 'data' / 'bankkyc.db')),
            key('VELTRIX_KEK_V1_BASE64'), key('VELTRIX_AUTH_SECRET_BASE64'),
            os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
            tuple(x.strip() for x in os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000').split(',')),
            ffprobe=os.getenv('FFPROBE_PATH', 'ffprobe'))
