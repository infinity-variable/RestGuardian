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

from class_definitions import TimerManager
from class_definitions import ScreenSaver
from class_definitions import ControlPanel
from class_definitions import Settings

from config_loader import load_restguardian_config
from utils import get_resource_path




def create_tray_icon(timer, root):
    try:
        image = Image.open(get_resource_path('resources/icons/logo_alarm.ico'))
    except FileNotFoundError as e:
        print(f"资源加载失败: {str(e)}")
        image = Image.new('RGB', (64, 64), color='red')  # 创建备用图标
    menu = (
        pystray.MenuItem('设置', lambda: Settings(root, timer)),
        pystray.MenuItem('控制', lambda: ControlPanel(root, timer)),
        pystray.MenuItem('退出', lambda: [timer.stop_timer(), os._exit(0)])
    )
    icon = pystray.Icon("rest_guardian", image, "Rest Guardian", menu)
    return icon

def main():
    root = tk.Tk()
    root.withdraw()
    root.title('Rest Guardian')
    # 会误弹出一个多余弹窗并且没有修改任务栏图标成功
    root.iconbitmap(get_resource_path('resources/icons/y_alarm.ico'))
    
    config = load_restguardian_config()
    try:
        timer = TimerManager(root)
        # settings = Settings(root, timer)
        tray_icon = create_tray_icon(timer, root)
        tray_icon.run_detached()
        
        root.withdraw()
        root.protocol('WM_DELETE_WINDOW', lambda: [root.withdraw()])
        timer.start_work_timer()
        root.mainloop()
    
    except Exception as e:
        print(f'程序初始化失败: {e}')
        import traceback
        traceback.print_exc()
        messagebox.showerror('致命错误', f'程序无法启动: {str(e)}')

#if __name__ == '__main__':
#    main()
# 主程序入口
if __name__ == '__main__':
    main()

try:
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
        r'Software\Microsoft\Windows\CurrentVersion\Run',
        0, winreg.KEY_ALL_ACCESS)
        
    app_path = sys.executable
    
    with open('rest_guardian_config.json', encoding='utf-8') as f:
        config = json.load(f)
    
    if config.get('auto_start', False):
        winreg.SetValueEx(key, 'RestGuardian', 0, winreg.REG_SZ, f'"{app_path}"')
    else:
        try:
            winreg.DeleteValue(key, 'RestGuardian')
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)
except Exception as e:
    messagebox.showerror('注册表错误', f'无法修改开机启动设置: {e}')

# 获取打包后的资源路径
# 检查是否是打包后的可执行文件
if getattr(sys, 'frozen', False):
    # 使用getattr来避免属性不存在的错误
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
else:
    base_path = os.path.abspath('.')

# 修改所有资源路径获取方式
icon_path = os.path.join(base_path, 'resources/icons/logo_alarm.ico')
wallpaper_dir = os.path.join(base_path, 'resources/wallpaper')
default_wallpaper_dir = os.path.join(base_path, 'resources/default_wallpaper')