import struct, unittest
from boot_icons import Link, transfer, crc, BASE, CAPACITY

class FakeLink:
    def __init__(self,values):self.values=iter(values);self.writes=0
    def initialize(self):pass
    def verify(self,*args):return next(self.values)
    def pages(self,*args):self.writes+=1

class ProtocolTests(unittest.TestCase):
    def test_unknown_full_image_never_writes(self):
        link=FakeLink([99])
        with self.assertRaises(ValueError):transfer(link,b'old',bytes(CAPACITY),{'full':3,'region':4},[{'full':1,'region':2}])
        self.assertEqual(link.writes,0)
    def test_wrong_region_never_writes(self):
        link=FakeLink([1,99])
        with self.assertRaises(ValueError):transfer(link,b'old',bytes(CAPACITY),{'full':3,'region':4},[{'full':1,'region':2}])
        self.assertEqual(link.writes,0)
    def test_remembered_baseline_and_both_post_checks(self):
        link=FakeLink([7,8,4,3])
        transfer(link,b'old',bytes(CAPACITY),{'full':3,'region':4},[{'full':1,'region':2},{'full':7,'region':8}])
        self.assertEqual(link.writes,1)
    def test_same_icons_skip_writes(self):
        link=FakeLink([3,4]);state={'full':3,'region':4}
        transfer(link,b'old',bytes(CAPACITY),state,[state]);self.assertEqual(link.writes,0)
    def test_failed_full_postcheck_is_not_success(self):
        link=FakeLink([1,2,4,99])
        with self.assertRaises(ValueError):transfer(link,b'old',bytes(CAPACITY),{'full':3,'region':4},[{'full':1,'region':2}])
        self.assertEqual(link.writes,1)
    def test_wire_packets_stay_in_reservation_and_match_payload(self):
        class Serial:
            def __init__(self):self.packets=[]
            def write(self,b):self.packets.append(b);return len(b)
            def flush(self):pass
            def read(self,n):return b'\x7c\x00'+bytes(61)
        s=Serial();data=bytes((i%251 for i in range(CAPACITY)));Link(s).pages(data,lambda *_:None)
        self.assertEqual(len(s.packets),192)
        for i,b in enumerate(s.packets):
            offset,phase,size=struct.unpack_from('<IBH',b,1)
            self.assertEqual((b[0],offset,phase,size),(0x6c,BASE+i*2048,i%2,2048))
            self.assertLessEqual(offset+size,BASE+CAPACITY)
            self.assertEqual(b[8:-4],data[i*2048:(i+1)*2048])
            self.assertEqual(struct.unpack_from('<I',b,len(b)-4)[0],crc(b[:-4]))

if __name__=='__main__':unittest.main()
