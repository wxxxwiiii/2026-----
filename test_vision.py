# -*- coding: utf-8 -*-
"""独立测试脚本：验证视觉模型能否正常返回内容（不依赖项目代码）。

用法（先设置环境变量，再运行）：
  set DEEPSEEK_API_KEY=sk-xxxx
  set DEEPSEEK_BASE_URL=https://api.deepseek.com     （可选，默认 deepseek）
  set VISION_MODEL=deepseek-v4-flash-vision-exp      （可选，默认 deepseek-v4-flash-vision-exp）
  python test_vision.py
"""
import os
import sys

from openai import OpenAI

API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
MODEL = os.environ.get('VISION_MODEL', 'deepseek-v4-flash-vision-exp')

# 一张 1x1 红色 PNG（base64），用于测试图片输入
TINY_PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

if not API_KEY:
    print('请先设置环境变量 DEEPSEEK_API_KEY')
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
print('model=%s base_url=%s key前4位=%s' % (MODEL, BASE_URL, API_KEY[:4]))

# 测试1：纯文本（验证模型名是否有效）
print('\n[测试1] 纯文本')
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': '请回复“OK”两个字。'}],
        max_tokens=50,
    )
    print('  finish_reason=%s content=%r' % (r.choices[0].finish_reason, r.choices[0].message.content))
except Exception as e:
    print('  调用异常：%s' % e)

# 测试2：图片输入（验证视觉能力）
print('\n[测试2] 图片输入')
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{'role': 'user', 'content': [
            {'type': 'text', 'text': '这张图是什么颜色？'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + TINY_PNG}},
        ]}],
        max_tokens=200,
    )
    content = r.choices[0].message.content if r.choices else ''
    print('  finish_reason=%s content=%r' % (r.choices[0].finish_reason, content))
    print('  结论：%s' % ('成功，模型可用' if content else '失败：content 为空'))
except Exception as e:
    print('  调用异常：%s' % e)
