"""AULA L99 Stream Deck editor. Run directly or build the portable Windows EXE."""
import os, sys, queue, threading, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk
from core import APP_ROOT, KEYS, load_settings, save_settings, resolve_target, launch_target, HotkeyBridge
from icons import get_icon
import firmware
import boot_icons
import desktop

BG='#16191f'; PANEL='#20252e'; FG='#edf1f7'; MUTED='#a1abba'; ACCENT='#79b3ff'


class Editor(tk.Tk):
    def __init__(self,instance=None):
        super().__init__()
        self.instance=instance;self.tray=None;self.hidden=False;self.closing=False;self.bridge_generation=0;self.close_dialog=None
        self.title('L99 Stream Deck · 바로가기 편집')
        self.geometry('1020x900');self.minsize(850,620)
        self.configure(bg=BG)
        self.bridge=None;self.events=queue.Queue();self.busy=False;self.photos={};self.pending={};self.dirty=False;self.updater_process=None
        try:self.settings=load_settings()
        except Exception as e:
            messagebox.showerror('설정 읽기 실패',str(e));self.destroy();return
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=PANEL)
        style.configure('TLabel',background=BG,foreground=FG,font=('맑은 고딕',10))
        style.configure('TButton',font=('맑은 고딕',10),padding=(12,7),background='#303846',foreground=FG,borderwidth=0)
        style.map('TButton',background=[('active','#44516a'),('disabled','#252b35')],foreground=[('disabled','#677180')])
        style.configure('Accent.TButton',background='#347dde',foreground='white')
        style.map('Accent.TButton',background=[('active','#4c91ef')])
        style.configure('TEntry',fieldbackground='#11151b',foreground=FG,insertcolor=FG,padding=7,bordercolor='#394354')
        top=ttk.Frame(self,padding=(26,20,26,12));top.pack(fill='x')
        ttk.Label(top,text='L99 STREAM DECK',font=('맑은 고딕',19,'bold')).pack(anchor='w')
        ttk.Label(top,text='11개의 바로가기를 나만의 이름과 아이콘으로 설정하세요.',foreground=MUTED).pack(anchor='w',pady=(5,0))
        ttk.Label(top,text='실행 경로는 저장 즉시 반영 · 이름과 아이콘은 아이콘 적용 후 반영',foreground=MUTED,font=('맑은 고딕',9)).pack(anchor='w',pady=(5,0))
        self.autostart=tk.BooleanVar(value=desktop.startup_enabled())
        ttk.Checkbutton(top,text='Windows 시작 시 자동 실행 · 트레이에서 시작',variable=self.autostart,command=self.change_startup).pack(anchor='w',pady=(8,0))
        footer=ttk.Frame(self,padding=(26,12,26,18));footer.pack(side='bottom',fill='x')
        self.status=tk.StringVar(value='연결 꺼짐 · 편집한 설정을 저장해 주세요.')
        ttk.Label(footer,textvariable=self.status,foreground=ACCENT,wraplength=940).pack(anchor='w',pady=(0,10))
        self.progress=ttk.Progressbar(footer,maximum=100,mode='determinate')
        self.progress.pack(fill='x',pady=(0,10))
        buttons=ttk.Frame(footer);buttons.pack(fill='x')
        self.connect_button=ttk.Button(buttons,text='연결 켜기',command=self.toggle_bridge);self.connect_button.pack(side='left')
        ttk.Label(buttons,text='진입 −  /  종료 +  ·  NumLock 켜짐',foreground=MUTED,font=('맑은 고딕',9)).pack(side='left',padx=14)
        ttk.Button(buttons,text='설정 저장',command=self.save).pack(side='right',padx=(10,0))
        self.apply_button=ttk.Button(buttons,text='펌웨어 적용',style='Accent.TButton',command=self.apply_firmware);self.apply_button.pack(side='right')
        self.icons_button=ttk.Button(buttons,text='아이콘 적용',command=self.apply_icons);self.icons_button.pack(side='right',padx=(0,8))
        area=ttk.Frame(self,padding=(20,0,12,0));area.pack(fill='both',expand=True)
        canvas=tk.Canvas(area,bg=BG,highlightthickness=0)
        scrollbar=ttk.Scrollbar(area,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas);win=canvas.create_window((0,0),window=content,anchor='nw')
        content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        def wheel(e):canvas.yview_scroll(int(-e.delta/120),'units')
        self.bind('<MouseWheel>',wheel)
        self.rows=[]
        for i,row in enumerate(self.settings):self.add_row(content,i,row)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.bind('<Unmap>',self.on_minimize)
        self.tray=desktop.Tray(self.events.put)
        if self.instance:self.instance.watch(self.events.put)
        self.after(60,self.poll)
        self.after(200,self.start_bridge)
        if '--tray' in sys.argv:self.after(300,self.hide_to_tray)

    def add_row(self,parent,i,row):
        card=ttk.Frame(parent,style='Card.TFrame',padding=(12,10));card.pack(fill='x',padx=(4,10),pady=5)
        card.columnconfigure(2,weight=1)
        tk.Label(card,text=f'NUM\n{KEYS[i]}',bg=PANEL,fg=ACCENT,font=('맑은 고딕',11,'bold'),width=5).grid(row=0,column=0,rowspan=2,padx=(0,10))
        image=tk.Label(card,bg='white',width=64,height=64,bd=0)
        image.grid(row=0,column=1,rowspan=2,padx=(0,14))
        name=tk.StringVar(value=row['name']);target=tk.StringVar(value=row['target'])
        # Name occupies the original icon-settings position, per the reference.
        upper=ttk.Frame(card,style='Card.TFrame');upper.grid(row=0,column=2,sticky='ew',pady=(0,5));upper.columnconfigure(1,weight=1)
        tk.Label(upper,text='이름',bg=PANEL,fg=MUTED,font=('맑은 고딕',9)).grid(row=0,column=0,padx=(0,8))
        ttk.Entry(upper,textvariable=name).grid(row=0,column=1,sticky='ew')
        ttk.Button(upper,text='아이콘 설정',command=lambda:self.choose_icon(i)).grid(row=0,column=2,padx=(10,0))
        ttk.Button(upper,text='기본 아이콘',command=lambda:self.reset_icon(i)).grid(row=0,column=3,padx=(6,0))
        lower=ttk.Frame(card,style='Card.TFrame');lower.grid(row=1,column=2,sticky='ew');lower.columnconfigure(0,weight=1)
        entry=ttk.Entry(lower,textvariable=target);entry.grid(row=0,column=0,sticky='ew')
        ttk.Button(lower,text='파일 경로',command=lambda:self.choose_file(i)).grid(row=0,column=1,padx=(10,0))
        self.rows.append({'name':name,'target':target,'icon':row['icon'],'image':image})
        target.trace_add('write',lambda *_:self.changed(i,True))
        name.trace_add('write',lambda *_:self.changed(i,False))
        self.refresh_icon(i)

    def changed(self,i,refresh):
        self.dirty=True
        if refresh:
            if i in self.pending:self.after_cancel(self.pending[i])
            self.pending[i]=self.after(500,lambda:self.refresh_icon(i))

    def snapshot(self):
        return [{'name':r['name'].get().strip(),'target':r['target'].get().strip(),'icon':r['icon']} for r in self.rows]

    def refresh_icon(self,i):
        self.pending.pop(i,None)
        try:
            icon=get_icon(self.snapshot()[i]);photo=ImageTk.PhotoImage(icon)
            self.photos[i]=photo;self.rows[i]['image'].configure(image=photo)
        except Exception as e:self.status.set(f'NUM {KEYS[i]} 아이콘 확인 필요: {e}')

    def choose_file(self,i):
        file=filedialog.askopenfilename(title=f'NUM {KEYS[i]} · 실행할 파일 선택',filetypes=[('프로그램과 바로가기','*.exe *.lnk *.url'),('모든 파일','*.*')])
        if file:
            self.rows[i]['target'].set(file)
            if not self.rows[i]['name'].get().strip():self.rows[i]['name'].set(Path(file).stem)

    def choose_icon(self,i):
        file=filedialog.askopenfilename(title=f'NUM {KEYS[i]} · 아이콘 이미지 선택',filetypes=[('이미지','*.png *.jpg *.jpeg *.ico *.bmp *.webp'),('모든 파일','*.*')])
        if not file:return
        try:
            get_icon({'icon':file})
            dest=APP_ROOT/'data/icons'/f'slot-{i}{Path(file).suffix.lower()}'
            dest.parent.mkdir(parents=True,exist_ok=True)
            if Path(file).resolve()!=dest.resolve():shutil.copy2(file,dest)
            self.rows[i]['icon']=str(dest);self.dirty=True;self.refresh_icon(i)
        except Exception as e:messagebox.showerror('아이콘 설정 실패',str(e))

    def reset_icon(self,i):
        self.rows[i]['icon']='';self.dirty=True;self.refresh_icon(i)

    def save(self):
        rows=self.snapshot()
        try:
            for i,r in enumerate(rows):
                try:resolve_target(r['target'])
                except ValueError as e:raise ValueError(f'NUM {KEYS[i]}: {e}') from e
            save_settings(rows);self.settings=rows;self.dirty=False
            self.status.set('설정 저장 완료 · 실행 경로가 연결 프로그램에 반영됐습니다.')
            return True
        except Exception as e:
            messagebox.showerror('저장 실패',str(e));return False

    def toggle_bridge(self):
        if self.bridge and self.bridge.is_alive():
            self.stop_bridge();return
        if not self.save():return
        self.start_bridge()

    def start_bridge(self):
        if self.closing or self.busy or (self.updater_process and self.updater_process.poll() is None):return
        if self.bridge and self.bridge.is_alive():return
        self.bridge_generation+=1;generation=self.bridge_generation
        self.bridge=HotkeyBridge(lambda event:self.events.put(('bridge',(generation,*event))));self.bridge.start()
        self.connect_button.configure(text='연결 끄기')

    def stop_bridge(self):
        self.bridge_generation+=1
        if self.bridge:self.bridge.stop();self.bridge.join(timeout=2)
        self.connect_button.configure(text='연결 켜기')

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='bridge':
                    generation,kind,value=value
                    if generation!=self.bridge_generation:continue
                if kind=='show':self.show_window();continue
                if kind=='exit':
                    self.quit_app()
                    if self.closing:return
                    continue
                if kind=='tray_error':self.show_window();messagebox.showerror('트레이 오류',value);continue
                if kind=='state':
                    text={'waiting':'연결 켜짐 · 키보드 홈에서 스트림덱으로 진입해 주세요.','active':'스트림덱 모드 활성화 · 뒤로가기를 누르면 숫자 키패드가 해제됩니다.','stopped':'연결 꺼짐 · 숫자 키패드 예약이 해제됐습니다.'}
                    self.status.set(text[value])
                    if value=='stopped':self.connect_button.configure(text='연결 켜기')
                elif kind=='launch':
                    try:
                        row=self.settings[value]
                        if row['target']:launch_target(row['target']);self.status.set(f'실행: {row["name"] or "NUM "+KEYS[value]}')
                        else:self.status.set(f'NUM {KEYS[value]} · 아직 바로가기가 지정되지 않았습니다.')
                    except Exception as e:self.status.set(f'실행 실패: {e}')
                elif kind=='error':messagebox.showerror('연결 오류',value)
                elif kind=='built':
                    self.set_busy(False)
                    exe,report=value
                    messagebox.showinfo('화면 파일 준비 완료','기본 업데이터를 엽니다.\n\nUSB 모드에서 Fn+스페이스를 약 5초 눌러 화면을 끈 뒤, 업데이터의 Start를 눌러 주세요.\n100%·OK가 나올 때까지 USB와 전원을 유지하세요.\n전체 전송은 약 10분 걸립니다.')
                    import subprocess
                    try:
                        # External Qt executable must not inherit the bundle DLL directory.
                        import ctypes
                        if getattr(sys,'frozen',False):ctypes.windll.kernel32.SetDllDirectoryW(None)
                        try:self.updater_process=subprocess.Popen([str(exe)],cwd=str(exe.parent))
                        finally:
                            if getattr(sys,'frozen',False):ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)
                        self.status.set('기본 업데이터 실행 완료 · 완료 후 창을 닫고 키보드를 다시 켜 주세요.')
                    except Exception as e:
                        messagebox.showerror('업데이터 실행 실패',str(e));self.start_bridge()
                elif kind=='build_error':
                    self.set_busy(False);self.start_bridge();messagebox.showerror('화면 파일 생성 실패',value)
                elif kind=='icon_progress':
                    stage,percent=value;self.progress['value']=percent
                    self.status.set(f'{stage} · {percent:.0f}% · USB와 전원을 유지해 주세요.')
                elif kind=='icons_done':
                    self.set_busy(False);self.progress['value']=100
                    self.start_bridge()
                    self.status.set(f'아이콘 적용·전체 검증 완료 · {value["seconds"]:.0f}초 · 키보드를 껐다 켜 주세요.')
                    messagebox.showinfo('아이콘 적용 완료','아이콘 전용 영역과 전체 화면의 CRC 검증을 통과했습니다.\n키보드를 껐다 켜고 스트림덱 화면을 확인해 주세요.')
                elif kind=='icons_error':
                    self.set_busy(False);self.status.set('아이콘 적용 중단 · 오류 내용을 확인해 주세요.')
                    messagebox.showerror('아이콘 적용 중단',value+'\n\n자동 재시도하지 않았습니다. 기록 도중 실패했다면 기본 펌웨어 적용으로 복구해 주세요.')
        except queue.Empty:pass
        if self.updater_process and self.updater_process.poll() is not None:
            self.updater_process=None;self.start_bridge()
            self.status.set('업데이터 창이 닫혀 연결을 다시 켰습니다. 100%·OK 완료 후 키보드를 껐다 켜 주세요.')
        self.after(60,self.poll)

    def apply_firmware(self):
        if self.updater_open():return
        if self.busy or not self.save():return
        if not messagebox.askokcancel('펌웨어 적용','저장한 이름과 아이콘으로 화면 파일을 만들고 기본 업데이터를 실행합니다.\n\n실행 경로만 바꿨다면 펌웨어 적용은 필요 없습니다.\n이번에는 화면 파일을 준비할까요?'):return
        self.stop_bridge()
        rows=self.snapshot()
        self.set_busy(True);self.status.set('화면 아이콘과 이름을 적용하는 중입니다…')
        def work():
            try:self.events.put(('built',firmware.build(rows,[get_icon(r) for r in rows])))
            except Exception as e:self.events.put(('build_error',str(e)))
        threading.Thread(target=work,daemon=True).start()

    def set_busy(self,value):
        self.busy=value
        for button in (self.apply_button,self.icons_button,self.connect_button):button.configure(state='disabled' if value else 'normal')
        if value:self.progress['value']=0

    def apply_icons(self):
        if self.updater_open():return
        if self.busy or not self.save():return
        if not messagebox.askokcancel('아이콘 적용 준비','이름과 아이콘만 전용 영역에 적용합니다.\n\n① 기본 업데이터가 열려 있다면 닫아 주세요.\n② USB 모드에서 Fn+스페이스를 약 5초 눌러 화면을 끄고 잠시 기다려 주세요.\n③ 준비되면 확인을 누르세요.\n\n전송량은 384KB이며, 적용 전후 전체 검증을 포함해 약 2~3분 걸립니다.\n완료 안내까지 USB와 전원을 유지하세요.'):return
        self.stop_bridge()
        rows=self.snapshot();self.set_busy(True);self.status.set('아이콘 생성 및 USB 연결 확인 중…')
        def work():
            try:
                result=boot_icons.upload(rows,[get_icon(r) for r in rows],lambda stage,pct:self.events.put(('icon_progress',(stage,pct))))
                self.events.put(('icons_done',result))
            except Exception as e:self.events.put(('icons_error',str(e)))
        threading.Thread(target=work,daemon=True).start()

    def updater_open(self):
        if self.updater_process and self.updater_process.poll() is None:
            messagebox.showinfo('기본 업데이터 실행 중','기본 업데이터의 작업을 끝내고 창을 닫은 뒤 적용해 주세요.');return True
        return False

    def close(self):
        if self.close_dialog and self.close_dialog.winfo_exists():self.close_dialog.lift();return
        self.show_window()
        dialog=tk.Toplevel(self);self.close_dialog=dialog;dialog.title('프로그램 닫기');dialog.configure(bg=BG);dialog.resizable(False,False)
        dialog.transient(self);dialog.grab_set()
        ttk.Label(dialog,text='창을 닫은 뒤 어떻게 할까요?',font=('맑은 고딕',12,'bold')).pack(padx=24,pady=(22,10))
        ttk.Label(dialog,text='트레이로 이동하면 스트림덱 연결이 계속 유지됩니다.').pack(padx=24,pady=(0,18))
        bar=ttk.Frame(dialog);bar.pack(padx=20,pady=(0,20))
        def choose(action):dialog.destroy();self.close_dialog=None;action()
        ttk.Button(bar,text='트레이로 이동',command=lambda:choose(self.hide_to_tray)).pack(side='left',padx=4)
        ttk.Button(bar,text='완전 종료',command=lambda:choose(self.quit_app)).pack(side='left',padx=4)
        ttk.Button(bar,text='취소',command=lambda:choose(lambda:None)).pack(side='left',padx=4)

    def change_startup(self):
        try:desktop.set_startup(self.autostart.get());self.status.set('Windows 자동 시작 '+('켜짐 · 트레이에서 시작합니다.' if self.autostart.get() else '꺼짐'))
        except Exception as ex:self.autostart.set(desktop.startup_enabled());messagebox.showerror('자동 시작 설정 실패',str(ex))

    def on_minimize(self,event):
        if event.widget is self and self.state()=='iconic':self.after_idle(self.hide_to_tray)

    def hide_to_tray(self):
        if not self.tray or self.tray.error:self.show_window();return
        if not self.tray.ready.is_set():self.after(100,self.hide_to_tray);return
        self.hidden=True;self.withdraw()

    def show_window(self):
        self.hidden=False;self.deiconify();self.state('normal');self.lift();self.focus_force()

    def quit_app(self):
        if self.busy:
            messagebox.showinfo('적용 중','파일 준비 또는 장치 전송·검증이 끝난 뒤 닫아 주세요.');return
        if self.updater_process and self.updater_process.poll() is None:
            self.show_window();messagebox.showinfo('업데이터 실행 중','기본 업데이터의 작업을 마치고 창을 닫은 뒤 종료해 주세요.');return
        if self.dirty:
            choice=messagebox.askyesnocancel('설정 저장','변경한 설정을 저장할까요?')
            if choice is None:return
            if choice and not self.save():return
        self.closing=True;self.stop_bridge()
        if self.tray:self.tray.stop()
        if self.instance:self.instance.close()
        self.destroy()


if __name__=='__main__':
    # Keep Korean UI crisp on Windows display scaling.
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    instance=desktop.Instance()
    if instance.duplicate:instance.close()
    else:Editor(instance).mainloop()
