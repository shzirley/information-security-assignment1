"""Seed Script for Assignment 2 Demo (Andi, Budi, Citra).
Task: J-QA-01 (Jorell)

Sets up:
1. Andi (Ketua HIMA - Requester): user account + RSA-2048 keypair
2. Budi (Bendahara HIMA - Owner): user account + RSA-2048 keypair + complete synthetic KYC application
   (Profile, KTP Budi Pratama, Bank Account Opening Form PDF, Verification Video)
3. Citra (Pihak Ketiga / Unauthorized Party): user account + RSA-2048 keypair
4. Saves private keys to backend/fixtures/demo_keys/*.pem for easy browser upload during demo.

Usage:
    python scripts/seed_assignment2_demo.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Crypto.PublicKey import RSA
from sqlalchemy import select, delete
from starlette.testclient import TestClient

from kyc.config import Settings
from kyc.db import (
    database,
    users,
    user_public_keys,
    share_requests,
    share_items,
    applications,
    profiles,
    evidence,
    limits,
)
from kyc.main import create_app


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic_kyc"
DEMO_KEYS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo_keys"
DEFAULT_PASSWORD = "Password123!"


def print_step(title: str):
    print(f"\n{'='*65}\n📌 {title}\n{'='*65}")


def cleanup_existing_demo_users(engine):
    """Cleanly purge previous demo accounts to ensure idempotent re-runs."""
    demo_usernames = ["andi", "budi", "citra"]
    with engine.begin() as conn:
        user_rows = conn.execute(
            select(users.c.id, users.c.username).where(
                users.c.username.in_(demo_usernames)
            )
        ).fetchall()

        user_ids = [row.id for row in user_rows]
        if not user_ids:
            return

        # 1. Clean share_items & share_requests
        req_rows = conn.execute(
            select(share_requests.c.id).where(
                (share_requests.c.requester_id.in_(user_ids))
                | (share_requests.c.owner_id.in_(user_ids))
            )
        ).fetchall()
        req_ids = [r.id for r in req_rows]
        if req_ids:
            conn.execute(delete(share_items).where(share_items.c.request_id.in_(req_ids)))
            conn.execute(delete(share_requests).where(share_requests.c.id.in_(req_ids)))

        # 2. Clean user_public_keys
        conn.execute(delete(user_public_keys).where(user_public_keys.c.user_id.in_(user_ids)))

        # 3. Clean application & personal data & evidence
        app_rows = conn.execute(
            select(applications.c.id).where(applications.c.owner_id.in_(user_ids))
        ).fetchall()
        app_ids = [a.id for a in app_rows]
        if app_ids:
            conn.execute(delete(profiles).where(profiles.c.application_id.in_(app_ids)))
            conn.execute(delete(evidence).where(evidence.c.application_id.in_(app_ids)))
            conn.execute(delete(applications).where(applications.c.id.in_(app_ids)))

        # 4. Clean users
        conn.execute(delete(users).where(users.c.id.in_(user_ids)))

        # 5. Reset rate limits
        conn.execute(delete(limits))

    print("✓ Previous demo data cleaned up successfully.")


def mutate(c: TestClient, method: str, path: str, **kwargs):
    """Helper to perform state-changing requests with CSRF token."""
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


def generate_and_save_keypair(username: str) -> tuple[str, str, Path]:
    """Generate RSA-2048 keypair, export public SPKI PEM and private PKCS#8 PEM."""
    rsa_key = RSA.generate(2048)
    pub_pem = rsa_key.publickey().export_key(format="PEM", pkcs=8).decode("utf-8")
    priv_pem = rsa_key.export_key(format="PEM").decode("utf-8")

    DEMO_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = DEMO_KEYS_DIR / f"{username}_private_key.pem"
    priv_path.write_text(priv_pem, encoding="utf-8")
    return pub_pem, priv_pem, priv_path


