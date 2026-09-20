"""系统设置：以 key-value 形式存进数据库，例如 DeepSeek API 密钥。"""
from extensions import db
from models import Setting


def get_setting(key, default=None):
    row = Setting.query.filter_by(key=key).first()
    return row.value if row else default


def set_setting(key, value):
    row = Setting.query.filter_by(key=key).first()
    if row is None:
        row = Setting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    db.session.commit()
    return row


PUBLIC_API_KEYS = ['nssd', 'ucdrs', 'curriculum', 'cnki']


def get_public_config():
    """读取公共文献 API 全局配置（JSON）。"""
    import json
    raw = get_setting('public_api_config', '')
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {k: {'enabled': False, 'api_key': '', 'rate': 10} for k in PUBLIC_API_KEYS}
