# -*- coding: utf-8 -*-
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.env_loader import load_dotenv

load_dotenv()
if not os.environ.get('ZHIPUAI_API_KEY'):
    print('未检测到 ZHIPUAI_API_KEY，请在 .env 中配置后重试。')
    sys.exit(1)

print('Loading GLM-5 client...')
from utils.glm5_client import GLM5Client

print('Initializing...')
client = GLM5Client(mode='api', api_model='glm-4-plus')

print('Health check:', client.health_check())

result = client.chat('你好', max_tokens=50)
print('Response:', result['content'][:100])
print('SUCCESS!')
