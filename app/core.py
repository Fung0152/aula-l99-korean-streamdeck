"""Local settings and launch targets. No network requests or device writes."""
from pathlib import Path
from urllib.parse import urlsplit
import json, os, sys, tempfile, threading, time, ctypes as C
from ctypes import wintypes as W

KEYS = [str(i) for i in range(10)] + ['/']
VKS = list(range(0x60, 0x6a)) + [0x6f]
VENDOR_SHA = '140efddf2fbb76aa172fdc524630917714efb9249f37edeccc6c07ad58901e41'
APP_ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent


def defaults():
    rows = [{'name': '', 'target': '', 'icon': ''} for _ in KEYS]
    rows[0] = {'name': '챗GPT', 'target': 'shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App', 'icon': ''}
    return rows


def load_settings(root=APP_ROOT):
    path = root / 'data/settings.local.json'
    if not path.exists():
        return defaults()
    value = json.loads(path.read_text(encoding='utf-8'))
    rows = value['buttons']
    if len(rows) != 11 or any(not isinstance(r.get(k), str) for r in rows for k in ('name', 'target', 'icon')):
        raise ValueError('설정 파일의 11개 버튼 형식이 올바르지 않습니다.')
    return [{k: r[k] for k in ('name', 'target', 'icon')} for r in rows]


def save_settings(rows, root=APP_ROOT):
    path = root / 'data/settings.local.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'version': 1, 'buttons': rows}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def resolve_target(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    if not text:
        return None
    u = urlsplit(text)
    if u.scheme.lower() in ('http', 'https'):
        if not u.hostname or any(c in text for c in '\r\n\0'):
            raise ValueError('올바른 웹사이트 주소를 입력해 주세요.')
        return ('url', text)
    if text.startswith('shell:AppsFolder\\') and len(text) > len('shell:AppsFolder\\'):
        return ('app', text)
    path = Path(os.path.expandvars(os.path.expanduser(text)))
    if not path.is_absolute() or not path.exists():
        raise ValueError('실행할 파일 또는 폴더의 전체 경로를 확인해 주세요.')
    return ('file', str(path))


def launch_target(text):
    resolved = resolve_target(text)
    if resolved:
        # Shell association opens http(s) in the user's default browser and
        # documents/shortcuts in their associated program. No shell command text.
        os.startfile(resolved[1])


class HotkeyBridge(threading.Thread):
    def __init__(self, on_event):
        super().__init__(daemon=True)
        self.on_event = on_event
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        u = C.WinDLL('user32', use_last_error=True)
        k = C.WinDLL('kernel32', use_last_error=True)
        k.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]
        k.CreateMutexW.restype = W.HANDLE
        k.CloseHandle.argtypes = [W.HANDLE]
        u.RegisterHotKey.argtypes = [W.HWND, C.c_int, W.UINT, W.UINT]
        u.RegisterHotKey.restype = W.BOOL
        u.UnregisterHotKey.argtypes = [W.HWND, C.c_int]
        u.PeekMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT, W.UINT]
        registered = set()
        active = False
        mutex = k.CreateMutexW(None, False, 'Local\\AULA_L99_Launcher_v1')
        duplicate = C.get_last_error() == 183

        def register(ident, vk):
            if not u.RegisterHotKey(None, ident, 0x4000, vk):
                raise RuntimeError('다른 프로그램이 필요한 숫자 키패드 단축키를 사용 중입니다.')
            registered.add(ident)

        def disable():
            nonlocal active
            for ident in list(registered):
                if ident >= 10:
                    u.UnregisterHotKey(None, ident)
                    registered.discard(ident)
            active = False

        try:
            if not mutex or duplicate:
                raise RuntimeError('다른 L99 연결 프로그램이 실행 중입니다. 먼저 종료해 주세요.')
            register(2, 0x6d)
            register(3, 0x6b)
            self.on_event(('state', 'waiting'))
            msg = W.MSG()
            last = {}
            while not self.stop_event.is_set():
                while u.PeekMessageW(C.byref(msg), None, 0, 0, 1):
                    if msg.message != 0x312:
                        continue
                    ident = msg.wParam
                    if ident == 2:
                        if not active:
                            try:
                                for i, vk in enumerate(VKS):
                                    register(10+i, vk)
                            except Exception:
                                disable()
                                raise
                            active = True
                        self.on_event(('state', 'active'))
                    elif ident == 3:
                        disable()
                        self.on_event(('state', 'waiting'))
                    elif active and 10 <= ident < 21:
                        now = time.monotonic()
                        if now-last.get(ident, -10) >= .6:
                            last[ident] = now
                            self.on_event(('launch', ident-10))
                self.stop_event.wait(.025)
        except Exception as e:
            self.on_event(('error', str(e)))
        finally:
            for ident in registered:
                u.UnregisterHotKey(None, ident)
            if mutex:
                k.CloseHandle(mutex)
            self.on_event(('state', 'stopped'))
