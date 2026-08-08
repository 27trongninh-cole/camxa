"""
Core codec for the game's compressed XML resource format used inside .pkg zip archives.

File format for each compressed XML entry:
    bytes[0:4]  = magic constant, little-endian uint32 = 0xEF004A22
    bytes[4:8]  = uncompressed size, little-endian uint32
    bytes[8:]   = zstd frame, compressed using a fixed shared dictionary

The outer .pkg file is itself a standard ZIP archive where every entry is
stored uncompressed (ZIP_STORED) with a fixed timestamp (1980-01-01).
"""
import struct
import zipfile
import io
from pathlib import Path
from functools import lru_cache

import zstandard as zstd

MAGIC = 0xEF004A22
HEADER_SIZE = 8
COMPRESS_LEVEL = 19

DATA_DIR = Path(__file__).parent / "data"
DICT_PATH = DATA_DIR / "zstd_dict.bin"


@lru_cache(maxsize=1)
def _get_dict() -> zstd.ZstdCompressionDict:
    dict_bytes = DICT_PATH.read_bytes()
    return zstd.ZstdCompressionDict(dict_bytes)


def decode_entry(raw: bytes) -> bytes:
    """Decode a raw XML entry (header + zstd frame) into plain XML bytes."""
    if len(raw) < HEADER_SIZE:
        raise ValueError("Entry too short to contain header")
    magic, size = struct.unpack("<II", raw[:HEADER_SIZE])
    if magic != MAGIC:
        raise ValueError(f"Unexpected magic {hex(magic)}, expected {hex(MAGIC)}")
    payload = raw[HEADER_SIZE:]
    dctx = zstd.ZstdDecompressor(dict_data=_get_dict())
    out = dctx.decompress(payload)
    if len(out) != size:
        raise ValueError(f"Decoded size mismatch: header says {size}, got {len(out)}")
    return out


def encode_entry(xml_bytes: bytes) -> bytes:
    """Encode plain XML bytes back into the raw entry format (header + zstd frame)."""
    cctx = zstd.ZstdCompressor(dict_data=_get_dict(), level=COMPRESS_LEVEL)
    compressed = cctx.compress(xml_bytes)
    header = struct.pack("<II", MAGIC, len(xml_bytes))
    return header + compressed


def load_pkg_entries(pkg_bytes: bytes) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
    """Read a .pkg (zip) file, return ordered ZipInfo list and a name->data dict."""
    zf = zipfile.ZipFile(io.BytesIO(pkg_bytes))
    infos = zf.infolist()
    data = {info.filename: zf.read(info.filename) for info in infos}
    return infos, data


def build_pkg(infos: list[zipfile.ZipInfo], data: dict[str, bytes]) -> bytes:
    """Rebuild a .pkg (zip) file preserving original entry order, STORED method,
    and fixed 1980-01-01 timestamp, exactly matching the original archive style."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for info in infos:
            new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
            new_info.compress_type = zipfile.ZIP_STORED
            new_info.external_attr = info.external_attr
            new_info.internal_attr = info.internal_attr
            new_info.create_system = info.create_system
            zf.writestr(new_info, data[info.filename])
    return buf.getvalue()


def patch_pkg_xml(pkg_bytes: bytes, target_filename: str, transform) -> bytes:
    """
    Generic helper: decode target_filename inside the pkg, apply `transform`
    (a function bytes -> bytes on the decoded XML content), re-encode, and
    rebuild the pkg with everything else untouched.
    """
    infos, data = load_pkg_entries(pkg_bytes)
    if target_filename not in data:
        raise ValueError(f"'{target_filename}' not found in package")

    decoded = decode_entry(data[target_filename])
    new_decoded = transform(decoded)
    data[target_filename] = encode_entry(new_decoded)

    return build_pkg(infos, data)
