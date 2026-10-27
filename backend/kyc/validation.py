"""In-memory structural validators. No uploaded plaintext written to disk."""
import io
import json
import struct
import subprocess
import warnings
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree
from PIL import Image
from pypdf import PdfReader

RULES = {
    'identity': ({'png', 'jpg', 'jpeg', 'pdf'}, 5 * 1024**2),
    'document': ({'pdf', 'docx'}, 10 * 1024**2),
    'video': ({'mp4'}, 30 * 1024**2),
}
class InvalidFile(ValueError):
    pass

def validate(data, filename, category, ffprobe='ffprobe'):
    extension = filename.rsplit('.', 1)[-1].lower()
    formats, cap = RULES[category]
    if extension not in formats:
        raise InvalidFile('Format tidak sesuai kategori.')
    if not data or len(data) > cap:
        raise InvalidFile('File kosong atau melebihi batas ukuran kategori.')
    try:
        if extension in ('png', 'jpg', 'jpeg'):
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if image.width * image.height > 20_000_000 or image.width < 1 or image.height < 1:
                        raise InvalidFile('Dimensi gambar terlalu besar.')
                    actual = image.format
                    if actual != ('PNG' if extension == 'png' else 'JPEG'):
                        raise InvalidFile('Isi gambar tidak sesuai format.')
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
            return 'image/png' if actual == 'PNG' else 'image/jpeg'
        if extension == 'pdf':
            if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]:
                raise InvalidFile('Struktur PDF tidak valid.')
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= 500:
                raise InvalidFile('PDF terkunci atau jumlah halaman tidak didukung.')
            for page in reader.pages:
                if float(page.mediabox.width) <= 0 or float(page.mediabox.height) <= 0:
                    raise InvalidFile('Ukuran halaman PDF tidak valid.')
            return 'application/pdf'
        if extension == 'docx':
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 1000 or sum(e.file_size for e in entries) > 40 * 1024**2:
                    raise InvalidFile('Batas isi arsip terlampaui.')
                names = [e.filename for e in entries]
                if len(names) != len(set(names)):
                    raise InvalidFile('Nama berulang dalam arsip.')
                for entry in entries:
                    path = PurePosixPath(entry.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename or entry.flag_bits & 1 or 'vbaproject' in entry.filename.lower():
                        raise InvalidFile('Arsip DOCX tidak diizinkan.')
                    if entry.file_size > 10 * 1024**2 or entry.file_size > max(1, entry.compress_size) * 200:
                        raise InvalidFile('Rasio kompresi arsip terlalu besar.')
                for required in ('[Content_Types].xml', '_rels/.rels', 'word/document.xml'):
                    value = archive.read(required)
                    if b'<!DOCTYPE' in value.upper() or b'<!ENTITY' in value.upper():
                        raise InvalidFile('Deklarasi XML tidak diizinkan.')
                    root = ElementTree.fromstring(value)
                    if required == 'word/document.xml' and root.tag != '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document':
                        raise InvalidFile('Dokumen bukan Word OOXML.')
                types = archive.read('[Content_Types].xml')
                if b'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml' not in types:
                    raise InvalidFile('Content type DOCX tidak valid.')
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        # Walk complete MP4 top-level boxes before ffprobe; reject truncated containers.
        cursor, boxes = 0, set()
        while cursor < len(data):
            if cursor + 8 > len(data):
                raise InvalidFile('Kontainer MP4 terpotong.')
            size, kind = struct.unpack('>I4s', data[cursor:cursor+8])
            header_size = 8
            if size == 1:
                if cursor + 16 > len(data):
                    raise InvalidFile('Header MP4 terpotong.')
                size = struct.unpack('>Q', data[cursor+8:cursor+16])[0]
                header_size = 16
            elif size == 0:
                size = len(data) - cursor
            if size < header_size or cursor + size > len(data):
                raise InvalidFile('Ukuran box MP4 tidak valid.')
            boxes.add(kind)
            cursor += size
        if not {b'ftyp', b'moov', b'mdat'} <= boxes:
            raise InvalidFile('MP4 harus memiliki ftyp, moov, dan mdat.')
        result = subprocess.run([ffprobe, '-v', 'error', '-protocol_whitelist', 'pipe', '-i', 'pipe:0',
            '-show_entries', 'format=duration:stream=codec_type,codec_name,duration', '-of', 'json'],
            input=data, capture_output=True, timeout=10, check=True)
        if len(result.stdout) > 65536:
            raise InvalidFile('Metadata MP4 terlalu besar.')
        meta = json.loads(result.stdout)
        video = [s for s in meta.get('streams', []) if s.get('codec_type') == 'video']
        durations = [meta.get('format', {}).get('duration')] + [s.get('duration') for s in video]
        duration = next((float(d) for d in durations if d not in (None, 'N/A')), 0)
        if not video or not 10 <= duration <= 30.1:
            raise InvalidFile('Video harus berdurasi 10–30 detik.')
        return 'video/mp4'
    except InvalidFile:
        raise
    except FileNotFoundError as exc:
        raise RuntimeError('FFPROBE_UNAVAILABLE') from exc
    except Exception as exc:
        raise InvalidFile('Isi file rusak atau tidak sesuai format.') from exc
