"""统一 AI 流式接口 /api/ai/chat-stream。"""
import json

from extensions import db
from flask import Blueprint, request, Response, stream_with_context, jsonify

from security import login_required, current_user_id
from services.ai import chat_stream, find_provider_by_model

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/ai/chat-stream', methods=['POST'])
@login_required
def ai_chat_stream():
    data = request.get_json(silent=True) or {}
    model = data.get('model', '')
    messages = data.get('messages', [])
    # 根据 model 自动匹配服务商（进而匹配 API 地址与密钥）
    provider = find_provider_by_model(model) or data.get('provider')

    if not messages or not isinstance(messages, list):
        return jsonify({'error': '缺少 messages 上下文数组'}), 400
    if not provider:
        return jsonify({'error': '未知模型标识：%s' % model}), 400

    def generate():
        try:
            for delta in chat_stream(provider, model, messages):
                yield 'data: ' + json.dumps({'delta': delta}, ensure_ascii=False) + '\n\n'
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield 'data: ' + json.dumps({'error': str(e)}, ensure_ascii=False) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@api_bp.route('/user-info')
@login_required
def user_info():
    """返回当前登录用户信息（含所属院校图书馆官网网址）。"""
    from models import User, School
    school_library_url = ''
    user = db.session.get(User, current_user_id())
    if user and user.school_id:
        school = db.session.get(School, user.school_id)
        if school:
            school_library_url = school.lib_website or ''
    return jsonify({'school_library_url': school_library_url})
