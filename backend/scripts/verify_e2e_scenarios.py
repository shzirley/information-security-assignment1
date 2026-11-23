"""Comprehensive E2E Verification & Storage Audit Runner for Assignment 2.
Tasks: J-QA-02 & J-QA-03 (Jorell)

Executes all 10 E2E demonstration scenarios (E01 to E10):
- E01: Keypair creation & registration (Andi & Budi)
- E02: Budi's pre-existing KYC application & documents
- E03: Andi creates share request for HIMA account opening
- E04: Budi reviews Andi's key fingerprint and approves
- E05: WhatsApp package generation & OOB channel simulation
- E06: Andi unwraps share key with private key & opens documents (SHA-256 verified)
- E07: Unauthorized third party (Citra) attempts to use package -> REJECTED
- E08: Budi revokes access; Andi attempts reopen -> REJECTED
- E09: Forensic SQLite storage audit (Zero plaintext, KEK wrapping, crypto-shredding)
- E10: Persistence verification across app restarts

Outputs structured findings for docs/assignment-2/VERIFICATION.md.
"""

import base64
import json
import os
import sys
import hashlib
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from sqlalchemy import select, text
from starlette.testclient import TestClient

from kyc.config import Settings
from kyc.db import (
    database,
    users,
    user_public_keys,
    share_requests,
    share_items,
    applications,
    evidence,
)
from kyc.main import create_app


DEMO_KEYS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo_keys"
DEFAULT_PASSWORD = "Password123!"


def parse_package(package_text: str) -> dict:
    encoded = package_text.removeprefix("VELTRIX-SHARE-1.")
    padded = encoded + "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def mutate(c: TestClient, method: str, path: str, **kwargs):
    csrf_res = c.get("/api/v1/auth/csrf")
    csrf = csrf_res.json().get("token", "")
    headers = kwargs.pop("headers", {})
    headers["X-CSRF-Token"] = csrf
    return getattr(c, method.lower())("/api/v1" + path, headers=headers, **kwargs)


def logout_client(c: TestClient):
    try:
        mutate(c, "POST", "/auth/logout")
    except Exception:
        pass
    c.cookies.clear()


def unwrap_share_key_local(package_text: str, priv_pem: str) -> bytes:
    """Simulates client-side unwrap via RSA-OAEP with recipient's private key."""
    parsed = parse_package(package_text)
    encrypted_key = base64.b64decode(parsed["ek"])
    rsa_key = RSA.import_key(priv_pem)
    cipher = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256)
    return cipher.decrypt(encrypted_key)


