"""统一知识库检索 + 文献引用 + RAG 教案生成（三层数据源，公共/图书馆先用模拟数据）。"""
import json
import uuid

from flask import Blueprint, request, jsonify, Response, stream_with_context

from extensions import db
from models import School, User, KbDoc, KbChunk, LessonCite, LessonPlan, Reflection, ApiLog, LearningSheet
from security import login_required, current_user_id
from services.ai import chat_stream, find_provider_by_model

rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')

PUBLIC_SOURCES = [
    {'key': 'nssd', 'label': '国家哲学社会科学文献中心'},
    {'key': 'ucdrs', 'label': '全国图书馆参考咨询联盟'},
    {'key': 'curriculum', 'label': '高等教育课标公开库'},
    {'key': 'cnki', 'label': '知网研学'},
]

SPORT_LESSON_SKILL = """你是一位资深的高校体育教师与备课专家。请严格依据高校体育课程标准，结合提供的知识库文献片段与教师历史教学反思，生成专业、结构清晰、可落地的体育教案。

教案需包含以下结构：
1. 教学目标（知识、技能、情感态度）
2. 教学重点与难点
3. 教学准备（场地、器材）
4. 教学过程（准备部分、基本部分、结束部分，含时间分配与组织教法）
5. 教学评价与安全注意事项

请用规范中文撰写，语言专业、简洁。"""


def _search_local(user_id, keyword, top_k):
    results = []
    docs = KbDoc.query.filter_by(owner_id=user_id).all()
    for doc in docs:
        for c in KbChunk.query.filter_by(doc_id=doc.id).all():
            if keyword.lower() in c.text.lower():
                results.append({
                    'source': 'local', 'source_label': '本地上传',
                    'title': doc.title, 'snippet': c.text[:200],
                    'url': doc.url or '', 'doc_id': doc.id,
                })
                if len(results) >= top_k:
                    return results
    return results


def _search_library_mock(school, keyword, top_k):
    if not school or not school.lib_enabled:
        return []
    label = (school.name or '本校') + '图书馆'
    return [{
        'source': 'library', 'source_label': label,
        'title': '《%s》馆藏图书' % keyword,
        'snippet': '模拟馆藏摘要：关于「%s」的馆藏文献（框架演示数据，接入真实图书馆接口后替换）。' % keyword,
        'url': 'https://example.com/library', 'doc_id': 0,
    }][:top_k]


def _search_public_mock(keyword, top_k):
    from services.settings import get_public_config
    config = get_public_config()
    results = []
    for i, src in enumerate(PUBLIC_SOURCES):
        if not config.get(src['key'], {}).get('enabled'):
            continue
        db.session.add(ApiLog(source=src['label'], keyword=keyword))
        results.append({
            'source': 'public', 'source_label': src['label'],
            'title': '《%s》相关文献（%s）' % (keyword, src['label']),
            'snippet': '模拟文献摘要：关于「%s」的公开文献片段（框架演示数据，接入真实 API 后替换）。' % keyword,
            'url': 'https://example.com/public/%d' % i, 'doc_id': 0,
        })
    if results:
        db.session.commit()
    return results[:top_k]


def _format_snippets(snippets):
    if not snippets:
        return ''
    lines = ['【知识库文献片段】']
    for i, s in enumerate(snippets, 1):
        lines.append('%d. [%s] %s：%s' % (i, s.get('source_label', ''), s.get('title', ''), s.get('snippet', '')))
    return '\n'.join(lines)


def _get_reflections_text():
    items = Reflection.query.order_by(Reflection.id.desc()).limit(5).all()
    if not items:
        return ''
    lines = ['【教师历史教学反思与听课记录】']
    for r in items:
        lines.append('- %s（%s）：%s' % (r.title, r.kind, (r.content or '')[:300]))
    return '\n'.join(lines)


