from flask import Flask

from config import Config
from extensions import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from routes.home import home_bp
    app.register_blueprint(home_bp)

    from routes.workbench import workbench_bp
    app.register_blueprint(workbench_bp)

    from routes.classroom import classroom_bp
    app.register_blueprint(classroom_bp)

    from routes.lesson_prep import lesson_prep_bp
    app.register_blueprint(lesson_prep_bp)

    from routes.api import api_bp
    app.register_blueprint(api_bp)

    from routes.rag import rag_bp
    app.register_blueprint(rag_bp)

    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from routes.modules import modules_bp
    app.register_blueprint(modules_bp)

    @app.template_filter('render_plan')
    def render_plan(content):
        import html
        import re
        from markupsafe import Markup
        esc = html.escape(content or '')
        esc = re.sub(r'\[图片\]\s+(/static/uploads/[\w./-]+)', r'<img src="\1" style="max-width:100%;border-radius:6px">', esc)
        esc = esc.replace('\n', '<br>')
        return Markup(esc)

    @app.context_processor
    def inject_globals():
        from datetime import date
        from models import User
        from security import current_user_id
        uid = current_user_id()
        name = ''
        username = ''
        if uid:
            user = db.session.get(User, uid)
            if user:
                name = user.name or user.username
                username = user.username
        week_info = '第 %d 周' % date.today().isocalendar()[1]
        return dict(user_name=name, week_info=week_info,
                    user_initial=(name[:1] if name else '师'),
                    username=username)

    with app.app_context():
        db.create_all()
        _migrate()
        _seed()

    return app


def _migrate():
    """轻量迁移：为已有表补充缺失列（兼容旧库）。"""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    if 'users' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'school_id' not in cols:
            db.session.execute(text('ALTER TABLE users ADD COLUMN school_id INTEGER'))
            db.session.commit()
    if 'schools' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('schools')]
        if 'lib_website' not in cols:
            db.session.execute(text('ALTER TABLE schools ADD COLUMN lib_website VARCHAR(500)'))
            db.session.commit()
    if 'lesson_plans' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('lesson_plans')]
        for col, typ in (('category', 'VARCHAR(40)'), ('sport_item', 'VARCHAR(40)'), ('grade', 'VARCHAR(40)')):
            if col not in cols:
                db.session.execute(text('ALTER TABLE lesson_plans ADD COLUMN %s %s' % (col, typ)))
                db.session.commit()
    if 'student_learning' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('student_learning')]
        for col, typ in (('class_id', 'INTEGER'), ('lesson_plan_id', 'INTEGER'),
                         ('sport_item', 'VARCHAR(40)'), ('period_id', 'INTEGER')):
            if col not in cols:
                db.session.execute(text('ALTER TABLE student_learning ADD COLUMN %s %s' % (col, typ)))
                db.session.commit()
    if 'layered_assignments' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('layered_assignments')]
        for col, typ in (('sport_item', 'VARCHAR(40)'), ('period_id', 'INTEGER')):
            if col not in cols:
                db.session.execute(text('ALTER TABLE layered_assignments ADD COLUMN %s %s' % (col, typ)))
                db.session.commit()
    if 'class_periods' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('class_periods')]
        for col, typ in (('content', 'TEXT'), ('week', 'VARCHAR(20)'), ('section', 'VARCHAR(40)'),
                         ('hours', 'VARCHAR(20)'), ('homework', 'TEXT'), ('course_name', 'VARCHAR(40)'),
                         ('sport_item', 'VARCHAR(40)'), ('location', 'VARCHAR(120)'),
                         ('source_file_id', 'INTEGER'), ('source_type', 'VARCHAR(20)')):
            if col not in cols:
                db.session.execute(text('ALTER TABLE class_periods ADD COLUMN %s %s' % (col, typ)))
                db.session.commit()
    if 'rollcall_records' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('rollcall_records')]
        if 'round_no' not in cols:
            db.session.execute(text('ALTER TABLE rollcall_records ADD COLUMN round_no INTEGER'))
            db.session.commit()
    if 'fitness_records' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('fitness_records')]
        if 'semester' not in cols:
            db.session.execute(text('ALTER TABLE fitness_records ADD COLUMN semester VARCHAR(20)'))
            db.session.commit()
        # 历史数据兼容：跨学年格式（如 2020-2021）截取前 4 位作为单年份，保证历史数据不丢失
        db.session.execute(text("UPDATE fitness_records SET year = substr(year, 1, 4) WHERE year LIKE '%-%'"))
        db.session.commit()
    if 'action_analyses' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('action_analyses')]
        for col, typ in (('mode', 'VARCHAR(20)'), ('pose_data', 'TEXT'),
                         ('metrics_data', 'TEXT'), ('key_frames', 'TEXT'),
                         ('technique_action', 'VARCHAR(80)'), ('status', 'VARCHAR(20)'),
                         ('error', 'TEXT')):
            if col not in cols:
                db.session.execute(text('ALTER TABLE action_analyses ADD COLUMN %s %s' % (col, typ)))
                db.session.commit()
        # 历史记录回填：早期状态字段为空时补为 success
        db.session.execute(text("UPDATE action_analyses SET status='success' WHERE status IS NULL OR status=''"))
        db.session.commit()
        # 历史数据回填：早期上传未记录班级，从学生所属班级反推，保证「班级常见错误汇总」可按班归类
        from models import ActionAnalysis, Student
        dirty = False
        for a in ActionAnalysis.query.filter(ActionAnalysis.class_id.is_(None),
                                             ActionAnalysis.student_id.isnot(None)).all():
            s = db.session.get(Student, a.student_id)
            if s and s.class_id:
                a.class_id = s.class_id
                dirty = True
        if dirty:
            db.session.commit()


def _seed():
    """首次运行写入默认账号、默认院校与默认成绩权重。"""
    from models import User, School, GradeSetting
    from security import hash_password

    if User.query.count() == 0:
        db.session.add(User(
            username='admin',
            password_hash=hash_password('admin123'),
            name='教师',
        ))
        db.session.commit()

    if School.query.count() == 0:
        db.session.add(School(name='示例大学', lib_type='oai', lib_endpoint='', lib_key='', lib_enabled=False))
        db.session.commit()

    admin = User.query.filter_by(username='admin').first()
    if admin and admin.school_id is None:
        admin.school_id = School.query.first().id
        db.session.commit()

    if GradeSetting.query.count() == 0:
        defaults = [
            ('attendance', '考勤', 60),
            ('answer', '课堂答题', 40),
        ]
        for key, name, weight in defaults:
            db.session.add(GradeSetting(key=key, name=name, weight=weight))
        db.session.commit()


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)

