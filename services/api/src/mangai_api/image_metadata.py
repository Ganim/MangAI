from __future__ import annotations

import struct


def infer_image_dimensions(content: bytes, mime_type: str) -> tuple[int | None, int | None]:
    try:
        if mime_type == "image/png":
            return _read_png_dimensions(content)
        if mime_type == "image/jpeg":
            return _read_jpeg_dimensions(content)
        if mime_type == "image/webp":
            return _read_webp_dimensions(content)
    except Exception:
        return (None, None)
    return (None, None)


def _read_png_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        return (None, None)
    width = int.from_bytes(content[16:20], "big")
    height = int.from_bytes(content[20:24], "big")
    return (width, height)


def _read_jpeg_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 4 or content[:2] != b"\xff\xd8":
        return (None, None)

    index = 2
    while index < len(content):
        while index < len(content) and content[index] == 0xFF:
            index += 1
        if index >= len(content):
            return (None, None)

        marker = content[index]
        index += 1

        if marker in {0xD8, 0xD9}:
            continue
        if index + 1 >= len(content):
            return (None, None)

        segment_length = struct.unpack(">H", content[index : index + 2])[0]
        if segment_length < 2:
            return (None, None)

        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 7 >= len(content):
                return (None, None)
            height = struct.unpack(">H", content[index + 3 : index + 5])[0]
            width = struct.unpack(">H", content[index + 5 : index + 7])[0]
            return (width, height)

        index += segment_length
    return (None, None)


def _read_webp_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 30 or content[:4] != b"RIFF" or content[8:12] != b"WEBP":
        return (None, None)

    chunk_header = content[12:16]
    if chunk_header == b"VP8X" and len(content) >= 30:
        width = 1 + int.from_bytes(content[24:27], "little")
        height = 1 + int.from_bytes(content[27:30], "little")
        return (width, height)

    if chunk_header == b"VP8 " and len(content) >= 30:
        width = struct.unpack("<H", content[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", content[28:30])[0] & 0x3FFF
        return (width, height)

    if chunk_header == b"VP8L" and len(content) >= 25:
        bits = int.from_bytes(content[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return (width, height)

    return (None, None)
