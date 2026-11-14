"""ACK/CRC checked private-icon updates for the hardware-tested L99 layout.

No explicit erase command, executable firmware write or automatic retry.
The original-updater initialization and 192-page write were verified on hardware.
"""
import hashlib, json, secrets, struct, time, zlib
from pathlib import Path
from core import APP_ROOT
from icon_transfer import BASE, CAPACITY, make_atlas

LAYOUT_SHA='0c16820f1adbdf35b604c9ac6fdd3b42465443afb0927a080cc0950fa01fe5d0'

def crc(data):return (zlib.crc32(data,0xffffffff)^0xffffffff)&0xffffffff

def layout(root=APP_ROOT):
    import zipfile
    with zipfile.ZipFile(Path(root)/'assets/private-layout.zip') as archive:
        data=archive.read('private-layout.bin')
    if hashlib.sha256(data).hexdigest()!=LAYOUT_SHA:
        raise ValueError('아이콘 전용 기준 파일의 무결성 검사에 실패했습니다.')
    from display_style import patch
    return patch(data)

def prepare(rows,icons,root=APP_ROOT):
    source=layout(root);target=bytearray(source);blob=make_atlas(rows,icons)
    target[BASE:BASE+len(blob)]=blob
    region=bytes(target[BASE:BASE+CAPACITY])
    return target,region,{'full':crc(target),'region':crc(region),'layout_revision':3}

def remember(state,root=APP_ROOT):
    path=Path(root)/'data/icon-baseline.local.json';path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state),encoding='utf-8');tmp.replace(path)

def candidates(source,root=APP_ROOT):
    states=[{'full':crc(source),'region':crc(source[BASE:BASE+CAPACITY]),'layout_revision':3}]
    for rel in ('data/icon-baseline.local.json','generated/icon-baseline-pending.json'):
        path=Path(root)/rel
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            if value.get('layout_revision')!=3:continue
            if not all(type(value.get(k)) is int and 0<=value[k]<=0xffffffff for k in ('full','region')):
                raise ValueError('아이콘 기준 기록이 올바르지 않습니다.')
            states.append(value)
    return states

class Link:
    def __init__(self,transport):self.s=transport
    def send(self,data):
        if self.s.write(data)!=len(data):raise OSError('전송이 불완전해 중단했습니다. 자동 재시도하지 않습니다.')
        self.s.flush()
    def receive(self,prefix,timeout=4):
        data=bytearray();deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            data.extend(self.s.read(63-len(data)))
            if len(data)==63:
                if data[0]!=prefix:raise ValueError('예상하지 못한 장치 응답으로 중단했습니다.')
                return bytes(data)
        raise TimeoutError('장치 응답이 없습니다. USB 모드에서 Fn+스페이스로 화면을 껐는지 확인해 주세요.')
    def initialize(self):
        self.s.reset_input_buffer()
        for sub in (0x30,0x32):
            body=bytes([0x4b,sub])+b'LT'+secrets.token_bytes(4)
            self.send((body+struct.pack('<I',crc(body))+bytes.fromhex('e817000008')).ljust(64,b'\0'))
            r=self.receive(0x4b)
            if struct.unpack_from('<I',r,1)[0]!=crc(body+struct.pack('<I',0x1971168b)+b'POTL'):
                raise ValueError('검증된 L99 화면 컨트롤러와 일치하지 않습니다.')
        self.send(bytes.fromhex('6d0101').ljust(64,b'\0'))
        if struct.unpack_from('<I',self.receive(0x7d),1)[0]!=0xefaa21:
            raise ValueError('검증된 화면 플래시와 일치하지 않습니다.')
        self.send(bytes.fromhex('6f02').ljust(64,b'\0'));self.receive(0x7f)
    def verify(self,start,size,expected,progress):
        body=b'\x6e'+struct.pack('<III',start,size,expected)
        self.send((body+struct.pack('<I',crc(body))).ljust(64,b'\0'))
        deadline=time.monotonic()+110
        while time.monotonic()<deadline:
            r=self.receive(0x7e);status=r[1];value=struct.unpack_from('<I',r,2)[0]
            if status==0x30:progress(min(1,value/size));continue
            if status not in (0x31,0x32):raise ValueError('CRC 검증 응답이 올바르지 않습니다.')
            if (status==0x31)!=(value==expected):raise ValueError('CRC 상태와 값이 일치하지 않습니다.')
            progress(1);return value
        raise TimeoutError('CRC 검사 제한 시간을 초과했습니다.')
    def pages(self,region,progress):
        if len(region)!=CAPACITY:raise ValueError('아이콘 예약 영역 크기가 올바르지 않습니다.')
        for index in range(CAPACITY//2048):
            offset=BASE+index*2048;body=b'\x6c'+struct.pack('<IBH',offset,index%2,2048)+region[index*2048:(index+1)*2048]
            self.send(body+struct.pack('<I',crc(body)))
            if self.receive(0x7c,32)[1] not in (0,1):raise ValueError('기기가 아이콘 기록을 거부했습니다.')
            progress((index+1)/(CAPACITY//2048))

def transfer(link,source,region,state,known,progress=lambda *_:None):
    """Separate protocol workflow allows failure-path tests without hardware."""
    link.initialize()
    actual=link.verify(0,len(source),known[0]['full'],lambda x:progress('기존 화면 검사',x*40))
    matches=[s for s in known if s['full']==actual]
    if not matches:raise ValueError('기존 화면이 확인된 기준과 다릅니다. 기록하지 않았습니다. 펌웨어 적용으로 전용 레이아웃을 먼저 설치해 주세요.')
    before=matches[0]
    if link.verify(BASE,CAPACITY,before['region'],lambda x:progress('아이콘 영역 검사',40+x*5))!=before['region']:
        raise ValueError('아이콘 영역이 기준과 다릅니다. 기록하지 않았습니다.')
    if before==state:
        progress('이미 같은 이름·아이콘입니다',100);return
    link.pages(region,lambda x:progress('아이콘 전송',45+x*10))
    if link.verify(BASE,CAPACITY,state['region'],lambda x:progress('전송 영역 검증',55+x*5))!=state['region']:
        raise ValueError('아이콘 기록 검증 실패. 기본 업데이터로 복구해 주세요.')
    if link.verify(0,len(source),state['full'],lambda x:progress('전체 보존 검증',60+x*40))!=state['full']:
        raise ValueError('전체 화면 검증 실패. 기본 업데이터로 복구해 주세요.')

def upload(rows,icons,progress=lambda *_:None,root=APP_ROOT):
    import serial
    from serial.tools import list_ports
    source=layout(root);target,region,state=prepare(rows,icons,root);known=candidates(source,root)
    ports=[p for p in list_ports.comports() if (p.vid,p.pid)==(0xeeef,0x268a)]
    if len(ports)!=1:raise ValueError('L99 화면 USB 장치 한 개를 연결해 주세요. 화면을 끈 직후라면 잠시 기다렸다 다시 시도해 주세요.')
    started=time.monotonic()
    with serial.Serial(ports[0].device,115200,timeout=.1,write_timeout=3) as s:
        transfer(Link(s),source,region,state,known,progress)
    remember(state,root)
    return {'seconds':round(time.monotonic()-started,1),'full_crc':f'{state["full"]:08X}','reserved_bytes':CAPACITY}
