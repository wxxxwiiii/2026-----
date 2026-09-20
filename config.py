import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
FRAME_DIR = os.path.join(UPLOAD_DIR, 'frames')
TMP_DIR = os.path.join(DATA_DIR, 'tmp')

for d in (DATA_DIR, UPLOAD_DIR, FRAME_DIR, TMP_DIR):
    os.makedirs(d, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'pe-teaching-ai-local-secret')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(DATA_DIR, 'app.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 视频文件最大 300MB
    MAX_CONTENT_LENGTH = 300 * 1024 * 1024
    # 允许上传的视频/表格格式
    ALLOWED_VIDEO_EXT = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
    ALLOWED_SHEET_EXT = {'xlsx', 'xls', 'csv'}
