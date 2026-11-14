"""Render official Galmuri BDF pixels without interpolation or antialiasing."""
from functools import lru_cache
from PIL import Image
from core import APP_ROOT

@lru_cache(maxsize=2)
def glyphs(condensed=False):
    name='Galmuri11-Condensed.bdf' if condensed else 'Galmuri11.bdf'
    lines=(APP_ROOT/'assets/fonts'/name).read_text(encoding='utf-8').splitlines()
    result={};i=0
    while i<len(lines):
        if lines[i].startswith('STARTCHAR '):
            code=None;advance=0;box=(0,0,0,0);bits=[];i+=1
            while lines[i]!='ENDCHAR':
                line=lines[i]
                if line.startswith('ENCODING '):code=int(line.split()[1])
                elif line.startswith('DWIDTH '):advance=int(line.split()[1])
                elif line.startswith('BBX '):box=tuple(map(int,line.split()[1:]))
                elif line=='BITMAP':
                    i+=1
                    while lines[i]!='ENDCHAR':bits.append(lines[i]);i+=1
                    break
                i+=1
            if code is not None:result[code]=(advance,box,bits)
        i+=1
    return result

def raster(text,condensed=False):
    font=glyphs(condensed);items=[font.get(ord(c),font[ord('?')]) for c in text]
    canvas=Image.new('1',(max(1,sum(g[0] for g in items)+8),32));x=0
    for advance,(w,h,dx,dy),rows in items:
        for y,row in enumerate(rows):
            n=int(row,16);width=len(row)*4
            for col in range(w):
                if n & (1<<(width-1-col)):
                    px=x+dx+col;py=20-dy-h+y
                    if 0<=px<canvas.width and 0<=py<canvas.height:canvas.putpixel((px,py),1)
        x+=advance
    bounds=canvas.getbbox()
    return canvas.crop(bounds) if bounds else Image.new('1',(1,1))

def label(image,text,top=53,bottom=69):
    mask=raster(text)
    if mask.width>image.width:mask=raster(text,True)
    if mask.width>image.width:
        while text and raster(text+'…',True).width>image.width:text=text[:-1]
        mask=raster(text+'…',True)
    if mask.height>bottom-top:raise ValueError('표시 영역보다 높은 글자가 포함되어 있습니다.')
    image.paste((255,255,255,255),((image.width-mask.width)//2,top+(bottom-top-mask.height)//2),mask)

