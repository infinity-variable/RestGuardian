
from config_loader import load_restguardian_config
import os
import sys

def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    resolved_path = os.path.normpath(os.path.join(base_path, relative_path))
    
    if not os.path.exists(resolved_path):
        error_msg = f"资源路径不存在: {resolved_path}\n当前工作目录: {os.getcwd()}\n系统路径: {sys.path}"
        raise FileNotFoundError(error_msg)
    return resolved_path
