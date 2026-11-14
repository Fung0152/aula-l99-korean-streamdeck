"""Per-user startup, tray lifecycle and single-instance signalling."""
import ctypes, subprocess, sys, threading, winreg
from ctypes import wintypes as W
from PIL import Image, ImageDraw
from core import APP_ROOT

RUN=r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME='AULA L99 Stream Deck'

def startup_command():
    args=[sys.executable]
    if not getattr(sys,'frozen',False):args.append(str(APP_ROOT/'main.py'))
    return subprocess.list2cmdline(args+['--tray'])

def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN) as key:
            return winreg.QueryValueEx(key,NAME)[0]==startup_command()
    except FileNotFoundError:return False

def set_startup(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,RUN) as key:
        if enabled:winreg.SetValueEx(key,NAME,0,winreg.REG_SZ,startup_command())
        else:
            try:winreg.DeleteValue(key,NAME)
            except FileNotFoundError:pass

class Instance:
    def __init__(self):
        self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        self.k.CreateMutexW.argtypes=[ctypes.c_void_p,W.BOOL,W.LPCWSTR];self.k.CreateMutexW.restype=W.HANDLE
        self.k.CreateEventW.argtypes=[ctypes.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR];self.k.CreateEventW.restype=W.HANDLE
        self.k.SetEvent.argtypes=[W.HANDLE];self.k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];self.k.CloseHandle.argtypes=[W.HANDLE]
        self.mutex=self.k.CreateMutexW(None,False,r'Local\AULA_L99_Editor_Tray_v1')
        error=ctypes.get_last_error()
        if not self.mutex:raise ctypes.WinError(error)
        self.duplicate=error==183
        self.event=self.k.CreateEventW(None,False,False,r'Local\AULA_L99_Editor_Show_v1')
        if not self.event:raise ctypes.WinError(ctypes.get_last_error())
        self.stop=threading.Event()
        if self.duplicate:self.k.SetEvent(self.event)
    def watch(self,post):
        def work():
            while not self.stop.is_set():
                if self.k.WaitForSingleObject(self.event,200)==0:post(('show',None))
        self.thread=threading.Thread(target=work,daemon=True);self.thread.start()
    def close(self):
        self.stop.set()
        if hasattr(self,'thread'):self.thread.join(1)
        self.k.CloseHandle(self.event);self.k.CloseHandle(self.mutex)

class Tray:
    def __init__(self,post):
        import pystray
        image=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(image)
        d.rounded_rectangle((2,2,61,61),radius=13,fill='#123da4')
        for y in (17,35):
            for x in (13,27,41):d.rectangle((x,y,x+9,y+10),outline='white',width=2)
        self.icon=pystray.Icon('AULA L99 Stream Deck',image,'L99 Stream Deck',pystray.Menu(
            pystray.MenuItem('열기',lambda *_:post(('show',None)),default=True),
            pystray.MenuItem('완전 종료',lambda *_:post(('exit',None)))))
        self.ready=threading.Event();self.error=None
        def run():
            try:self.icon.run(setup=lambda icon:(setattr(icon,'visible',True),self.ready.set()))
            except Exception as ex:self.error=ex;self.ready.set();post(('tray_error',str(ex)))
        self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
    def stop(self):self.icon.stop()
