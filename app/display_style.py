"""Only entry tile placement/bitmap and the deck's back-button caption."""
import struct
from PIL import Image,ImageDraw
from pixel_font import label

def entry_tile():
    im=Image.new('RGBA',(60,69));d=ImageDraw.Draw(im)
    d.rounded_rectangle((5,0,54,49),radius=10,fill=(16,58,160,255))
    for y in (12,28):
        for x in (14,26,38):d.rectangle((x,y,x+7,y+9),outline='white',width=2)
    label(im,'스트림덱',58,69)
    return im

def patch(source):
    from firmware import encode_icon
    data=bytearray(source);table,count=struct.unpack_from('<II',data,0x30);allowed=[]
    if count!=584:raise ValueError('스트림덱 전용 화면 형식이 아닙니다.')
    def replace(at,blob):data[at:at+len(blob)]=blob;allowed.append((at,at+len(blob)))
    for bank in range(2):
        for index in (569,572):
            at,w,h,kind=struct.unpack_from('<IHHI',data,table+(bank*count+index)*12)
            if (w,h,kind)!=(60,69,8280|(2<<24)):raise ValueError('화면 아이콘 형식 불일치')
            if index==569:im=entry_tile()
            else:
                values=struct.unpack_from('<'+'H'*(w*h),data,at);im=Image.new('RGBA',(w,h))
                im.putdata([(((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17,((v>>12)&15)*17) for v in values])
                # Preserve the arrow/rounded-square pixels, replace caption only.
                im.paste((0,0,0,0),(0,52,60,69));label(im,'뒤로가기')
            replace(at,encode_icon(im))
    # Only the additive home entry widget; all touch events stay byte-identical.
    widget=10751444
    if struct.unpack_from('<H',data,widget+11)[0]!=569:raise ValueError('홈 스트림덱 위치 형식 불일치')
    replace(widget+7,struct.pack('<HH',167,281))
    previous=0
    for lo,hi in sorted(set(allowed)):
        if lo<previous:continue
        assert data[previous:lo]==source[previous:lo];previous=hi
    assert data[previous:]==source[previous:]
    return bytes(data)
