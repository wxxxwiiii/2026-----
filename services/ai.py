"""多服务商 AI 客户端（DeepSeek / 通义千问 / 文心一言 / GPT / 本地模型），OpenAI 兼容接口。"""
from openai import OpenAI

PROVIDERS = {
    'deepseek': {
        'name': 'DeepSeek',
        'base_url': 'https://api.deepseek.com',
        'models': [
            {'id': 'deepseek-chat', 'label': 'DeepSeek 通用', 'pricing': '付费'},
            {'id': 'deepseek-reasoner', 'label': 'DeepSeek 深度思考', 'pricing': '付费'},
        ],
        'key_setting': 'deepseek_api_key',
    },
    'qwen': {
        'name': '通义千问',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'models': [
            {'id': 'qwen-turbo', 'label': '通义千问 Turbo', 'pricing': '免费'},
            {'id': 'qwen-plus', 'label': '通义千问 Plus', 'pricing': '付费'},
        ],
        'key_setting': 'qwen_api_key',
    },
    'ernie': {
        'name': '文心一言',
        'base_url': 'https://qianfan.baidubce.com/v2',
        'models': [
            {'id': 'ernie-speed-128k', 'label': 'ERNIE Speed', 'pricing': '免费'},
            {'id': 'ernie-4.0-8k', 'label': 'ERNIE 4.0', 'pricing': '付费'},
        ],
        'key_setting': 'ernie_api_key',
    },
    'gpt': {
        'name': 'GPT',
        'base_url': 'https://api.openai.com/v1',
        'models': [
            {'id': 'gpt-4o-mini', 'label': 'GPT-4o mini', 'pricing': '付费'},
            {'id': 'gpt-4o', 'label': 'GPT-4o', 'pricing': '付费'},
        ],
        'key_setting': 'gpt_api_key',
    },
    'local': {
        'name': '本地模型',
        'base_url': 'http://localhost:11434/v1',
        'models': [
            {'id': 'qwen2.5:7b', 'label': 'Qwen2.5 7B（本地）', 'pricing': '免费'},
            {'id': 'llama3.1:8b', 'label': 'Llama3.1 8B（本地）', 'pricing': '免费'},
        ],
        'key_setting': None,  # 本地模型无需密钥
    },
}

DEFAULT_PROVIDER = 'deepseek'


def provider_options():
    """返回给前端的选择项（不含密钥等敏感信息）。"""
    return {
        pid: {'name': cfg['name'], 'models': cfg['models']}
        for pid, cfg in PROVIDERS.items()
    }


def find_provider_by_model(model):
    for pid, cfg in PROVIDERS.items():
        for m in cfg['models']:
            if m['id'] == model:
                return pid
    return None


def get_client(provider_id):
    cfg = PROVIDERS.get(provider_id)
    if not cfg:
        raise ValueError('未知模型服务商：%s' % provider_id)
    key_setting = cfg.get('key_setting')
    if key_setting:
        from services.settings import get_setting
        api_key = get_setting(key_setting, '')
        if not api_key:
            raise ValueError('请先在「系统设置」中配置 %s 的 API 密钥' % cfg['name'])
    else:
        api_key = 'local'
    return OpenAI(api_key=api_key, base_url=cfg['base_url'])


def chat(provider_id, model, messages, temperature=0.7):
    """非流式对话，返回完整文本。"""
    client = get_client(provider_id)
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, stream=False,
    )
    return resp.choices[0].message.content


def chat_stream(provider_id, model, messages, temperature=0.7):
    """流式对话，逐段 yield 文本增量。"""
    client = get_client(provider_id)
    stream = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, stream=True,
    )
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta
            content = getattr(delta, 'content', None)
            if content:
                yield content
