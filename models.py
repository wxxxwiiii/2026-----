"""数据表定义（SQLAlchemy ORM）。集中在此文件，便于维护与将来迁移。"""
from datetime import datetime

from extensions import db

# 运动项目枚举（班级-运动项目绑定、教案、学情分层共用）
SPORT_ITEMS = ['篮球', '排球', '足球', '田径', '武术', '健美操', '羽毛球', '乒乓球', '其他项目']

# 运动项目 → 技术动作枚举（AI 动作识别「技术动作」下拉用）
SPORT_TECHNIQUES = {
    '排球': ['双手垫球', '正面双手传球', '正面上手发球', '原地起跳扣球', '拦网'],
    '篮球': ['运球', '双手胸前传球', '原地单手肩上投篮', '三步上篮', '防守滑步'],
    '足球': ['脚内侧传球', '脚背正面踢球', '脚背外侧运球', '前额正面头球', '脚内侧停球'],
    '田径': ['蹲踞式起跑', '途中跑', '立定跳远', '背越式跳高', '原地推铅球'],
    '武术': ['弓步冲拳', '马步架打', '正踢腿', '腾空飞脚', '套路'],
    '健美操': ['基本步伐', '开合跳', '单腿平衡', '纵劈腿', '成套动作'],
    '羽毛球': ['正手高远球', '反手发球', '网前挑球', '杀球', '吊球'],
    '乒乓球': ['正手攻球', '反手推挡', '发球', '搓球', '拉球'],
    '其他项目': ['其他'],
}

# 动作诊断记录状态 → 展示标签
ACTION_STATUS_LABELS = {
    'pending': '排队中',
    'processing': '识别中',
    'success': '识别成功',
    'no_human': '未检测到人体',
    'not_install': 'MediaPipe未安装',
    'failed': '识别失败',
}

# 教学进度表：课程名称（固定 4 项）
COURSE_NAMES = ['大学体育一', '大学体育二', '大学体育三', '大学体育四']

# 教学进度表：授课项目 → 对应场地映射（管理员后续可维护）
SPORT_VENUES = {
    '足球': '足球场', '排球': '排球场', '篮球': '篮球场', '田径': '田径场',
    '武术': '武术馆', '体操': '体操馆', '羽毛球': '羽毛球馆', '乒乓球': '乒乓球馆',
    '网球': '网球场', '游泳': '游泳馆', '健美操': '形体舞蹈房', '健身体能': '健身房',
    '其他': '',
}
PROJECT_ITEMS = list(SPORT_VENUES.keys())


