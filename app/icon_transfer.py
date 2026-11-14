"""Private icon atlas layout and CRC codec."""
import struct, hashlib, json
from pathlib import Path
from PIL import Image
from firmware import tile

BASE = 0x00A80000
CAPACITY = 0x60000
REGION = 0x20000
WIDTH, HEIGHT = 320, 480
TILE_BYTES = 60*69*2
PIXEL_PADDING = 5  # 11-byte transport header + 5 bytes = 4-byte aligned icon start
ICON_DATA_OFFSET = 11 + PIXEL_PADDING


def crc16(data, initial=0xffff):
    crc=initial
    for b in data:
        crc ^= b
        for _ in range(8):crc=(crc>>1)^0xa001 if crc&1 else crc>>1
    return crc


def make_atlas(rows, icons):
    if len(rows)!=11 or len(icons)!=11:raise ValueError('아이콘 11개가 필요합니다.')
    from firmware import encode_icon
    pixels=bytearray(PIXEL_PADDING)
    for row,icon in zip(rows,icons):
        pixels+=encode_icon(tile(row,icon))
    pixels.extend(bytes(WIDTH*HEIGHT*2-len(pixels)))
    return struct.pack('<IHHBH',len(pixels),WIDTH,HEIGHT,0,crc16(pixels))+pixels