def _build_prompt(mode, course_info, user_input, kb_text, reflection_text, old_plan_text):
    parts = []
    if kb_text:
        parts.append(kb_text)
    if reflection_text:
        parts.append(reflection_text)
    if mode == 'revise' and old_plan_text:
        parts.append('【原教案】\n' + old_plan_text)
    context = '\n\n'.join(parts)

    if mode == 'generate':
        task = '请生成一份关于「%s」的体育教案。' % (course_info or '未指定主题')
    elif mode == 'activity':
        task = '请为「%s」这节课设计课前、课中、课后一体化教学活动。' % (course_info or '未指定主题')
    else:
        task = '请修订优化这份教案。'

    prompt = task + '\n'
    if user_input:
        prompt += '具体要求：' + user_input + '\n'
    if context:
        prompt += '\n参考资料：\n' + context
    return prompt


def _save_lesson_plan(mode, course_info, user_input, content, lesson_plan_id=None):
    if mode == 'revise' and lesson_plan_id:
        old = db.session.get(LessonPlan, lesson_plan_id)
        group_id = old.group_id if old else uuid.uuid4().hex[:12]
        version = (old.version + 1) if old else 1
        title = (old.title if old else '修订教案')
    else:
        group_id = uuid.uuid4().hex[:12]
        version = 1
        title = course_info or (user_input[:40] if user_input else '未命名教案')
    import html as html_mod
    content_html = html_mod.escape(content or '').replace('\n', '<br>')
    plan = LessonPlan(group_id=group_id, version=version, title=title, subject=course_info, content=content_html)
    db.session.add(plan)
    db.session.commit()
    return plan.id


@rag_bp.route('/search', methods=['POST'])
@login_required
def search():
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '').strip()
    top_k = data.get('top_k', 10)
    if not keyword:
        return jsonify({'results': []})

    uid = current_user_id()
    school = None
    user = db.session.get(User, uid)
    if user and user.school_id:
        school = db.session.get(School, user.school_id)

    results = _search_local(uid, keyword, top_k)
    results += _search_library_mock(school, keyword, top_k)
    results += _search_public_mock(keyword, top_k)
    return jsonify({'results': results[:top_k]})


@rag_bp.route('/cite', methods=['POST'])
@login_required
def cite():
    data = request.get_json(silent=True) or {}
    db.session.add(LessonCite(
        lesson_plan_id=data.get('lesson_plan_id'),
        doc_id=data.get('doc_id'),
        source_name=data.get('source_label', ''),
        title=data.get('title', ''),
        snippet=data.get('snippet', ''),
        url=data.get('url', ''),
    ))
    db.session.commit()
    return jsonify({'ok': True})


@rag_bp.route('/lesson-plan', methods=['POST'])
@login_required
def lesson_plan():
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'generate')  # generate / revise / activity
    model = data.get('model', 'deepseek-chat')
    provider = data.get('provider') or find_provider_by_model(model)
    enable_skill = data.get('enable_skill', True)
    course_info = (data.get('course_info') or '').strip()
    user_input = (data.get('user_input') or '').strip()
    lesson_plan_id = data.get('lesson_plan_id')

    if not provider:
        return jsonify({'error': '未知模型标识：%s' % model}), 400

    # 1. 三层知识库检索
    uid = current_user_id()
    school = None
    user = db.session.get(User, uid)
    if user and user.school_id:
        school = db.session.get(School, user.school_id)
    keyword = user_input or course_info
    snippets = []
    if keyword:
        snippets = _search_local(uid, keyword, 5) + _search_library_mock(school, keyword, 3) + _search_public_mock(keyword, 3)
    kb_text = _format_snippets(snippets)

    # 2. 历史教学反思/听课记录
    reflection_text = _get_reflections_text()

    # 3. 修订模式读取原教案
    old_plan_text = ''
    if mode == 'revise' and lesson_plan_id:
        old = db.session.get(LessonPlan, lesson_plan_id)
        if old:
            old_plan_text = old.content or ''

    # 4. 拼接提示词
    system_prompt = SPORT_LESSON_SKILL if enable_skill else '你是一名专业的体育教师，请按要求生成内容。'
    user_prompt = _build_prompt(mode, course_info, user_input, kb_text, reflection_text, old_plan_text)

    def generate():
        full = ''
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ]
            for delta in chat_stream(provider, model, messages):
                full += delta
                yield 'data: ' + json.dumps({'delta': delta}, ensure_ascii=False) + '\n\n'
            plan_id = _save_lesson_plan(mode, course_info, user_input, full, lesson_plan_id)
            yield 'data: ' + json.dumps({'done': True, 'lesson_plan_id': plan_id}, ensure_ascii=False) + '\n\n'
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield 'data: ' + json.dumps({'error': str(e)}, ensure_ascii=False) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


