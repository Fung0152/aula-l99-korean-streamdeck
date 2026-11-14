"""Windows shell icon extraction and code-rendered fallback icons."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
from PIL import Image, ImageDraw, ImageOps


def fallback(web=False):
    im = Image.new('RGBA', (64,64), 'white')
    d = ImageDraw.Draw(im)
    if web:
        d.ellipse((9,9,55,55), outline='#4079db', width=3)
        d.ellipse((23,9,41,55), outline='#4079db', width=2)
        d.line((10,32,54,32), fill='#4079db', width=2)
        d.arc((10,18,54,46), 0, 360, fill='#4079db', width=2)
    else:
        d.rounded_rectangle((13,9,51,55), radius=6, fill='#eef1f8', outline='#8d9ab0', width=2)
        for y in (24,33,42):
            d.line((22,y,43,y), fill='#8d9ab0', width=2)
    return im


def shell_icon(path, size=64):
    class SHFILEINFO(C.Structure):
        _fields_=[('hIcon',W.HICON),('iIcon',C.c_int),('dwAttributes',W.DWORD),('szDisplayName',W.WCHAR*260),('szTypeName',W.WCHAR*80)]
    class BIH(C.Structure):
        _fields_=[('biSize',W.DWORD),('biWidth',W.LONG),('biHeight',W.LONG),('biPlanes',W.WORD),('biBitCount',W.WORD),('biCompression',W.DWORD),('biSizeImage',W.DWORD),('biXPelsPerMeter',W.LONG),('biYPelsPerMeter',W.LONG),('biClrUsed',W.DWORD),('biClrImportant',W.DWORD)]
    shell=C.WinDLL('shell32');g=C.WinDLL('gdi32');u=C.WinDLL('user32')
    shell.SHGetFileInfoW.argtypes=[W.LPCWSTR,W.DWORD,C.POINTER(SHFILEINFO),W.UINT,W.UINT];shell.SHGetFileInfoW.restype=C.c_size_t
    g.CreateCompatibleDC.argtypes=[W.HDC];g.CreateCompatibleDC.restype=W.HDC
    g.CreateDIBSection.argtypes=[W.HDC,C.c_void_p,W.UINT,C.POINTER(C.c_void_p),W.HANDLE,W.DWORD];g.CreateDIBSection.restype=W.HBITMAP
    g.SelectObject.argtypes=[W.HDC,W.HGDIOBJ];g.SelectObject.restype=W.HGDIOBJ
    g.DeleteObject.argtypes=[W.HGDIOBJ];g.DeleteDC.argtypes=[W.HDC]
    u.DrawIconEx.argtypes=[W.HDC,C.c_int,C.c_int,W.HICON,C.c_int,C.c_int,W.UINT,W.HBRUSH,W.UINT]
    u.DestroyIcon.argtypes=[W.HICON]
    info=SHFILEINFO()
    if not shell.SHGetFileInfoW(str(Path(path)),0,C.byref(info),C.sizeof(info),0x100):
        return fallback()
    dc=None;bitmap=None;old=None
    try:
        dc=g.CreateCompatibleDC(None);bits=C.c_void_p()
        header=BIH(C.sizeof(BIH),size,-size,1,32,0,size*size*4,0,0,0,0)
        bitmap=g.CreateDIBSection(dc,C.byref(header),0,C.byref(bits),None,0)
        if not bitmap or not bits.value:
            return fallback()
        old=g.SelectObject(dc,bitmap)
        C.memset(bits,255,size*size*4)
        if not u.DrawIconEx(dc,0,0,info.hIcon,size,size,0,None,3):
            return fallback()
        # A white opaque backing also handles icons without an alpha channel.
        return Image.frombytes('RGB',(size,size),C.string_at(bits,size*size*4),'raw','BGRX').convert('RGBA')
    finally:
        if old:g.SelectObject(dc,old)
        if bitmap:g.DeleteObject(bitmap)
        if dc:g.DeleteDC(dc)
        u.DestroyIcon(info.hIcon)


def get_icon(row):
    if row.get('icon'):
        with Image.open(row['icon']) as image:
            if image.width*image.height > 25000000:
                raise ValueError('아이콘 이미지는 2500만 화소 이하로 선택해 주세요.')
            image=ImageOps.exif_transpose(image).convert('RGBA')
            image.thumbnail((56,56),Image.Resampling.LANCZOS)
            result=Image.new('RGBA',(64,64),'white')
            result.alpha_composite(image,((64-image.width)//2,(64-image.height)//2))
            return result
    target=row.get('target','').strip().strip('"')
    if target.lower().startswith(('https://','http://')):
        return fallback(True)
    if target and Path(target).exists():
        return shell_icon(target)
    return fallback()
