"""Generate icon resources offline, then prepare the ORIGINAL vendor updater."""
from pathlib import Path
import struct, json, hashlib, shutil
from PIL import Image, ImageDraw, ImageFont
from core import APP_ROOT, VENDOR_SHA


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def tile(row,icon):
    im=Image.new('RGBA',(60,69),(0,0,0,255))
    icon=icon.convert('RGBA').resize((48,48),Image.Resampling.LANCZOS)
    im.alpha_composite(icon,(6,1))
    d=ImageDraw.Draw(im)
    label=row['name'].strip() or ('추가' if not row['target'].strip() else '실행')
    from pixel_font import label as draw_label
    draw_label(im,label)
    return im


def encode_icon(im):
    out=bytearray()
    for r,g,b,a in im.getdata():
        out+=struct.pack('<H',((a>>4)<<12)|((r>>4)<<8)|((g>>4)<<4)|(b>>4))
    return out


def build(rows,icons,root=APP_ROOT):
    """Full original-updater package using the hardware-verified private layout."""
    from boot_icons import prepare
    data,region,state=prepare(rows,icons,root)
    out=root/'generated';out.mkdir(exist_ok=True)
    target=out/'UartTFT-II_Flash.bin';tmp=target.with_suffix('.tmp')
    tmp.write_bytes(data);tmp.replace(target)
    (out/'icon-baseline-pending.json').write_text(json.dumps(state),encoding='utf-8')
    report={'sha256':hashlib.sha256(data).hexdigest(),'private_icon_layout_revision':3,
            'device_written':False,'updater':'original vendor 1.31'}
    (out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    package=root/'update-package';package.mkdir(exist_ok=True)
    if list(package.glob('HFD_Code*.bin')):raise ValueError('업데이트 폴더에 실행 펌웨어가 있습니다. 별도의 깨끗한 프로그램 폴더를 사용해 주세요.')
    for f in (root/'vendor').rglob('*'):
        if f.is_file():
            if f.name.startswith('HFD_Code') or 'TIMING' in f.name:raise ValueError('기본 업데이터 패키지가 아닙니다.')
            dest=package/f.relative_to(root/'vendor');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    exe=package/'HFD_ISP_TOOL_V1.31.exe'
    if sha(exe)!=VENDOR_SHA:raise ValueError('기본 업데이터 무결성 검사 실패')
    shutil.copy2(target,package/target.name)
    if sha(package/target.name)!=report['sha256']:raise ValueError('화면 파일 복사 검증 실패')
    return exe,report