def main():
    print("#" * 65)
    print("🚀 VELTRIX BankKYC — Assignment 2 Demo Seeder (J-QA-01)")
    print("   Skenario: Rekening Organisasi Mahasiswa (HIMA Informatika)")
    print("#" * 65)

    settings = Settings.from_env()
    engine = database(settings.database_url)

    # Clean previous demo state
    cleanup_existing_demo_users(engine)

    app = create_app(settings)
    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. SETUP ANDI (KETUA HIMA - PEMINTA DOKUMEN)
    # -------------------------------------------------------------
    print_step("1. Inisialisasi Akun Andi (Ketua HIMA - Peminta)")
    reg_andi = mutate(client, "POST", "/auth/register", json={"username": "andi", "password": DEFAULT_PASSWORD})
    assert reg_andi.status_code == 201, f"Failed to register andi: {reg_andi.text}"
    mutate(client, "POST", "/auth/login", json={"username": "andi", "password": DEFAULT_PASSWORD})

    andi_pub, andi_priv, andi_key_file = generate_and_save_keypair("andi")
    res_andi_key = mutate(client, "PUT", "/keys/me", json={"public_key_pem": andi_pub})
    assert res_andi_key.status_code == 200, f"Failed to register andi key: {res_andi_key.text}"
    andi_fp = res_andi_key.json()["fingerprint"]
    print(f"✓ Akun 'andi' aktif (Password: {DEFAULT_PASSWORD})")
    print(f"✓ Kunci Publik didaftarkan ke server (Fingerprint: {andi_fp})")
    print(f"✓ Kunci Privat disimpan di file: {andi_key_file.relative_to(Path.cwd())}")

    # -------------------------------------------------------------
    # 2. SETUP BUDI (BENDAHARA HIMA - PEMILIK DATA)
    # -------------------------------------------------------------
    print_step("2. Inisialisasi Akun Budi (Bendahara HIMA - Pemilik Data)")
    logout_client(client)
    reg_budi = mutate(client, "POST", "/auth/register", json={"username": "budi", "password": DEFAULT_PASSWORD})
    assert reg_budi.status_code == 201, f"Failed to register budi: {reg_budi.text}"
    mutate(client, "POST", "/auth/login", json={"username": "budi", "password": DEFAULT_PASSWORD})

    budi_pub, budi_priv, budi_key_file = generate_and_save_keypair("budi")
    res_budi_key = mutate(client, "PUT", "/keys/me", json={"public_key_pem": budi_pub})
    assert res_budi_key.status_code == 200, f"Failed to register budi key: {res_budi_key.text}"
    budi_fp = res_budi_key.json()["fingerprint"]
    print(f"✓ Akun 'budi' aktif (Password: {DEFAULT_PASSWORD})")
    print(f"✓ Kunci Publik didaftarkan ke server (Fingerprint: {budi_fp})")
    print(f"✓ Kunci Privat disimpan di file: {budi_key_file.relative_to(Path.cwd())}")

    # Create Budi's KYC Application
    print("\n   Mengunggah Dokumen KYC Budi Pratama (Bendahara HIMA)...")
    res_app = mutate(client, "POST", "/applications", json={})
    assert res_app.status_code == 201, res_app.text
    budi_app = res_app.json()
    app_id = budi_app["id"]

    # 2.1 Personal Data Profile
    curr_ver = client.get(f"/api/v1/applications/{app_id}").json()["version"]
    res_prof = mutate(
        client,
        "PUT",
        f"/applications/{app_id}/personal-data",
        json={
            "version": curr_ver,
            "profile": {
                "full_name": "BUDI PRATAMA",
                "identity_number": "DUMMY-3273-011508-0001",
                "date_of_birth": "1995-08-17",
                "email": "budi.pratama@example.org",
                "phone": "080012345678",
                "address": "JL. DIPONEGORO NO. 45, BANDUNG",
                "occupation": "MAHASISWA (BENDAHARA HIMA)",
                "account_purpose": "REKENING OPERASIONAL ORGANISASI MAHASISWA",
            },
        },
    )
    assert res_prof.status_code == 200, f"Failed to save profile: {res_prof.text}"
    print("   ✓ Profil personal data tersimpan & terenkripsi.")

    # 2.2 Upload KTP Budi Pratama
    ktp_path = FIXTURES_DIR / "ktp_budi_pratama.png"
    if ktp_path.exists():
        curr_ver = client.get(f"/api/v1/applications/{app_id}").json()["version"]
        with open(ktp_path, "rb") as f:
            res_ktp = mutate(
                client,
                "POST",
                f"/applications/{app_id}/evidence",
                data={"category": "identity", "document_type": "ktp", "version": str(curr_ver)},
                files={"file": ("ktp_budi_pratama.png", f.read(), "image/png")},
            )
        assert res_ktp.status_code == 201, f"Failed to upload KTP: {res_ktp.text}"
        print("   ✓ Dokumen KTP (ktp_budi_pratama.png) berhasil diunggah & terenkripsi.")

    # 2.3 Upload Bank Account Form Budi
    form_path = FIXTURES_DIR / "bank_account_form_budi.pdf"
    if form_path.exists():
        curr_ver = client.get(f"/api/v1/applications/{app_id}").json()["version"]
        with open(form_path, "rb") as f:
            res_form = mutate(
                client,
                "POST",
                f"/applications/{app_id}/evidence",
                data={"category": "document", "document_type": "account_opening_form", "version": str(curr_ver)},
                files={"file": ("bank_account_form_budi.pdf", f.read(), "application/pdf")},
            )
        assert res_form.status_code == 201, f"Failed to upload form: {res_form.text}"
        print("   ✓ Formulir Pembukaan Rekening (bank_account_form_budi.pdf) berhasil diunggah & terenkripsi.")

    # 2.4 Upload Video Demo (optional - requires ffmpeg/ffprobe)
    video_path = Path(__file__).resolve().parent.parent / "fixtures" / "verification-demo.mp4"
    if video_path.exists():
        try:
            curr_ver = client.get(f"/api/v1/applications/{app_id}").json()["version"]
            with open(video_path, "rb") as f:
                res_vid = mutate(
                    client,
                    "POST",
                    f"/applications/{app_id}/evidence",
                    data={"category": "video", "document_type": "verification_video", "version": str(curr_ver)},
                    files={"file": ("verification-demo.mp4", f.read(), "video/mp4")},
                )
            if res_vid.status_code == 201:
                print("   ✓ Video verifikasi sintetis berhasil diunggah & terenkripsi.")
            else:
                print(f"   ℹ Lewati upload video (status {res_vid.status_code}): validator memerlukan ffprobe.")
        except Exception as e:
            print(f"   ℹ Lewati upload video: {e}")

    # 2.5 Submit Application
    with engine.begin() as conn:
        conn.execute(applications.update().where(applications.c.id == app_id).values(status="SUBMITTED"))
    print("   ✓ Status pengajuan Budi: 'SUBMITTED' (Siap dibagikan).")

    # -------------------------------------------------------------
    # 3. SETUP CITRA (PIHAK KETIGA / MAHASISWA LAIN)
    # -------------------------------------------------------------
    print_step("3. Inisialisasi Akun Citra (Pihak Ketiga / Unauthorized Party)")
    logout_client(client)
    reg_citra = mutate(client, "POST", "/auth/register", json={"username": "citra", "password": DEFAULT_PASSWORD})
    assert reg_citra.status_code == 201, f"Failed to register citra: {reg_citra.text}"
    mutate(client, "POST", "/auth/login", json={"username": "citra", "password": DEFAULT_PASSWORD})

    citra_pub, citra_priv, citra_key_file = generate_and_save_keypair("citra")
    res_citra_key = mutate(client, "PUT", "/keys/me", json={"public_key_pem": citra_pub})
    assert res_citra_key.status_code == 200, f"Failed to register citra key: {res_citra_key.text}"
    citra_fp = res_citra_key.json()["fingerprint"]
    print(f"✓ Akun 'citra' aktif (Password: {DEFAULT_PASSWORD})")
    print(f"✓ Kunci Publik didaftarkan ke server (Fingerprint: {citra_fp})")
    print(f"✓ Kunci Privat disimpan di file: {citra_key_file.relative_to(Path.cwd())}")

    engine.dispose()

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print_step("RINGKASAN SEEDING SELESAI (SIAP DEMO)")
    print(f"""
Akun Demo Siap Pakai:
-----------------------------------------------------------------
1. ANDI  (Ketua HIMA - Peminta)
   - Username: andi
   - Password: {DEFAULT_PASSWORD}
   - Private Key: backend/fixtures/demo_keys/andi_private_key.pem
   - Fingerprint: {andi_fp}

2. BUDI  (Bendahara HIMA - Pemilik Data)
   - Username: budi
   - Password: {DEFAULT_PASSWORD}
   - Application ID: {app_id}
   - Dokumen: Profil, KTP (Budi Pratama), Formulir Rekening HIMA, Video
   - Private Key: backend/fixtures/demo_keys/budi_private_key.pem
   - Fingerprint: {budi_fp}

3. CITRA (Pihak Ketiga - Penyerang/Unauthorized Party)
   - Username: citra
   - Password: {DEFAULT_PASSWORD}
   - Private Key: backend/fixtures/demo_keys/citra_private_key.pem
   - Fingerprint: {citra_fp}
-----------------------------------------------------------------
Semua kunci privat `.pem` tersimpan aman di folder `backend/fixtures/demo_keys/`.
""")


if __name__ == "__main__":
    main()