class School(db.Model):
    """院校（高校图书馆配置）。lib_type: oai / superstar。"""
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lib_type = db.Column(db.String(20))  # oai / superstar
    lib_endpoint = db.Column(db.String(300))
    lib_key = db.Column(db.String(200))
    lib_website = db.Column(db.String(500))  # 图书馆官网网址（用于跳转）
    lib_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model):
    """教师账号（单机版默认一个，预留多人扩展）。"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(80))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SchoolClass(db.Model):
    """行政班。"""
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.String(40))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Student(db.Model):
    """学生。"""
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(40))
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))  # 男 / 女
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Schedule(db.Model):
    """授课课表。day_of_week: 0=周一 ... 6=周日。"""
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(120), nullable=False)
    day_of_week = db.Column(db.Integer)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    location = db.Column(db.String(120))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    """考勤记录。status: 出勤/缺勤/请假/迟到。"""
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    date = db.Column(db.String(20))
    status = db.Column(db.String(20))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RollCallRecord(db.Model):
    """点名记录。mode: 轮转 / 追问；round_no: 抽取轮次（用于本轮去重）。"""
    __tablename__ = 'rollcall_records'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    mode = db.Column(db.String(20))
    round_no = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AnswerRecord(db.Model):
    """课堂提问作答记录。result: 答对/部分/答错/未答。"""
    __tablename__ = 'answer_records'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    result = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KbDoc(db.Model):
    """知识库文档。source: local（本地上传）/ library（院校图书馆）/ public（公共文献）。"""
    __tablename__ = 'kb_docs'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    school_id = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    doc_type = db.Column(db.String(40))
    source = db.Column(db.String(20))
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KbChunk(db.Model):
    """知识库切片。embedding 预留（暂用关键词检索）。"""
    __tablename__ = 'kb_chunks'
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('kb_docs.id'))
    text = db.Column(db.Text)
    source_name = db.Column(db.String(120))
    embedding = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LessonCite(db.Model):
    """教案引用记录（文献溯源）。lesson_plan_id 待教案生成后绑定。"""
    __tablename__ = 'lesson_cites'
    id = db.Column(db.Integer, primary_key=True)
    lesson_plan_id = db.Column(db.Integer)
    doc_id = db.Column(db.Integer)
    source_name = db.Column(db.String(120))
    title = db.Column(db.String(200))
    snippet = db.Column(db.Text)
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ApiLog(db.Model):
    """公共文献 API 调用日志。"""
    __tablename__ = 'api_logs'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(80))
    keyword = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClassSportBinding(db.Model):
    """班级-运动项目关联配置。教师为自己授课的行政班绑定对应运动项目（可一绑多）。"""
    __tablename__ = 'class_sport_bindings'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    sport_item = db.Column(db.String(40), nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('class_id', 'sport_item', name='uq_class_sport'),)


class ClassPeriod(db.Model):
    """课时：教师按行政班维护的授课课时（可手动添加或教学进度表导入）。"""
    __tablename__ = 'class_periods'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    order_no = db.Column(db.Integer, default=0)          # 课次（数字，排序依据）
    name = db.Column(db.String(200), nullable=False)     # 课时名称（短标题，供分层下拉展示）
    content = db.Column(db.Text)                          # 授课内容（长文本）
    week = db.Column(db.String(20))                       # 星期
    section = db.Column(db.String(40))                    # 节次
    hours = db.Column(db.String(20))                      # 本次学时
    homework = db.Column(db.Text)                         # 作业
    course_name = db.Column(db.String(40))                # 课程名称
    sport_item = db.Column(db.String(40))                 # 授课项目
    location = db.Column(db.String(120))                  # 授课地点
    note = db.Column(db.String(200))                      # 备注
    source_file_id = db.Column(db.Integer)                # 源文件ID（关联资源库 resources.id）
    source_type = db.Column(db.String(20), default='manual')  # manual / schedule_import
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentLearning(db.Model):
    """学生学情记录（体能/技能水平与分层），按 行政班 + 运动项目 + 课时 三元组隔离。"""
    __tablename__ = 'student_learning'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    sport_item = db.Column(db.String(40))
    period_id = db.Column(db.Integer)       # 课时（来自课时管理 class_periods）
    lesson_plan_id = db.Column(db.Integer)  # 旧版关联教案，历史数据归档保留
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    fitness_score = db.Column(db.Float)
    skill_score = db.Column(db.Float)
    level = db.Column(db.String(20))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LayeredAssignment(db.Model):
    """分层作业（含专项作业，记录所属运动项目与课时）。"""
    __tablename__ = 'layered_assignments'
    id = db.Column(db.Integer, primary_key=True)
    lesson_plan_id = db.Column(db.Integer)
    period_id = db.Column(db.Integer)   # 课时（来自课时管理 class_periods）
    sport_item = db.Column(db.String(40))
    level = db.Column(db.String(20))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reflection(db.Model):
    """听课记录 / 教学反思。kind: 听课记录 / 教学反思。"""
    __tablename__ = 'reflections'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    course_name = db.Column(db.String(120))
    date = db.Column(db.String(20))
    lesson_plan_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Todo(db.Model):
    """个人待办。"""
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20))  # 备课/教学/教研/其他
    done = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.String(20))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LessonPlan(db.Model):
    """教案（含版本）。同一教案用 group_id 关联，version 递增。content 为结构化 JSON 字符串。"""
    __tablename__ = 'lesson_plans'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.String(40), index=True)
    version = db.Column(db.Integer, default=1)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    duration = db.Column(db.String(40))
    category = db.Column(db.String(40))   # 资源分类
    sport_item = db.Column(db.String(40))  # 项目类型
    grade = db.Column(db.String(40))       # 年级
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LearningSheet(db.Model):
    """学习单。phase: 课前/课中/课后。"""
    __tablename__ = 'learning_sheets'
    id = db.Column(db.Integer, primary_key=True)
    lesson_plan_id = db.Column(db.Integer, db.ForeignKey('lesson_plans.id'))
    phase = db.Column(db.String(20))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Resource(db.Model):
    """教学资源（资料库）。file_path 为空时表示外部链接。"""
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40))  # 教案模板/教学视频/图片/文档/其他
    file_path = db.Column(db.String(300))
    link = db.Column(db.String(500))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FitnessRecord(db.Model):
    """体测数据与成绩。原始测量值 + 各单项标准分 + 总分与等级。"""
    __tablename__ = 'fitness_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    year = db.Column(db.String(20))  # 学年
    semester = db.Column(db.String(20))  # 学期（第一学期/第二学期，空=全年）
    # 原始测量值
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    bmi = db.Column(db.Float)
    vital_capacity = db.Column(db.Float)       # 肺活量 ml
    run_50m = db.Column(db.Float)              # 秒
    sit_and_reach = db.Column(db.Float)        # 坐位体前屈 cm
    standing_long_jump = db.Column(db.Float)   # 立定跳远 cm
    pull_up = db.Column(db.Integer)            # 引体向上（男）
    sit_up = db.Column(db.Integer)             # 仰卧起坐（女）
    run_1000m = db.Column(db.Float)            # 男
    run_800m = db.Column(db.Float)             # 女
    # 各单项标准分与附加分
    bmi_score = db.Column(db.Float)
    vital_score = db.Column(db.Float)
    run50_score = db.Column(db.Float)
    sitreach_score = db.Column(db.Float)
    jump_score = db.Column(db.Float)
    strength_score = db.Column(db.Float)
    endurance_score = db.Column(db.Float)
    extra_score = db.Column(db.Float)
    total_score = db.Column(db.Float)
    grade = db.Column(db.String(20))  # 优秀/良好/及格/不及格
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FitnessStandard(db.Model):
    """国标评分表。item: BMI/肺活量/50米跑/...；value 为对应分数的成绩值。"""
    __tablename__ = 'fitness_standards'
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(40))
    gender = db.Column(db.String(10))
    grade_group = db.Column(db.String(40))
    score = db.Column(db.Float)
    value = db.Column(db.Float)
    note = db.Column(db.String(200))


class ActionAnalysis(db.Model):
    """动作诊断记录。frames/pose_data/metrics_data/key_frames 为 JSON 字符串。"""
    __tablename__ = 'action_analyses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    sport_type = db.Column(db.String(80))
    technique_action = db.Column(db.String(80))   # 技术动作（如双手垫球、正面上手发球）
    video_path = db.Column(db.String(300))
    frames = db.Column(db.Text)          # 抽帧图片路径 JSON
    mode = db.Column(db.String(20), default='mediapipe')  # 分析模式（当前仅 mediapipe）
    pose_data = db.Column(db.Text)       # 各帧 33 关键点 JSON
    metrics_data = db.Column(db.Text)    # 关节角度/力矩 JSON
    key_frames = db.Column(db.Text)      # 关键帧 JSON
    result = db.Column(db.Text)          # 文字诊断
    status = db.Column(db.String(20), default='success')  # success/no_human/not_install/failed/pending/processing
    error = db.Column(db.Text)           # 失败原因或姿态状态说明
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TrainingPlan(db.Model):
    """专项训练方案（基于班级常见错误汇总生成）。content 为结构化 JSON。"""
    __tablename__ = 'training_plans'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    sport_type = db.Column(db.String(80))
    technique_action = db.Column(db.String(80))
    title = db.Column(db.String(200))
    content = db.Column(db.Text)          # 结构化 JSON：目标/练习/课时安排等
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GradeSetting(db.Model):
    """平时成绩分值分配。key: attendance(考勤)/answer(答题)，weight 为分值，和为 100。"""
    __tablename__ = 'grade_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(40))
    name = db.Column(db.String(80))
    weight = db.Column(db.Float)


class StudentGrade(db.Model):
    """学生平时成绩。"""
    __tablename__ = 'student_grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    term = db.Column(db.String(40))
    attendance_score = db.Column(db.Float)
    answer_score = db.Column(db.Float)
    total = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Setting(db.Model):
    """系统设置（key-value）。"""
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text)
