"""Cloud configuration must fail closed before connecting to a database."""
import base64
import ssl
import tempfile

import pytest
from pymysql import Connection
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from kyc.cloud import configure_cloud_environment


@pytest.fixture
def cloud_env(monkeypatch, tmp_path):
    certificates = ssl.create_default_context().get_ca_certs(binary_form=True)
    if not certificates:
        pytest.skip('No system CA certificate is available for the TLS configuration test.')
    ca = ssl.DER_cert_to_PEM_cert(certificates[0])
    values = {
        'APP_ENV': 'production',
        'COOKIE_SECURE': 'true',
        'KYC_DATABASE_URL': 'mysql://test_user:p%40ss%3Aword@mysql.example.com:25060/defaultdb',
        'KYC_MYSQL_CA_PEM': ca,
        'VELTRIX_KEK_V1_BASE64': base64.b64encode(b'K' * 32).decode(),
        'VELTRIX_AUTH_SECRET_BASE64': base64.b64encode(b'A' * 32).decode(),
        'ALLOWED_ORIGINS': 'https://veltrix.example.com/, https://other.example.com',
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    original = tempfile.NamedTemporaryFile
    monkeypatch.setattr('kyc.cloud.tempfile.NamedTemporaryFile',
                        lambda **kwargs: original(dir=tmp_path, **kwargs))
    return values, tmp_path


def test_cloud_mysql_uses_verified_tls_and_preserves_keys(cloud_env):
    values, _ = cloud_env
    settings, ca_path = configure_cloud_environment()
    engine = create_engine(settings.database_url)
    try:
        url = make_url(settings.database_url)
        assert url.drivername == 'mysql+pymysql'
        assert url.password == 'p@ss:word'
        assert url.host == 'mysql.example.com'
        assert url.port == 25060
        assert ca_path.read_text(encoding='utf-8') == values['KYC_MYSQL_CA_PEM']
        assert settings.kek == b'K' * 32
        assert settings.auth_secret == b'A' * 32
        assert settings.secure_cookie is True
        assert settings.allowed_origins == ('https://veltrix.example.com', 'https://other.example.com')
        # Construct the actual driver's SSL context without making a network connection.
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        connection = Connection(**kwargs, defer_connect=True)
        assert connection.ctx.check_hostname is True
        assert connection.ctx.verify_mode == ssl.CERT_REQUIRED
    finally:
        engine.dispose()
        ca_path.unlink(missing_ok=True)


@pytest.mark.parametrize(('name', 'value', 'message'), [
    ('KYC_DATABASE_URL', '', 'Missing cloud configuration'),
    ('KYC_MYSQL_CA_PEM', '', 'Missing cloud configuration'),
    ('APP_ENV', 'demo', 'APP_ENV=production'),
    ('COOKIE_SECURE', 'false', 'COOKIE_SECURE=true'),
    ('KYC_DATABASE_URL', 'sqlite:///local.db', 'external MySQL'),
    ('ALLOWED_ORIGINS', 'http://veltrix.example.com', 'exact HTTPS origins'),
    ('ALLOWED_ORIGINS', 'https://*.vercel.app', 'exact HTTPS origins'),
    ('ALLOWED_ORIGINS', 'https://veltrix.example.com/path', 'exact HTTPS origins'),
    ('VELTRIX_KEK_V1_BASE64', 'invalid-key', 'missing/invalid'),
    ('VELTRIX_AUTH_SECRET_BASE64', base64.b64encode(b'K' * 32).decode(), 'distinct 32-byte keys'),
])
def test_cloud_rejects_unsafe_or_incomplete_config(cloud_env, monkeypatch, name, value, message):
    _, temp_directory = cloud_env
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        configure_cloud_environment()
    assert list(temp_directory.iterdir()) == []


def test_cloud_rejects_invalid_ca_before_writing_a_file(cloud_env, monkeypatch):
    _, temp_directory = cloud_env
    monkeypatch.setenv('KYC_MYSQL_CA_PEM', 'not a certificate')
    with pytest.raises(ssl.SSLError):
        configure_cloud_environment()
    assert list(temp_directory.iterdir()) == []
