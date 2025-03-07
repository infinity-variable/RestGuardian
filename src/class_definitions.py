import tkinter as tk
import winreg
from tkinter import ttk, messagebox, filedialog
import json
import threading
import time
import pystray
from PIL import Image, ImageTk
import os
import sys


from config_loader import load_restguardian_config
from utils import get_resource_path

class TimerManager:
    def __init__(self, master):
        self.master = master
        self.root = master  # 初始化root属性
        self.work_timer = None
        self.rest_timer = None
        self.control_panel = None
        self.work_start = time.time()
        self.rest_start = time.time() 
        self.is_screensaver_active = False
        self.load_config()

    def force_close_screensaver(self):
        self.stop_timer('all')
        self.load_config()
        if hasattr(self, 'screensaver') and self.screensaver.window.winfo_exists():
            self.screensaver.window.destroy()
        self.is_screensaver_active = False
        self.work_start = time.time()
        self.master.event_generate('<<UpdateDisplay>>')
        self.start_work_timer()

    def load_config(self):
        try:
            with open('rest_guardian_config.json', encoding='utf-8') as f:
                self.config = json.load(f)
            # 确保配置项存在
            self.config.setdefault('interval', 1)
            self.config.setdefault('duration', 1)
            self.config.setdefault('auto_mode', '自动')
        except FileNotFoundError:
            self.config = {'interval': 28, 'duration': 2, 'auto_mode': '自动'}

    def reset_timer(self, is_manual=False):
        if self.is_screensaver_active:
            self.force_close_screensaver()
        self.stop_timer()
        self.start_work_timer()


    def start_work_timer(self):
        self.stop_timer('rest')
        interval_sec = self.config['interval'] * 60
        self.work_start = time.time()
        self.master.bind('<<TriggerScreenSaver>>', lambda e: self.trigger_screensaver())
        self.work_timer = threading.Timer(interval_sec, self.trigger_screensaver)
        self.work_timer.start()
        self.master.event_generate('<<UpdateDisplay>>')
        self.master.after(100, lambda: self.master.event_generate('<<UpdateDisplay>>'))

    def start_rest_timer(self):
        self.stop_timer('work')
        duration_sec = self.config['duration'] * 60
        self.rest_start = time.time() - 1  # 统一时间源，减少1秒以同步倒计时
        
        # 根据配置决定回调函数
        print(f'当前模式: {self.config.get("auto_mode")}')
        if self.config.get('auto_mode', '自动') == '自动':
            print(f'[线程{threading.get_ident()}] 自动模式回调创建')
            callback = lambda: self.master.after(0, lambda: [
                print(f'[主线程回调] 即将执行_auto_restart_work'),
                self._auto_restart_work()
            ])
        else:
            print('手动模式回调触发')
            callback = lambda: self.master.after(0, self._manual_update)

        # 创建并启动计时器
        self.rest_timer = threading.Timer(duration_sec, callback)
        self.rest_timer.start()
        self.master.event_generate('<<UpdateDisplay>>')
        if self.control_panel:
            self.master.after(100, self.control_panel.update_display)

    def _auto_restart_work(self):
        print(f'[DEBUG] 进入_auto_restart_work方法 线程ID:{threading.get_ident()} 时间:{time.time()}')
        print("自动模式重启工作计时器，触发时间:", time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 确保在主线程执行
        if self.master:
            self.master.after(0, lambda: [
                self.start_work_timer(),
                self.master.event_generate('<<UpdateDisplay>>'),
                print(f'[主线程回调] 工作计时器状态:', 
                      self.work_timer.is_alive() if self.work_timer else '未启动')
            ])
        else:
            print('[ERROR] master引用丢失!')
        print(f'[DEBUG] 退出_auto_restart_work方法 时间:{time.time()}')

   # def _manual_update(self):
      # self.master.event_generate('<<UpdateDisplay>>')
     #   if self.control_panel:
       #     self.control_panel.work_remaining.set('等待开始')
     #   self.master.event_generate('<<UpdateDisplay>>')
      #  if self.control_panel:
      #      self.master.after(100, self.control_panel.update_display)


    def _manual_update(self):
        print(f'[DEBUG] 进入_manual_update方法 线程ID:{threading.get_ident()} 时间:{time.time()}')
        print(f'当前模式: {self.config.get("auto_mode", "手动")}')
        
        self.master.event_generate('<<UpdateDisplay>>')
        print('[EVENT] 主界面显示更新事件已触发')
        
        if self.control_panel:
            print('[CONTROL_PANEL] 控制面板存在，更新工作状态显示')
            self.control_panel.work_remaining.set('等待开始')
        else:
            print('[WARNING] 控制面板引用丢失!')
        
        print(f'即将触发3次更新事件，当前时间: {time.strftime("%H:%M:%S")}')
        for i in range(3):
            self.master.event_generate('<<UpdateDisplay>>')
            print(f'[EVENT #{i+1}] 更新事件已触发')
            self.master.after(50, lambda: self.master.event_generate('<<UpdateDisplay>>'))
        
        if self.control_panel:
            print('[CONTROL_PANEL] 调度控制面板更新显示')
            self.control_panel.work_remaining.set('等待开始')
       #     self.master.after(0, self.control_panel.update_display)
        
        print(f'[DEBUG] 退出_manual_update方法 时间:{time.time()}')

    def sync_config(self):
        """同步配置到timer_manager"""
        self.load_config()  # 重新加载最新配置
        self.start_rest_timer()
        self.start_rest_timer()

    def _notify_control_panel(self):
        self.master.event_generate('<<TriggerScreenSaver>>')
        if self.control_panel and self.control_panel.winfo_exists():
            self.control_panel.update_display()

    def stop_timer(self, timer_type='all'):
        if timer_type in ('all', 'work') and self.work_timer and self.work_timer.is_alive():
            self.work_timer.cancel()
        if timer_type in ('all', 'rest') and self.rest_timer and self.rest_timer.is_alive():
            self.rest_timer.cancel()

    def trigger_screensaver(self):
        self.load_config()
        self.is_screensaver_active = True
        self.start_rest_timer()  # 这里已经包含模式判断
        self.root.after(0, self._create_screensaver)

    def on_screensaver_close(self):
        self.is_screensaver_active = False
        self.screensaver.window.destroy()
        self.start_work_timer()

    def _create_screensaver(self):
        self.screensaver = ScreenSaver(self.root, self)
        self.screensaver.window.protocol('WM_DELETE_WINDOW', self.on_screensaver_close)
        self.screensaver.window.mainloop()

  
class ScreenSaver:
    def __init__(self, master, timer_manager):
        self.window = tk.Toplevel(master)
        self.master = master
        self.timer_manager = timer_manager  # 添加属性赋值
        self.window.attributes('-fullscreen', True)
        
        self.start_time = self.timer_manager.rest_start  # 使用统一时间源
        
        # 创建全屏画布
        self.canvas = tk.Canvas(self.window, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
            
        # 初始化默认位置值
        y_position = screen_height // 2  # 默认居中位置
            
        # 加载适配屏幕的背景图片
        try:
            bg_image_path = get_resource_path(self.timer_manager.config.get('bg_image', 'resources/default_wallpaper/chris-tabone-jtVL1btP-oc-unsplash.jpg'))
           
            # 获取配置并严格验证
            position = str(self.timer_manager.config.get('countdown_position', '底部')).strip()
            valid_positions = {'顶部', '居中', '底部'}
            
            # 使用字典get方法带默认值
            y_position = {
                '顶部': screen_height * 0.1,
                '居中': screen_height // 2,
                '底部': screen_height * 0.9
            }.get(position, screen_height // 2)  # 无效值自动回退默认
            
            self.bg_image = Image.open(bg_image_path)
            # 保持比例缩放填充屏幕
            resized_image = self.bg_image.resize(
                (screen_width, screen_height),
                Image.Resampling.LANCZOS
            )
            self.bg_photo = ImageTk.PhotoImage(resized_image)
            self.canvas.create_image(screen_width//2, screen_height//2, 
                                   image=self.bg_photo, anchor='center')
        except Exception as e:
            self.canvas.configure(bg='black')
            bg_image_path = get_resource_path(self.timer_manager.config.get('bg_image', 'resources/default_wallpaper/chris-tabone-jtVL1btP-oc-unsplash.jpg'))
            messagebox.showerror('图片加载失败', f'无法加载背景图片:\n{bg_image_path}\n错误: {e}')

        # 倒计时标签
        self.countdown_text = self.canvas.create_text(
            self.window.winfo_screenwidth()//2,
            y_position,
            text="00:00",
            fill='white',
            font=('Segoe UI', 90, 'bold'),
            anchor='center'
        )
        self.update_countdown()
        
        # 立即启动倒计时
        self.timer_manager = timer_manager
        
        # 退出按钮
        try:
            close_img = Image.open(get_resource_path('resources/icons/close.png')).resize((30, 30), Image.Resampling.LANCZOS)
            self.close_photo = ImageTk.PhotoImage(close_img)
            exit_btn = ttk.Button(self.canvas, image=self.close_photo, command=self.window.destroy, style='Round.TButton')
        except Exception:
            # ttk.Button 没有 font 参数，使用 tk.Button 替代
            exit_btn = tk.Button(self.canvas, text='退出', command=self.window.destroy, font=('Microsoft YaHei', 12))
        exit_btn.place(relx=0.98, rely=0.02, anchor='ne')
        
        # 绑定ESC按键事件
        self.window.bind('<Escape>', lambda e: self.window.destroy())

        self.update_countdown()
        self.start_time = self.timer_manager.rest_start  # 将start_time初始化移至此
        self.window.after(1000, self.update_countdown)


 # 倒计时
    def update_countdown(self):
        # 添加时间补偿逻辑
        total_duration = self.timer_manager.config['duration'] * 60
        elapsed_since_rest_start = time.time() - self.timer_manager.rest_start
        self.remaining = max(0, total_duration - int(elapsed_since_rest_start) - 1)  # 减去1秒补偿
        
        if self.remaining > 0:
            self.canvas.itemconfig(self.countdown_text, 
                text=f'{self.remaining//60:02d}:{self.remaining%60:02d}')
            self.window.after(1000, self.update_countdown)
        else:
            self.window.destroy()

 

class Settings(tk.Toplevel):
    DEFAULT_BG_IMAGE = get_resource_path('resources/default_wallpaper/chris-tabone-jtVL1btP-oc-unsplash.jpg')
    def __init__(self, master, timer_manager):
        super().__init__(master)
        self.iconbitmap(get_resource_path('resources/icons/y_alarm.ico'))
        self.timer_manager = timer_manager  # 显式声明实例属性
        self.timer_manager: 'TimerManager' = timer_manager  # 添加类型提示
        self.title('Rest Guardian')
        
        # 设置Win10风格
        self.style = ttk.Style()
        self.style.theme_use('vista')
        
        # 统一样式配置
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white', foreground='black')
        self.style.configure('TSeparator', background='#F8F8F8')
        self.style.configure('TCheckbutton', background='white', foreground='black', font=('Microsoft YaHei', 11), padding=(20, 5), indicatorwidth=20, indicatormargin=5, indicatorrelief='flat', indicatormarginleft=5, indicatorbackground='white', indicatorforeground='#0078D4')
        self.style.configure('TRadiobutton', background='white', foreground='black', font=('Microsoft YaHei', 11))  # 新增单选按钮样式
        
        # 主容器
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # 表单容器
        form_frame = ttk.Frame(main_frame)
        form_frame.grid(row=0, column=0, pady=10)
        
        ttk.Label(form_frame, text='工作时长:', font=('Microsoft YaHei', 11)).grid(row=0, column=0, padx=15, pady=5, sticky='w')
        self.interval_entry = ttk.Entry(form_frame, font=('Segoe UI', 11), width=12)
        self.interval_entry.grid(row=0, column=1, padx=10, pady=2)
        ttk.Label(form_frame, text='分钟', font=('Microsoft YaHei', 11)).grid(row=0, column=2, padx=0, pady=5, sticky='w')
        
        ttk.Label(form_frame, text='休息时长:', font=('Microsoft YaHei', 11)).grid(row=1, column=0, padx=15, pady=5, sticky='w')
        self.duration_entry = ttk.Entry(form_frame, font=('Segoe UI', 11), width=12 )
        self.duration_entry.grid(row=1, column=1, padx=10, pady=2)
        ttk.Label(form_frame, text='分钟', font=('Microsoft YaHei', 11)).grid(row=1, column=2, padx=0, pady=5, sticky='w')
        # 图片上传功能
        ttk.Label(form_frame, text='背景图片:', font=('Microsoft YaHei', 11)).grid(row=2, column=0, padx=15, pady=5, sticky='w')
        self.bg_image_entry = ttk.Entry(form_frame, width=12, font=('Segoe UI', 11))
        self.bg_image_entry.grid(row=2, column=1, padx=10, pady=2)
        ttk.Button(form_frame, text='本地图片', command=self.select_image, style='Round.TButton', width=10).grid(row=2, column=2, padx=15, sticky='e')
                 
        # 倒计时位置设置
        position_frame = ttk.Frame(main_frame)
        position_frame.grid(row=3, column=0, pady=10, sticky='w')
        ttk.Label(position_frame, text='倒计时位置:', font=('Microsoft YaHei', 11)).pack(side='left', padx=15)
        self.countdown_position_var = tk.StringVar(value=self.timer_manager.config.get('countdown_position', '顶部'))
        for position in ['顶部', '居中', '底部']:
            rb = ttk.Radiobutton(position_frame, text=position, variable=self.countdown_position_var, 
                               value=position)
            rb.pack(side='left', padx=5)

        # 模式选择容器
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=4, column=0, pady=10, sticky='w')
        ttk.Label(mode_frame, text='模式:', font=('Microsoft YaHei', 11)).pack(side='left', padx=15)
        self.mode_var = tk.StringVar(value=self.timer_manager.config.get('auto_mode', '自动'))
        for mode in ['自动', '手动']:
            rb = ttk.Radiobutton(mode_frame, text=mode, variable=self.mode_var, 
                               value=mode)
            rb.pack(side='left', padx=5)

        # 开机自启动选项
        self.auto_start_var = tk.BooleanVar()
        main_frame.grid_columnconfigure(0, weight=1)
        ttk.Checkbutton(main_frame, text=' 开机自动启动', variable=self.auto_start_var).grid(row=5, column=0, pady=10, sticky='w', padx=1)
        
        # 保存按钮
        save_btn = ttk.Button(main_frame, text='保存', command=self.save_settings, style='Accent.TButton', width=8)
        save_btn.grid(row=5, column=0, pady=15, sticky='e', padx=15)
        

        
        self.load_settings()

    def load_settings(self):
        try:
            with open('rest_guardian_config.json', encoding='utf-8') as f:
                config = json.load(f)
                self.interval_entry.insert(0, config.get('interval', 60))
                self.duration_entry.insert(0, config.get('duration', 1))
                # 默认不勾选自启动
                self.auto_start_var.set(config.get('auto_start', False))
        except FileNotFoundError:
            self.interval_entry.insert(0, '28')
            self.duration_entry.insert(0, '2')
            self.auto_start_var.set(False)

    def get_duration(self):
        try:
            with open('rest_guardian_config.json', encoding='utf-8') as f:
                return json.load(f).get('duration', 1) * 60
        except FileNotFoundError:
            return 60

    def select_image(self):
        filepath = filedialog.askopenfilename(filetypes=[('图片文件', '*.jpg *.jpeg *.png')])
        if filepath:
            self.bg_image_entry.delete(0, tk.END)
            self.bg_image_entry.insert(0, filepath)

    def save_settings(self):
        try:
            config = {
                'interval': int(self.interval_entry.get()),
                'duration': int(self.duration_entry.get()),
                'bg_image': self.bg_image_entry.get() or self.DEFAULT_BG_IMAGE,
                'auto_start': self.auto_start_var.get(),
                'auto_mode': self.mode_var.get(),
                'countdown_position': self.countdown_position_var.get(),
            }
            with open('rest_guardian_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False)
            
            # 同步配置到timer_manager
            if hasattr(self, 'timer_manager'):
                self.timer_manager.config = config
                self.timer_manager.stop_timer('all')
                self.timer_manager.start_work_timer()
            
            # 注册表操作
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Run',
                    0, winreg.KEY_SET_VALUE)
                
                app_path = sys.executable
                
                if config['auto_start']:
                    winreg.SetValueEx(key, 'RestGuardian', 0, winreg.REG_SZ, f'"{app_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, 'RestGuardian')
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)
            except Exception as e:
                messagebox.showerror('注册表错误', f'无法修改开机启动设置: {e}')
                
            messagebox.showinfo('成功', '设置已保存')
        except ValueError:
            messagebox.showerror('错误', '请输入有效的数字')

class ControlPanel(tk.Toplevel):
    def __init__(self, master, timer_manager):
        super().__init__(master)
        self.iconbitmap(get_resource_path('resources/icons/y_alarm.ico'))
        self.timer_manager = timer_manager  # 显式声明实例属性
        self.timer_manager: 'TimerManager' = timer_manager  # 添加类型提示
        
        self.work_remaining = tk.StringVar()
        self.rest_remaining = tk.StringVar()
        self.timer_manager = timer_manager
        self.timer_manager.control_panel = self
        
        # 设置Win10风格
        self.style = ttk.Style()
        self.style.theme_use('vista')
        
        # 统一样式配置
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white', foreground='black')
        self.style.configure('TSeparator', background='#F8F8F8')
        
        # 主容器
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # 倒计时显示框架
        self.timer_frame = ttk.Frame(main_frame)
        self.timer_frame.grid(row=0, column=0, pady=10, sticky='nsew')

        # 工作倒计时容器
        work_frame = ttk.Frame(self.timer_frame)
        work_frame.grid(row=0, column=0, padx=20, sticky='ns')
        ttk.Label(work_frame, text='工作时间', style='TLabel', font=('Microsoft YaHei', 12)).pack(pady=5)
        ttk.Label(work_frame, textvariable=self.work_remaining, font=('Segoe UI', 24, 'bold'), foreground='#0078D4').pack(pady=5)
        ttk.Button(work_frame, text='工作', command=self.start_work_timer, style='Round.TButton').pack(pady=5)

        # 分隔线
        ttk.Separator(self.timer_frame, orient='vertical', style='TSeparator').grid(row=0, column=1, sticky='ns', padx=20)

        # 休息倒计时容器
        rest_frame = ttk.Frame(self.timer_frame)
        rest_frame.grid(row=0, column=2, padx=20, sticky='ns')
        ttk.Label(rest_frame, text='休息时间', style='TLabel', font=('Microsoft YaHei', 12)).pack(pady=5)
        ttk.Label(rest_frame, textvariable=self.rest_remaining, font=('Segoe UI', 24, 'bold'), foreground='#00B294').pack(pady=5)
        ttk.Button(rest_frame, text='休息', command=self.on_rest_button_click, style='Round.TButton').pack(pady=5)
        
        # 控制按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, pady=15)
        
        # 初始化后立即启动显示更新
        self.update_display()
        self.after(100, self.update_display)

    def start_work_timer(self):
        self.timer_manager.force_close_screensaver()
        self.timer_manager.stop_timer('all')
        self.timer_manager.work_start = time.time()
        self.timer_manager.start_work_timer()
        self.rest_remaining.set('--:--')
        self.timer_manager.master.event_generate('<<UpdateDisplay>>')
        self.update_display()
        self.rest_remaining.set('--:--')

    def update_display(self):
        if self.timer_manager.work_timer and self.timer_manager.work_timer.is_alive():
            work_elapsed = time.time() - self.timer_manager.work_start
            work_remaining = max(0, self.timer_manager.config['interval']*60 - work_elapsed)
            self.work_remaining.set(f'{int(work_remaining//60):02d}:{int(work_remaining%60):02d}')
            self.rest_remaining.set('--:--')
        elif self.timer_manager.is_screensaver_active:
            rest_elapsed = time.time() - self.timer_manager.rest_start
            rest_remaining = max(0, self.timer_manager.config.get('duration', 1)*60 - rest_elapsed)
            self.rest_remaining.set(f'{int(rest_remaining//60):02d}:{int(rest_remaining%60):02d}')
            # 仅自动模式显示--:--
            if self.timer_manager.config.get('auto_mode', '自动') == '自动':
                self.work_remaining.set('--:--')
        else:
            if self.timer_manager.config.get('auto_mode', '自动') == '手动':
                self.work_remaining.set('等待开始')
            else:
                self.work_remaining.set('--:--')
            self.rest_remaining.set('--:--')
        
        self.after(100, self.update_display)

    def on_rest_button_click(self):
        self.timer_manager.stop_timer('all')
        self.timer_manager.trigger_screensaver()
        self.update_display()
        self.work_remaining.set('--:--')
