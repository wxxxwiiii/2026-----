"""AI 动作识别：视频抽帧（OpenCV）+ 视觉模型分析（DeepSeek 视觉）。"""
import base64
import os
import uuid

import cv2

from config import FRAME_DIR
from services.ai import get_client, PROVIDERS

# DeepSeek 视觉模型：优先读环境变量 VISION_MODEL，默认用 CLAUDE.md 约定的模型名。
# 这样当模型名需要更换时，无需改代码，改环境变量即可。
VISION_MODEL = os.environ.get('VISION_MODEL', 'deepseek-v4-flash-vision-exp')


def extract_frames(video_path, max_frames=6):
    """从视频均匀抽取 max_frames 帧，保存到 FRAME_DIR，返回图片绝对路径列表。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print('[动作识别] 抽帧失败：无法打开视频 %s' % video_path, flush=True)
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print('[动作识别] 视频可读，总帧数=%d' % total, flush=True)
    if total <= 0:
        print('[动作识别] 抽帧失败：总帧数为 0（视频编码可能不被 OpenCV 支持，如 HEVC/H.265）', flush=True)
        cap.release()
        return []
    n = min(max_frames, total)
    indices = [int(total * (i + 0.5) / n) for i in range(n)]
    paths = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        name = 'frame_%s_%d.jpg' % (uuid.uuid4().hex[:8], idx)
        path = os.path.join(FRAME_DIR, name)
        # 用 imencode + open 写文件，避免 cv2.imwrite 不支持中文路径的问题
        ok, buf = cv2.imencode('.jpg', frame)
        if not ok:
            continue
        with open(path, 'wb') as fp:
            fp.write(buf.tobytes())
        paths.append(path)
    cap.release()
    print('[动作识别] 抽帧完成，得到 %d 帧' % len(paths), flush=True)
    return paths


def _image_data_url(path):
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    mime = 'image/' + ('jpeg' if ext in ('jpg', 'jpeg') else ext)
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    return 'data:%s;base64,%s' % (mime, b64)


def analyze_action(frame_paths, sport_type, student_name='', technique_action=''):
    """调用视觉模型分析动作帧，返回「动作缺陷 + 纠错建议」文本。"""
    client = get_client('deepseek')
    base_url = PROVIDERS['deepseek']['base_url']
    tech = ('「%s」' % technique_action) if technique_action else ''
    content = [{
        'type': 'text',
        'text': '请分析以下「%s」%s动作视频帧（学生：%s）。请指出动作缺陷，并给出针对性的纠错建议。'
                '请务必全程使用简体中文回答，不要使用英文或其他语言。' % (
                    sport_type or '未指定项目', tech, student_name or '未知'),
    }]
    for p in frame_paths:
        content.append({'type': 'image_url', 'image_url': {'url': _image_data_url(p)}})

    # 日志：实际调用的 model / base_url / 图片数
    print('[动作识别] 调用视觉模型 model=%s base_url=%s 图片数=%d 学生=%s' % (
        VISION_MODEL, base_url, len(frame_paths), student_name or '未知'), flush=True)

    finish_reason = 'N/A'
    content_text = ''
    reasoning_text = ''
    # 推理/视觉模型的 reasoning 会占大量 token；先给足预算，content 仍为空则翻倍重试一次
    for attempt, mt in enumerate((8000, 16000)):
        try:
            resp = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{'role': 'user', 'content': content}],
                temperature=0.4,
                max_tokens=mt,
            )
        except Exception as e:
            print('[动作识别] 视觉模型请求异常 model=%s error=%s' % (VISION_MODEL, e), flush=True)
            raise

        finish_reason = resp.choices[0].finish_reason if resp.choices else 'N/A'
        msg = resp.choices[0].message if resp.choices else None
        content_text = getattr(msg, 'content', '') if msg else ''
        reasoning_text = getattr(msg, 'reasoning_content', '') if msg else ''
        print('[动作识别] 视觉模型响应 model=%s attempt=%d finish_reason=%s content长度=%d reasoning长度=%d' % (
            VISION_MODEL, attempt + 1, finish_reason, len(content_text or ''), len(reasoning_text or '')), flush=True)
        if content_text and content_text.strip():
            break
        print('[动作识别] content 为空，加大 max_tokens 重试', flush=True)

    print('[动作识别] 视觉模型响应全文: %s' % ((content_text or reasoning_text or '(空)')), flush=True)

    # 优先用最终答案 content；仍为空（reasoning 占满 token）则退回 reasoning_content
    result = (content_text or reasoning_text or '').strip()
    if not result:
        print('[动作识别] 视觉模型返回空 content：model=%s finish_reason=%s' % (VISION_MODEL, finish_reason), flush=True)
        raise ValueError('视觉模型未返回诊断内容（model=%s，finish_reason=%s）' % (VISION_MODEL, finish_reason))
    return result
