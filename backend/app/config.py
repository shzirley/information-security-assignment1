import base64
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

@dataclass(frozen=True)
class Settings:
    database_url: str
    master_key: bytes
    secure_cookie: bool = False
    allowed_origins: tuple[str, ...] = ('http://127.0.0.1:3000', 'http://localhost:3000')
    max_file_bytes: int = 25_000_000
    session_seconds: int = 8 * 60 * 60

    @classmethod
    def from_env(cls):
        try:
            key = base64.b64decode(os.environ['VELTRIX_MASTER_KEY'], validate=True)
            if len(key) != 32:
                raise ValueError()
        except (KeyError, ValueError) as exc:
            raise RuntimeError('Set VELTRIX_MASTER_KEY to a base64-encoded 32-byte secret. Run python setup_env.py.') from exc
        default_db = 'sqlite:///' + str(Path(__file__).resolve().parents[1] / 'data' / 'veltrix.db')
        return cls(os.getenv('DATABASE_URL', default_db), key,
                   os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
                   tuple(x.strip() for x in os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000').split(',')))
