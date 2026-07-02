import os
import sys
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLATFORM = sys.platform
IS_WINDOWS = PLATFORM == 'win32'
IS_MACOS = PLATFORM == 'darwin'
IS_LINUX = PLATFORM.startswith('linux')


def get_env_or_default(env_name: str, default: str) -> str:
    return os.environ.get(env_name, default)


def get_project_root() -> str:
    return BASE_DIR


def get_report_dir() -> str:
    default = os.path.join(BASE_DIR, '每日报告归档')
    return get_env_or_default('REPORT_OUTPUT_DIR', default)


def get_log_dir() -> str:
    default = os.path.join(BASE_DIR, 'logs')
    return get_env_or_default('LOG_DIR', default)


def get_data_dir() -> str:
    default = os.path.join(BASE_DIR, 'data')
    return get_env_or_default('DATA_DIR', default)


def get_model_dir() -> str:
    if IS_WINDOWS:
        default = r'D:\models\Qwen'
    elif IS_MACOS:
        default = os.path.expanduser('~/models/Qwen')
    else:
        default = os.path.join(BASE_DIR, 'models')
    return get_env_or_default('MODEL_DIR', default)


def get_wind_skill_dir() -> str:
    if IS_WINDOWS:
        default = r'C:\Users\Administrator\.agents\skills\wind-mcp-skill'
    elif IS_MACOS:
        default = os.path.expanduser('~/.agents/skills/wind-mcp-skill')
    else:
        default = os.path.expanduser('~/.agents/skills/wind-mcp-skill')
    return get_env_or_default('WIND_SKILL_DIR', default)


def get_llama_server_exe() -> str:
    if IS_WINDOWS:
        default = r'D:\models\llama_cpp_bin\llama-server.exe'
    elif IS_MACOS:
        default = os.path.expanduser('~/models/llama_cpp_bin/llama-server')
    else:
        default = '/usr/local/bin/llama-server'
    return get_env_or_default('LLAMA_SERVER_EXE', default)


def get_qwen_model_path(model_name: str = 'qwen2.5-1.5b-instruct-q4_k_m.gguf') -> str:
    model_dir = get_model_dir()
    return os.path.join(model_dir, 'Qwen2.5-1.5B-Instruct', model_name)


def get_qwen_7b_model_path(model_name: str = 'qwen2.5-7b-instruct-q4_k_m.gguf') -> str:
    model_dir = get_model_dir()
    return os.path.join(model_dir, 'Qwen2.5-7B-Instruct', model_name)


def get_font_path(font_name: str = 'simhei') -> str:
    font_map = {
        'simhei': {
            'win': r'C:\Windows\Fonts\simhei.ttf',
            'mac': '/Library/Fonts/SimHei.ttf',
            'linux': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        },
        'simsun': {
            'win': r'C:\Windows\Fonts\simsun.ttc',
            'mac': '/Library/Fonts/SimSun.ttc',
            'linux': '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
        },
        'msyh': {
            'win': r'C:\Windows\Fonts\msyh.ttc',
            'mac': '/Library/Fonts/Microsoft YaHei.ttc',
            'linux': '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        }
    }
    
    if font_name not in font_map:
        font_name = 'simhei'
    
    config = font_map[font_name]
    
    if IS_WINDOWS:
        default = config['win']
    elif IS_MACOS:
        default = config['mac']
    else:
        default = config['linux']
    
    env_key = f'FONT_{font_name.upper()}_PATH'
    return get_env_or_default(env_key, default)


def get_windows_font_path(font_name: str) -> str:
    font_paths = {
        'MSYH': r'C:\Windows\Fonts\msyh.ttc',
        'SIMHEI': r'C:\Windows\Fonts\simhei.ttf',
        'SIMSUN': r'C:\Windows\Fonts\simsun.ttc'
    }
    return font_paths.get(font_name.upper(), font_paths.get('SIMHEI'))


def get_yizhao_filtered_dir() -> str:
    if IS_WINDOWS:
        default = os.path.join(BASE_DIR, 'data', 'yizhao_filtered')
    else:
        default = os.path.join(BASE_DIR, 'data', 'yizhao_filtered')
    return get_env_or_default('YIZHAO_FILTERED_DIR', default)


def get_yizhao_root_dir() -> str:
    if IS_WINDOWS:
        default = r'D:\YiZhao-FinDataSet'
    else:
        default = os.path.expanduser('~/YiZhao-FinDataSet')
    return get_env_or_default('YIZHAO_ROOT_DIR', default)


def get_node_exe() -> str:
    if IS_WINDOWS:
        default = r'C:\Program Files\nodejs\node.exe'
    else:
        default = '/usr/local/bin/node'
    return get_env_or_default('NODE_EXE', default)


def get_python_exe() -> str:
    streamlit_python = os.environ.get('STREAMLIT_PYTHON')
    if streamlit_python:
        return streamlit_python
    
    if IS_WINDOWS:
        candidates = [
            r'C:\Users\Administrator\AppData\Roaming\Accio\pre-install\python\python.exe',
            r'C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe',
            r'C:\Program Files\Python38\python.exe',
            sys.executable
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
    
    return sys.executable


def ensure_dir_exists(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def resolve_path(path: str) -> str:
    if path.startswith('~'):
        return os.path.expanduser(path)
    if not os.path.isabs(path):
        return os.path.abspath(os.path.join(BASE_DIR, path))
    return path


def get_cache_dir() -> str:
    default = os.path.join(BASE_DIR, 'data', 'cache')
    return get_env_or_default('CACHE_DIR', default)