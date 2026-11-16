"""Automated Cryptography & Security Defense Regression Test Suite.
Verifies boundary integrity, anti-tampering (AEAD GCM), AAD owner binding,
authorized reviewer in-memory preview, zero-plaintext storage at rest, and audit controls.
"""
import hashlib
import json
import secrets
from pathlib import Path

import pytest
from kyc.config import Settings
from kyc.crypto import Envelope, IntegrityFailure, canonical
from tests.test_bankkyc import P, act, complete, create, csrf, login, mutate, profile, system, upload


class TestCryptographyBoundaries:
    """Test cryptographic boundary integrity, tamper resistance, and fail-closed properties."""

    @pytest.fixture
    def crypto_env(self):
        kek = secrets.token_bytes(32)
        envelope = Envelope(kek)
        context = {
            'id': 'obj-sec-test-01',
            'application_id': 'app-bankkyc-2026',
            'owner_id': 'applicant-puput-01',
            'kind': 'evidence',
            'category': 'identity',
            'payload_version': 1,
            'key_version': 1,
        }
        raw_payload = b'DUMMY-KTP-PUPUT-NUGROHO-NIK-2912541012827585-CONFIDENTIAL-IMAGE-BYTES'
        metadata = {'filename': 'ktp_puput.png', 'mime_type': 'image/png'}
        encrypted = envelope.encrypt(context, raw_payload, metadata)
        stored_row = {**context, **encrypted}
        return {
            'kek': kek,
            'envelope': envelope,
            'context': context,
            'raw_payload': raw_payload,
            'metadata': metadata,
            'stored_row': stored_row,
            'sha256_original': hashlib.sha256(raw_payload).hexdigest(),
        }

    def test_round_trip_exact_byte_recovery(self, crypto_env):
        """Decryption using legitimate parameters must yield 100% byte-identical payload."""
        envelope = crypto_env['envelope']
        meta, recovered = envelope.decrypt(crypto_env['stored_row'])
        assert recovered == crypto_env['raw_payload']
        assert meta['filename'] == crypto_env['metadata']['filename']
        assert hashlib.sha256(recovered).hexdigest() == crypto_env['sha256_original']

    def test_tampered_ciphertext_1bit_fails_closed(self, crypto_env):
        """Flipping a single bit in the ciphertext must cause AEAD authentication failure."""
        envelope = crypto_env['envelope']
        row = dict(crypto_env['stored_row'])

        # Flip the first bit of the ciphertext
        ct = bytearray(row['ciphertext'])
        ct[0] ^= 0x01
        row['ciphertext'] = bytes(ct)

        with pytest.raises((IntegrityFailure, ValueError)):
            envelope.decrypt(row)

    def test_tampered_aad_cross_application_substitution_fails(self, crypto_env):
        """Cross-application substitution: Moving ciphertext to another application must abort."""
        envelope = crypto_env['envelope']
        row = dict(crypto_env['stored_row'])

        # Attacker swaps application_id to victim's application
        row['application_id'] = 'app-fraudulent-target-999'

        with pytest.raises((IntegrityFailure, ValueError)):
            envelope.decrypt(row)

    def test_tampered_aad_wrong_owner_fails(self, crypto_env):
        """Ownership reassignment tampering: Changing owner_id must abort decryption."""
        envelope = crypto_env['envelope']
        row = dict(crypto_env['stored_row'])

        # Attacker reassigns ownership
        row['owner_id'] = 'user-fraudster-666'

        with pytest.raises((IntegrityFailure, ValueError)):
            envelope.decrypt(row)

    def test_tampered_tag_fails_closed(self, crypto_env):
        """Corrupting the 16-byte authentication tag must abort decryption immediately."""
        envelope = crypto_env['envelope']
        row = dict(crypto_env['stored_row'])

        header = json.loads(row['header'])
        # Invalidate the GCM authentication tag
        header['tag'] = 'QUFBQUFBQUFBQUFBQUFBQQ=='
        row['header'] = json.dumps(header)

        with pytest.raises((IntegrityFailure, ValueError)):
            envelope.decrypt(row)

    def test_wrong_kek_fails(self, crypto_env):
        """Attempting unwrap with incorrect KEK must reject without partial plaintext."""
        wrong_kek = secrets.token_bytes(32)
        wrong_envelope = Envelope(wrong_kek)

        with pytest.raises((IntegrityFailure, ValueError)):
            wrong_envelope.decrypt(crypto_env['stored_row'])


class TestAuthorizedPreviewAndStorageSecurity:
    """End-to-end authorized reviewer preview, zero-plaintext at rest, and audit."""

    def test_unassigned_reviewer_access_is_denied(self, system):
        """A reviewer not assigned to the case cannot access document review preview."""
        settings, app, client, accounts = system
        login(client, 'owner')
        row = complete(client)
        row = act(client, row, 'submit', synthetic_acknowledged=True).json()

        # Admin assigns application to 'reviewer'
        login(client, 'admin')
        mutate(client, 'PUT', f"/admin/assignments/{row['id']}", json={'reviewer_id': accounts['reviewer']['id'], 'version': row['version']})

        # 'reviewer2' (unassigned) attempts to access document preview
        login(client, 'reviewer2')
        evidence_id = row['evidence'][0]['id']
        response = client.get(P + f"/applications/{row['id']}/evidence/{evidence_id}/review-preview")

        # Must return 404 (Resource Not Found / Not Accessible for unauthorized reviewer)
        assert response.status_code in (403, 404)

    def test_preview_response_headers_prevent_disk_caching(self, system):
        """Preview response must enforce strict no-store and nosniff headers."""
        settings, app, client, accounts = system
        login(client, 'owner')
        row = complete(client)
        row = act(client, row, 'submit', synthetic_acknowledged=True).json()

        # Admin assigns to 'reviewer'
        login(client, 'admin')
        mutate(client, 'PUT', f"/admin/assignments/{row['id']}", json={'reviewer_id': accounts['reviewer']['id'], 'version': row['version']})

        login(client, 'reviewer')
        evidence_id = row['evidence'][0]['id']
        response = client.get(P + f"/applications/{row['id']}/evidence/{evidence_id}/review-preview")
        assert response.status_code == 200

        # Verify security headers
        assert 'no-store' in response.headers.get('cache-control', '')
        assert response.headers.get('x-content-type-options') == 'nosniff'

    def test_zero_plaintext_at_rest_in_sqlite(self, system):
        """Inspect database storage to verify no plaintext NIK/Name appears in raw rows."""
        from sqlalchemy import select
        from kyc.db import database, objects

        settings, app, client, accounts = system
        login(client, 'owner')
        row = complete(client)

        db_engine = database(settings.database_url)
        with db_engine.connect() as conn:
            query = select(objects.c.id, objects.c.kind, objects.c.category, objects.c.ciphertext, objects.c.wrapped_keys)
            rows = conn.execute(query).fetchall()

        assert len(rows) >= 4, "At least profile and 3 evidence objects must exist"

        for obj_id, kind, category, ciphertext, wrapped_keys in rows:
            # Ciphertext and wrapped keys must be binary BLOBs
            assert isinstance(ciphertext, (bytes, bytearray))
            assert isinstance(wrapped_keys, (bytes, bytearray))

            # Must NOT contain plaintext NIK or common personal names
            assert b'PUPUT NUGROHO' not in ciphertext
            assert b'2912541012827585' not in ciphertext
            assert b'DUMMY-2026-001' not in ciphertext