LEARNING_SHEET_SKILL = """你是一位资深的高校体育教师。请根据提供的教案，生成一份「课前、课中、课后」一体化学习单，帮助学生课前预习、课中参与、课后巩固。

请严格按以下三段输出，每段以对应标记作为标题另起一行：
【课前学习单】
（预习任务、思考问题、准备活动等）
【课中学习单】
（课堂任务、练习要点、合作探究等）
【课后学习单】
（巩固练习、拓展延伸、自评反思等）

内容要贴合教案主题与教学目标，具体可落地执行，语言规范简洁。"""


def _save_learning_sheets(lesson_plan_id, full_text):
    """把 AI 生成的一体化学习单按【课前/课中/课后】标记拆分为三条 LearningSheet。"""
    phases = {'课前学习单': '课前', '课中学习单': '课中', '课后学习单': '课后'}
    LearningSheet.query.filter_by(lesson_plan_id=lesson_plan_id).delete()
    positions = []
    for marker in phases:
        pos = full_text.find('【%s】' % marker)
        if pos != -1:
            positions.append((pos, marker))
    positions.sort()
    for i, (pos, marker) in enumerate(positions):
        content_start = pos + len('【%s】' % marker)
        content_end = positions[i + 1][0] if i + 1 < len(positions) else len(full_text)
        content = full_text[content_start:content_end].strip()
        if content:
            db.session.add(LearningSheet(lesson_plan_id=lesson_plan_id, phase=phases[marker], content=content))
    db.session.commit()


@rag_bp.route('/learning-sheet', methods=['POST'])
@login_required
def learning_sheet():
    """根据已有教案生成课前/课中/课后一体化学习单（SSE 流式）。"""
    import re as _re
    data = request.get_json(silent=True) or {}
    lesson_plan_id = data.get('lesson_plan_id')
    model = data.get('model', 'deepseek-chat')
    provider = data.get('provider') or find_provider_by_model(model)

    plan = db.session.get(LessonPlan, lesson_plan_id) if lesson_plan_id else None
    if not plan:
        return jsonify({'error': '未找到教案'}), 400
    if not provider:
        return jsonify({'error': '未知模型标识：%s' % model}), 400

    plan_text = _re.sub(r'<[^>]+>', '', plan.content or '')
    plan_text = plan_text.replace('&nbsp;', ' ').replace('&amp;', '&').strip()
    user_prompt = '教案标题：%s\n\n教案内容：\n%s\n\n请据此生成课前、课中、课后一体化学习单。' % (plan.title, plan_text)

    def generate():
        full = ''
        try:
            messages = [
                {'role': 'system', 'content': LEARNING_SHEET_SKILL},
                {'role': 'user', 'content': user_prompt},
            ]
            for delta in chat_stream(provider, model, messages):
                full += delta
                yield 'data: ' + json.dumps({'delta': delta}, ensure_ascii=False) + '\n\n'
            _save_learning_sheets(lesson_plan_id, full)
            yield 'data: ' + json.dumps({'done': True, 'lesson_plan_id': lesson_plan_id}, ensure_ascii=False) + '\n\n'
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield 'data: ' + json.dumps({'error': str(e)}, ensure_ascii=False) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
