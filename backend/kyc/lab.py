"""Real randomized measurements against isolated, reproducible synthetic fixtures."""
import hashlib
import io
import json
import platform
import secrets
import statistics
import time
from importlib.metadata import version
from pathlib import Path
from Crypto.Cipher import AES, DES, ARC4
from Crypto.Util.Padding import pad, unpad
from PIL import Image
from pypdf import PdfWriter
from .crypto import canonical, SUITE, DROP

FIXTURE_PROFILE = {'full_name': 'Nara Contoh', 'identity_number': 'DUMMY-2026-001', 'date_of_birth': '2000-01-15',
    'email': 'nara@example.com', 'phone': '080000000001', 'address': 'Jalan Simulasi 12', 'occupation': 'Desainer fiktif', 'account_purpose': 'Tabungan simulasi'}
ALGORITHMS = ('AES-256-GCM', 'DES-CBC', 'RC4', 'Pipeline berlapis')

def fixture_bytes(name):
    if name == 'personal-json':
        return canonical(FIXTURE_PROFILE)
    if name == 'identity-png':
        from PIL import ImageDraw
        image = Image.new('RGB', (640, 360), '#e0f1ff')
        ImageDraw.Draw(image).text((40, 120), 'DUMMY IDENTITY - NARA CONTOH - NOT REAL', fill='#143355')
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    if name == 'document-pdf':
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.add_metadata({'/Title': 'DUMMY account form - synthetic fixture'})
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    if name == 'video-mp4':
        return (Path(__file__).resolve().parents[1] / 'fixtures' / 'verification-demo.mp4').read_bytes()
    raise ValueError('Unknown fixture')

def measure(body, settings):
    data = fixture_bytes(body.fixture)
    samples, order_history = [], []
    for trial in range(-body.warmups + 1, body.repetitions + 1):
        order = list(ALGORITHMS)
        secrets.SystemRandom().shuffle(order)
        if trial > 0:
            order_history.append(order)
        for position, algorithm in enumerate(order):
            aes_key, des_key, rc4_key = secrets.token_bytes(32), secrets.token_bytes(8), secrets.token_bytes(32)
            iv, nonce = secrets.token_bytes(8), secrets.token_bytes(12)
            start = time.perf_counter_ns()
            if algorithm == 'AES-256-GCM':
                cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=16)
                encrypted, tag = cipher.encrypt_and_digest(data)
            elif algorithm == 'DES-CBC':
                encrypted = DES.new(des_key, DES.MODE_CBC, iv=iv).encrypt(pad(data, 8))
            elif algorithm == 'RC4':
                encrypted = ARC4.new(rc4_key, drop=DROP).encrypt(data)
            else:
                intermediate = ARC4.new(rc4_key, drop=DROP).encrypt(data)
                intermediate = DES.new(des_key, DES.MODE_CBC, iv=iv).encrypt(pad(intermediate, 8))
                cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=16)
                encrypted, tag = cipher.encrypt_and_digest(intermediate)
            encrypt_ns = time.perf_counter_ns() - start
            start = time.perf_counter_ns()
            if algorithm == 'AES-256-GCM':
                recovered = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=16).decrypt_and_verify(encrypted, tag)
            elif algorithm == 'DES-CBC':
                recovered = unpad(DES.new(des_key, DES.MODE_CBC, iv=iv).decrypt(encrypted), 8)
            elif algorithm == 'RC4':
                recovered = ARC4.new(rc4_key, drop=DROP).decrypt(encrypted)
            else:
                intermediate = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=16).decrypt_and_verify(encrypted, tag)
                intermediate = unpad(DES.new(des_key, DES.MODE_CBC, iv=iv).decrypt(intermediate), 8)
                recovered = ARC4.new(rc4_key, drop=DROP).decrypt(intermediate)
            decrypt_ns = time.perf_counter_ns() - start
            start = time.perf_counter_ns()
            correct = recovered == data
            correctness_ns = time.perf_counter_ns() - start
            extra = {'AES-256-GCM': 28, 'DES-CBC': 8, 'RC4': 0, 'Pipeline berlapis': 36}[algorithm]
            if trial > 0:
                samples.append(dict(trial=trial, algorithm=algorithm, execution_order=position+1, encrypt_ns=encrypt_ns,
                    decrypt_ns=decrypt_ns, correctness_ns=correctness_ns, overhead_bytes=len(encrypted)+extra-len(data),
                    ciphertext_bytes=len(encrypted), round_trip_ok=correct))
    rows = []
    for algorithm in ALGORITHMS:
        entries = [s for s in samples if s['algorithm'] == algorithm]
        encrypt = [s['encrypt_ns'] for s in entries]
        decrypt = [s['decrypt_ns'] for s in entries]
        q1, _, q3 = statistics.quantiles(encrypt, n=4, method='inclusive')
        rows.append(dict(algorithm=algorithm, encrypt_ms=statistics.median(encrypt)/1e6,
            decrypt_ms=statistics.median(decrypt)/1e6, iqr_ms=(q3-q1)/1e6,
            encrypt_sd_ms=statistics.stdev(encrypt)/1e6, decrypt_sd_ms=statistics.stdev(decrypt)/1e6,
            overhead_bytes=entries[0]['overhead_bytes'], round_trip_ok=all(e['round_trip_ok'] for e in entries),
            throughput_mib_s=(len(data)/1024**2)/(statistics.median(encrypt)/1e9) if statistics.median(encrypt) else None))
    return dict(kind=body.kind, fixture=body.fixture, fixture_sha256=hashlib.sha256(data).hexdigest(), input_bytes=len(data),
        repetitions=body.repetitions, warmups=body.warmups, status='completed', simulated=False, rows=rows, samples=samples,
        methodology_version='vtx-cipher-core-v1', suite=SUITE,
        environment=dict(python=platform.python_version(), platform=platform.platform(), machine=platform.machine(),
            pycryptodome=version('pycryptodome'), fastapi=version('fastapi'), sqlalchemy=version('SQLAlchemy'),
            timer='perf_counter_ns', timer_resolution_seconds=time.get_clock_info('perf_counter').resolution,
            quartiles='inclusive', execution_order=order_history, rc4_drop=DROP,
            timer_scope='cipher construction + padding + cipher transform + GCM tag; excludes RNG, operational private packing/AAD, key wrapping, JSON, HTTP and DB',
            overhead_scope='binary ciphertext + nonce/tag/IV, excludes operational envelope/header/wrapped keys',
            video_scope='small frontend smoke fixture; not representative of 10-30 MiB video',
            peak_memory_bytes=None, peak_memory_reason='native allocations not measured'))
