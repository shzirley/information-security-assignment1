"""Configure the external MySQL deployment without loading local database keys."""
import os
import ssl
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

REQUIRED = ('KYC_DATABASE_URL', 'KYC_MYSQL_CA_PEM', 'VELTRIX_KEK_V1_BASE64',
            'VELTRIX_AUTH_SECRET_BASE64', 'ALLOWED_ORIGINS')


def configure_cloud_environment():
    missing = [name for name in REQUIRED if not os.environ.get(name, '').strip()]
    if missing:
        raise RuntimeError('Missing cloud configuration: ' + ', '.join(missing))
    if os.getenv('APP_ENV') != 'production' or os.getenv('COOKIE_SECURE', '').lower() != 'true':
        raise RuntimeError('Cloud startup requires APP_ENV=production and COOKIE_SECURE=true.')

    url = make_url(os.environ['KYC_DATABASE_URL'])
    if url.drivername not in ('mysql', 'mysql+pymysql') or not url.host or not url.database:
        raise RuntimeError('Cloud startup requires an external MySQL database, not local SQLite.')
    origins = [origin.strip().rstrip('/') for origin in os.environ['ALLOWED_ORIGINS'].split(',')]
    for origin in origins:
        parts = urlsplit(origin)
        if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
                or parts.path or parts.query or parts.fragment or '*' in parts.netloc):
            raise RuntimeError('ALLOWED_ORIGINS must list exact HTTPS origins without paths or wildcards.')

    # Validate keys before creating a CA file or reaching a remote database.
    from .config import Settings
    Settings.from_env()
    ca = os.environ['KYC_MYSQL_CA_PEM'].replace('\\n', '\n')
    ssl.create_default_context(cadata=ca)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='veltrix-ca-', suffix='.pem', delete=False) as handle:
        handle.write(ca)
        ca_path = Path(handle.name)
    ca_path.chmod(0o600)
    url = url.set(drivername='mysql+pymysql', query={
        'charset': 'utf8mb4', 'ssl_ca': str(ca_path),
        # SQLAlchemy folds these into one ssl dictionary for PyMySQL.
        # Mixing in top-level ssl_verify_* options can replace that dictionary
        # and discard the supplied CA/hostname settings in the driver.
        'ssl_check_hostname': 'true', 'connect_timeout': '10',
    })
    os.environ['KYC_DATABASE_URL'] = url.render_as_string(hide_password=False)
    os.environ['ALLOWED_ORIGINS'] = ','.join(origins)
    return Settings.from_env(), ca_path
