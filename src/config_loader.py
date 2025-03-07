import json

def load_restguardian_config():
    try:
        with open('rest_guardian_config.json', encoding='utf-8') as f:
            config = json.load(f)
        config.setdefault('interval', 28)
        config.setdefault('duration', 1)
        config.setdefault('auto_mode', '自动')
        config.setdefault('countdown_position', '底部')
        return config
    except FileNotFoundError:
        return {'interval': 28, 'duration': 2, 'auto_mode': '自动', 'countdown_position': '底部'}