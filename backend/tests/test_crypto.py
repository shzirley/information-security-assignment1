import secrets
import pytest
from app.crypto import Crypto, IntegrityError, ALGORITHMS

@pytest.mark.parametrize('algorithm', ALGORITHMS)
@pytest.mark.parametrize('payload', [b'', b'x', b'x' * 16, bytes(range(256)) * 128])
def test_crypto_boundaries(algorithm, payload):
    crypto = Crypto(secrets.token_bytes(32))
    ciphertext = crypto.encrypt(payload, algorithm, 'item-1')
    assert crypto.decrypt(ciphertext, algorithm, 'item-1') == payload
    assert crypto.encrypt(payload, algorithm, 'item-1') != ciphertext
    with pytest.raises(IntegrityError):
        crypto.decrypt(ciphertext, algorithm, 'item-2')
    with pytest.raises(IntegrityError):
        Crypto(secrets.token_bytes(32)).decrypt(ciphertext, algorithm, 'item-1')
    with pytest.raises(IntegrityError):
        crypto.decrypt(ciphertext[:20], algorithm, 'item-1')
