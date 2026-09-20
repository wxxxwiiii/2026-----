"""班级动作常见错误汇总：调用文字模型对多人诊断文本归类、合并同类错误。"""
import json

from services.ai import get_client

# 用文字模型做归类（不是视觉模型）
AGGREGATION_MODEL = 'deepseek-chat'


def summarize_class_errors(items):
    """把多人诊断文本归类为「共性错误类型」。

    items: [{'student': 学生名, 'text': 诊断文本}, ...]
    返回: [{'error_name', 'students': [名字], 'description', 'suggestion'}, ...]
    """
    items = [it for it in items if (it.get('text') or '').strip()]
    if not items:
        return []

    lines = ['学生「%s」诊断：%s' % (it['student'], it['text']) for it in items]
    prompt = (
        '你是高校体育动作诊断助手。以下是班级内多位学生的动作诊断文本，'
        '请把共性问题归类为若干「错误类型」，合并同类错误。'
        '严格只输出一个 JSON 数组，每个元素含字段：'
        'error_name(错误类型名，简短)、students(涉及的学生姓名数组)、'
        'description(统一错误描述)、suggestion(统一纠正建议)。'
        '所有字段内容请使用简体中文输出，不要使用英文。'
        '不要输出 JSON 以外的任何文字。\n\n' + '\n\n'.join(lines)
    )

    client = get_client('deepseek')
    resp = client.chat.completions.create(
        model=AGGREGATION_MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    text = (resp.choices[0].message.content or '').strip() if resp.choices else ''

    # 容错解析：去掉可能的 markdown 代码块包裹
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:]
        text = text.strip()
    try:
        groups = json.loads(text)
    except Exception:
        return []
    if not isinstance(groups, list):
        return []
    # 只保留字段齐全的条目
    result = []
    for g in groups:
        if isinstance(g, dict) and g.get('error_name'):
            students = g.get('students')
            # 容错：模型可能把名单返回成单个字符串（如「张三、李四」）
            if isinstance(students, str):
                students = [students]
            if not isinstance(students, list):
                students = []
            result.append({
                'error_name': g.get('error_name', ''),
                'students': students,
                'description': g.get('description', ''),
                'suggestion': g.get('suggestion', ''),
            })
    return result