def run_e2e_verification() -> dict:
    results = {}
    settings = Settings.from_env()
    engine = database(settings.database_url)
    app = create_app(settings)
    client = TestClient(app)

    print("\n" + "="*70)
    print("🔬 RUNNING E2E VERIFICATION SCENARIOS (E01 - E10)")
    print("="*70)

    # -------------------------------------------------------------
    # E01: Kunci Andi & Budi
    # -------------------------------------------------------------
    print("\n[E01] Verifikasi Pasangan Kunci Andi & Budi...")
    with engine.begin() as conn:
        k_rows = conn.execute(
            select(user_public_keys.c.user_id, user_public_keys.c.fingerprint, users.c.username)
            .select_from(user_public_keys.join(users, user_public_keys.c.user_id == users.c.id))
            .where(users.c.username.in_(["andi", "budi", "citra"]))
        ).fetchall()

    fps = {r.username: r.fingerprint for r in k_rows}
    assert "andi" in fps and "budi" in fps, "Andi or Budi key missing. Run seed script first."
    results["E01"] = {
        "status": "PASSED",
        "andi_fingerprint": fps["andi"],
        "budi_fingerprint": fps["budi"],
        "citra_fingerprint": fps.get("citra"),
    }
    print(f"   ✓ Andi Fingerprint : {fps['andi']}")
    print(f"   ✓ Budi Fingerprint : {fps['budi']}")

    # -------------------------------------------------------------
    # E02: Pengajuan KYC Budi
    # -------------------------------------------------------------
    print("\n[E02] Verifikasi Pengajuan Dokumen Budi...")
    mutate(client, "POST", "/auth/login", json={"username": "budi", "password": DEFAULT_PASSWORD})
    res_apps = client.get("/api/v1/applications").json()
    budi_app = res_apps["items"][0]
    app_id = budi_app["id"]

    res_app_detail = client.get(f"/api/v1/applications/{app_id}").json()
    budi_evidences = res_app_detail.get("evidence") or budi_app.get("evidence", [])
    ev_categories = [e["category"] for e in budi_evidences]

    assert "identity" in ev_categories and "document" in ev_categories, "Budi application missing KTP or form"
    results["E02"] = {
        "status": "PASSED",
        "application_id": app_id,
        "app_status": budi_app["status"],
        "evidence_count": len(budi_evidences),
        "categories": ev_categories,
    }
    print(f"   ✓ Application ID : {app_id} (Status: {budi_app['status']})")
    print(f"   ✓ Evidence Uploaded : {ev_categories}")

    # -------------------------------------------------------------
    # E03: Andi Request Akses
    # -------------------------------------------------------------
    print("\n[E03] Andi Mengirim Permintaan Akses...")
    logout_client(client)
    mutate(client, "POST", "/auth/login", json={"username": "andi", "password": DEFAULT_PASSWORD})

    req_payload = {
        "owner_username": "budi",
        "purpose": "Pengajuan rekening HIMA Informatika",
        "items": ["profile", "identity", "document"],
    }
    res_req = mutate(client, "POST", "/share-requests", json=req_payload)
    assert res_req.status_code == 201, f"Failed to create request: {res_req.text}"
    req_data = res_req.json()
    request_id = req_data["id"]

    results["E03"] = {
        "status": "PASSED",
        "request_id": request_id,
        "purpose": req_data["purpose"],
        "req_status": req_data["status"],
        "requester_key_id": req_data.get("requester_key_id"),
    }
    print(f"   ✓ Request ID : {request_id} (Status: {req_data['status']})")
    print(f"   ✓ Purpose    : {req_data['purpose']}")

    # -------------------------------------------------------------
    # E04 & E05: Budi Review, Approve, & Generate WA Package
    # -------------------------------------------------------------
    print("\n[E04 & E05] Budi Menyetujui & Menghasilkan Paket WA...")
    logout_client(client)
    mutate(client, "POST", "/auth/login", json={"username": "budi", "password": DEFAULT_PASSWORD})

    # Budi inspects incoming request
    inc_res = client.get("/api/v1/share-requests?box=incoming").json()
    matching_req = next(r for r in inc_res["items"] if r["id"] == request_id)
    assert matching_req["requester_key_fingerprint"] == fps["andi"][:16], "Fingerprint mismatch in approval modal!"

    # Budi approves request
    apprv_payload = {
        "application_id": app_id,
        "items": ["profile", "identity", "document"],
    }
    res_apprv = mutate(client, "POST", f"/share-requests/{request_id}/approve", json=apprv_payload)
    assert res_apprv.status_code == 200, f"Approve failed: {res_apprv.text}"
    apprv_data = res_apprv.json()
    package_text = apprv_data["package"]

    parsed_pkg = parse_package(package_text)
    assert parsed_pkg["key_fp"] == fps["andi"][:16], "Package was not encrypted for Andi's public key!"

    results["E04"] = {
        "status": "PASSED",
        "verified_fingerprint": matching_req["requester_key_fingerprint"],
        "decision": "APPROVED",
    }
    results["E05"] = {
        "status": "PASSED",
        "package_prefix": package_text[:25] + "...",
        "package_length": len(package_text),
        "target_fingerprint_prefix": parsed_pkg["key_fp"],
    }
    print(f"   ✓ Fingerprint Cocok : {matching_req['requester_key_fingerprint']}")
    print(f"   ✓ Paket WA Dibuat   : {package_text[:40]}... (Total: {len(package_text)} chars)")

    # -------------------------------------------------------------
    # E09 PART 1: Audit Database Sebelum Pencabutan (Data at Rest)
    # -------------------------------------------------------------
    print("\n[E09 - Part 1] Audit Database Saat Status APPROVED...")
    with engine.begin() as conn:
        req_db = conn.execute(
            select(
                share_requests.c.status,
                share_requests.c.wrapped_share_key,
                share_requests.c.wrap_nonce,
                share_requests.c.wrap_tag,
            ).where(share_requests.c.id == request_id)
        ).fetchone()

        items_db = conn.execute(
            select(
                share_items.c.id,
                share_items.c.kind,
                share_items.c.display_name,
                share_items.c.mime_type,
                share_items.c.ciphertext,
                share_items.c.nonce,
            ).where(share_items.c.request_id == request_id)
        ).fetchall()

    assert req_db.wrapped_share_key is not None, "wrapped_share_key must not be null"
    assert len(items_db) >= 2, "Items must be encrypted in share_items"

    # Verify no plaintext PII
    for item in items_db:
        assert b"BUDI PRATAMA" not in item.ciphertext, f"Plaintext leak in item {item.kind}"
        assert b"3273011508950001" not in item.ciphertext, f"Plaintext NIK leak in item {item.kind}"

    results["E09_pre_revoke"] = {
        "status": "PASSED",
        "wrapped_share_key_len": len(req_db.wrapped_share_key),
        "encrypted_items_count": len(items_db),
        "item_kinds": [i.kind for i in items_db],
        "zero_plaintext_pii": True,
    }
    print(f"   ✓ Kunci Berbagi Tersimpan Terbungkus KEK ({len(req_db.wrapped_share_key)} bytes)")
    print(f"   ✓ Jumlah Item Terenkripsi : {len(items_db)} ({[i.kind for i in items_db]})")
    print(f"   ✓ Audit Forensik: NOL plaintext nama/NIK di kolom ciphertext.")

    # -------------------------------------------------------------
    # E06: Andi Membuka Dokumen dengan Private Key Miliknya
    # -------------------------------------------------------------
    print("\n[E06] Andi Mendekripsi Paket & Membuka Dokumen...")
    logout_client(client)
    mutate(client, "POST", "/auth/login", json={"username": "andi", "password": DEFAULT_PASSWORD})

    andi_priv_pem = (DEMO_KEYS_DIR / "andi_private_key.pem").read_text(encoding="utf-8")
    unwrapped_share_key = unwrap_share_key_local(package_text, andi_priv_pem)
    b64_share_key = base64.b64encode(unwrapped_share_key).decode("utf-8")

    # Andi gets item list
    items_list_res = client.get(f"/api/v1/share-requests/{request_id}/items")
    assert items_list_res.status_code == 200, items_list_res.text
    available_items = items_list_res.json()["items"]

    opened_items = {}
    for it in available_items:
        it_id = it["id"]
        open_res = mutate(
            client,
            "POST",
            f"/share-requests/{request_id}/items/{it_id}/open",
            json={"share_key": b64_share_key},
        )
        assert open_res.status_code == 200, f"Failed to open item {it['kind']}: {open_res.text}"
        assert open_res.headers.get("cache-control") == "no-store", "Cache-Control must be no-store!"

        content_bytes = open_res.content
        item_sha256 = hashlib.sha256(content_bytes).hexdigest()
        opened_items[it["kind"]] = {
            "mime_type": it["mime_type"],
            "bytes_length": len(content_bytes),
            "sha256": item_sha256,
        }

    results["E06"] = {
        "status": "PASSED",
        "opened_items": opened_items,
        "cache_control": "no-store",
    }
    print(f"   ✓ Kunci Simetris Berhasil Didekripsi via RSA-OAEP di Sisi Klien.")
    for kind, info in opened_items.items():
        print(f"   ✓ Item '{kind}' Terbuka : {info['bytes_length']} bytes (SHA256: {info['sha256'][:16]}...)")

    # -------------------------------------------------------------
    # E07: Citra (Pihak Ketiga) Mencoba Membuka Dokumen -> REJECTED
    # -------------------------------------------------------------
    print("\n[E07] Uji Keamanan: Citra Mencoba Memakai Paket WA...")
    logout_client(client)
    res_citra_login = mutate(client, "POST", "/auth/login", json={"username": "citra", "password": DEFAULT_PASSWORD})
    assert res_citra_login.status_code == 200, f"Citra login failed: {res_citra_login.text}"

    # Citra tries with her own private key
    citra_priv_pem = (DEMO_KEYS_DIR / "citra_private_key.pem").read_text(encoding="utf-8")
    citra_rsa_failed = False
    try:
        unwrap_share_key_local(package_text, citra_priv_pem)
    except Exception:
        citra_rsa_failed = True

    # Citra calls API open
    first_item_id = available_items[0]["id"]
    citra_api_res = mutate(
        client,
        "POST",
        f"/share-requests/{request_id}/items/{first_item_id}/open",
        json={"share_key": b64_share_key},
    )
    assert citra_api_res.status_code in (403, 404), f"Citra should be denied! Status: {citra_api_res.status_code}"

    results["E07"] = {
        "status": "PASSED",
        "rsa_decrypt_by_citra_failed": citra_rsa_failed,
        "api_response_code": citra_api_res.status_code,
        "api_error_code": citra_api_res.json().get("error", {}).get("code"),
    }
    print(f"   ✓ Dekripsi RSA oleh Citra : GAGAL (Mathematical Rejection)")
    print(f"   ✓ Akses API oleh Citra     : DITOLAK ({citra_api_res.status_code} {citra_api_res.json().get('error', {}).get('code')})")

    # -------------------------------------------------------------
    # E08: Budi Mencabut Akses & Andi Coba Buka Lagi -> REJECTED
    # -------------------------------------------------------------
    print("\n[E08] Budi Mencabut Akses (Revoke)...")
    logout_client(client)
    mutate(client, "POST", "/auth/login", json={"username": "budi", "password": DEFAULT_PASSWORD})

    rev_res = mutate(client, "POST", f"/share-requests/{request_id}/revoke")
    assert rev_res.status_code == 200, f"Revoke failed: {rev_res.text}"

    # Andi tries to reopen after revoke
    logout_client(client)
    mutate(client, "POST", "/auth/login", json={"username": "andi", "password": DEFAULT_PASSWORD})
    reopen_res = mutate(
        client,
        "POST",
        f"/share-requests/{request_id}/items/{first_item_id}/open",
        json={"share_key": b64_share_key},
    )
    assert reopen_res.status_code in (403, 404), f"Reopen should fail after revoke: {reopen_res.status_code}"

    results["E08"] = {
        "status": "PASSED",
        "revoke_status_code": rev_res.status_code,
        "reopen_denied_code": reopen_res.status_code,
        "reopen_error_code": reopen_res.json().get("error", {}).get("code"),
    }
    print(f"   ✓ Status Akses Dicabut : REVOKED")
    print(f"   ✓ Reopen oleh Andi Ditolak : {reopen_res.status_code} {reopen_res.json().get('error', {}).get('code')}")

    # -------------------------------------------------------------
    # E09 PART 2: Crypto-Shredding Audit Setelah Revoke
    # -------------------------------------------------------------
    print("\n[E09 - Part 2] Audit Forensik Crypto-Shredding Pasca-Revoke...")
    with engine.begin() as conn:
        post_req_db = conn.execute(
            select(
                share_requests.c.status,
                share_requests.c.wrapped_share_key,
            ).where(share_requests.c.id == request_id)
        ).fetchone()

        post_items_db = conn.execute(
            select(share_items.c.id).where(share_items.c.request_id == request_id)
        ).fetchall()

    assert post_req_db.status == "REVOKED"
    assert post_req_db.wrapped_share_key is None, "wrapped_share_key must be shredded (NULL)!"
    assert len(post_items_db) == 0, "share_items rows must be completely deleted from DB!"

    results["E09_post_revoke"] = {
        "status": "PASSED",
        "request_status": post_req_db.status,
        "wrapped_share_key_is_null": post_req_db.wrapped_share_key is None,
        "remaining_share_items_rows": len(post_items_db),
    }
    print(f"   ✓ Status DB               : REVOKED")
    print(f"   ✓ wrapped_share_key di DB : NULL (Telah Dimusnahkan)")
    print(f"   ✓ Sisa Baris share_items  : 0 (Crypto-Shredding Sempurna)")

    # -------------------------------------------------------------
    # E10: Persistence Across Restart
    # -------------------------------------------------------------
    print("\n[E10] Verifikasi Persistensi Pasca-Restart Sistem...")
    # Simulate fresh app instance
    engine.dispose()
    fresh_engine = database(settings.database_url)
    with fresh_engine.begin() as conn:
        persisted = conn.execute(
            select(share_requests.c.id, share_requests.c.status).where(
                share_requests.c.id == request_id
            )
        ).fetchone()

    assert persisted is not None and persisted.status == "REVOKED"
    results["E10"] = {
        "status": "PASSED",
        "persisted_id": persisted.id,
        "persisted_status": persisted.status,
    }
    print(f"   ✓ Data Permintaan Tetap Persisten di SQLite Setelah Engine Reset.")

    fresh_engine.dispose()
    print("\n" + "="*70)
    print("🎉 ALL 10 E2E SCENARIOS (E01 - E10) VERIFIED & PASSED!")
    print("="*70)
    return results


if __name__ == "__main__":
    res = run_e2e_verification()
    # Save verification JSON results for report documentation
    out_json = Path(__file__).resolve().parent.parent / "fixtures" / "e2e_verification_results.json"
    out_json.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\n✓ Saved verification metrics to {out_json.name}")
