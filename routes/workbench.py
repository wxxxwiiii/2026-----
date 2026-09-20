"""教师工作台：课表、学生名册（分班）、教学反思、听课记录、教师待办。"""
import calendar
import csv
import datetime
import io

from flask import Blueprint, render_template, request, redirect, url_for, flash
from openpyxl import load_workbook

from extensions import db
from models import (SchoolClass, Student, Schedule, Reflection, Todo, ClassSportBinding, ClassPeriod,
                    Resource, SPORT_ITEMS, PROJECT_ITEMS, SPORT_VENUES, COURSE_NAMES)
from security import login_required

workbench_bp = Blueprint('workbench', __name__, url_prefix='/workbench')

DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
REFLECTION_KINDS = ['教学反思', '听课记录']
TODO_CATEGORIES = ['备课', '教学', '教研', '其他']


def _int_or_none(v):
    try:
        return int(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _all_classes():
    return SchoolClass.query.order_by(SchoolClass.id).all()


def _class_map():
    return {c.id: c.name for c in _all_classes()}


def _month_grid(year, month):
    cal = calendar.Calendar(firstweekday=0)  # 周一作为一周第一天
    return cal.monthdatescalendar(year, month)


@workbench_bp.route('/')
@login_required
def index():
    items = Schedule.query.order_by(Schedule.day_of_week, Schedule.start_time).all()
    by_day = {i: [s for s in items if (s.day_of_week or 0) == i] for i in range(7)}
    undone_todos = Todo.query.filter_by(done=False).order_by(Todo.id.desc()).limit(6).all()
    today = datetime.date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    weeks = _month_grid(year, month)
    prev = (year - 1, 12) if month == 1 else (year, month - 1)
    next_ = (year + 1, 1) if month == 12 else (year, month + 1)
    return render_template('workbench/index.html', active='workbench',
                           by_day=by_day, days=DAYS, class_map=_class_map(),
                           todos=undone_todos, weeks=weeks, today=today,
                           year=year, month=month, prev=prev, next_=next_,
                           schedule_count=len(items))


# ============ 教师课表 ============

@workbench_bp.route('/schedule')
@login_required
def schedule():
    items = Schedule.query.order_by(Schedule.day_of_week, Schedule.start_time).all()
    by_day = {}
    for i in range(7):
        by_day[i] = [s for s in items if (s.day_of_week or 0) == i]
    return render_template('workbench/schedule.html', active='workbench',
                           by_day=by_day, days=DAYS, classes=_all_classes(),
                           class_map=_class_map())


@workbench_bp.route('/schedule/add', methods=['POST'])
@login_required
def schedule_add():
    db.session.add(Schedule(
        course_name=request.form.get('course_name', '').strip(),
        day_of_week=_int_or_none(request.form.get('day_of_week')) or 0,
        start_time=request.form.get('start_time', ''),
        end_time=request.form.get('end_time', ''),
        location=request.form.get('location', ''),
        class_id=_int_or_none(request.form.get('class_id')),
        note=request.form.get('note', ''),
    ))
    db.session.commit()
    flash('已添加课表', 'success')
    return redirect(url_for('workbench.schedule'))


@workbench_bp.route('/schedule/<int:sid>/edit', methods=['GET', 'POST'])
@login_required
def schedule_edit(sid):
    s = db.get_or_404(Schedule, sid)
    if request.method == 'POST':
        s.course_name = request.form.get('course_name', '').strip()
        s.day_of_week = _int_or_none(request.form.get('day_of_week')) or 0
        s.start_time = request.form.get('start_time', '')
        s.end_time = request.form.get('end_time', '')
        s.location = request.form.get('location', '')
        s.class_id = _int_or_none(request.form.get('class_id'))
        s.note = request.form.get('note', '')
        db.session.commit()
        flash('已保存修改', 'success')
        return redirect(url_for('workbench.schedule'))
    return render_template('workbench/schedule_edit.html', active='workbench',
                           s=s, days=DAYS, classes=_all_classes())


@workbench_bp.route('/schedule/<int:sid>/delete', methods=['POST'])
@login_required
def schedule_delete(sid):
    s = db.get_or_404(Schedule, sid)
    db.session.delete(s)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('workbench.schedule'))


# ============ 班级 ============

@workbench_bp.route('/classes/add', methods=['POST'])
@login_required
def class_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash('班级名称不能为空', 'error')
    else:
        c = SchoolClass(name=name, grade=request.form.get('grade', '').strip(),
                        note=request.form.get('note', ''))
        db.session.add(c)
        db.session.flush()  # 先取得班级 id，用于写绑定
        for sport in request.form.getlist('sport_items'):
            if sport:
                db.session.add(ClassSportBinding(class_id=c.id, sport_item=sport))
        db.session.commit()
        flash('已新建班级', 'success')
    return redirect(url_for('workbench.students'))


@workbench_bp.route('/classes/<int:cid>/edit', methods=['POST'])
@login_required
def class_edit(cid):
    c = db.get_or_404(SchoolClass, cid)
    c.name = request.form.get('name', '').strip()
    c.grade = request.form.get('grade', '').strip()
    c.note = request.form.get('note', '')
    # 重建该班的运动项目绑定（历史分层数据按三元组归档保留，不受解绑影响）
    ClassSportBinding.query.filter_by(class_id=cid).delete()
    for sport in request.form.getlist('sport_items'):
        if sport:
            db.session.add(ClassSportBinding(class_id=cid, sport_item=sport))
    db.session.commit()
    flash('已保存班级', 'success')
    return redirect(url_for('workbench.students'))


@workbench_bp.route('/classes/<int:cid>/delete', methods=['POST'])
@login_required
def class_delete(cid):
    c = db.get_or_404(SchoolClass, cid)
    n = Student.query.filter_by(class_id=cid).count()
    if n > 0:
        flash(f'该班级还有 {n} 名学生，请先移除学生或换班', 'error')
    else:
        ClassSportBinding.query.filter_by(class_id=cid).delete()
        db.session.delete(c)
        db.session.commit()
        flash('已删除班级', 'success')
    return redirect(url_for('workbench.students'))


# ============ 课时管理 ============

@workbench_bp.route('/periods/add', methods=['POST'])
@login_required
def period_add():
    class_id = request.form.get('class_id', type=int)
    name = request.form.get('name', '').strip()
    if not class_id:
        flash('请选择行政班', 'error')
    elif not name:
        flash('请填写课时名称', 'error')
    else:
        db.session.add(ClassPeriod(class_id=class_id, name=name, content=name,
                                   order_no=_int_or_none(request.form.get('order_no')) or 0,
                                   note=request.form.get('note', '').strip(),
                                   source_type='manual'))
        db.session.commit()
        flash('已添加课时', 'success')
    return redirect(url_for('workbench.progress', pclass_id=class_id))


@workbench_bp.route('/periods/<int:pid>/edit', methods=['POST'])
@login_required
def period_edit(pid):
    p = db.get_or_404(ClassPeriod, pid)
    name = request.form.get('name', '').strip()
    content = request.form.get('content', '').strip() or name
    if not content:
        flash('授课内容不能为空', 'error')
        return redirect(url_for('workbench.progress', pclass_id=p.class_id))
    p.name = name or content[:40]
    p.content = content
    p.order_no = _int_or_none(request.form.get('order_no')) or p.order_no
    p.week = request.form.get('week', '').strip()
    p.section = request.form.get('section', '').strip()
    p.hours = request.form.get('hours', '').strip()
    p.homework = request.form.get('homework', '').strip()
    p.course_name = request.form.get('course_name', '').strip()
    p.sport_item = request.form.get('sport_item', '').strip()
    p.location = request.form.get('location', '').strip()
    p.note = request.form.get('note', '').strip()
    db.session.commit()
    flash('已保存课时', 'success')
    return redirect(url_for('workbench.progress', pclass_id=p.class_id))


@workbench_bp.route('/periods/<int:pid>/delete', methods=['POST'])
@login_required
def period_delete(pid):
    p = db.get_or_404(ClassPeriod, pid)
    class_id = p.class_id
    # 仅删除课时本身，历史分层记录按三元组归档保留，不受影响
    db.session.delete(p)
    db.session.commit()
    flash('已删除课时（历史分层数据归档保留）', 'success')
    return redirect(url_for('workbench.progress', pclass_id=class_id))


# ============ 教学进度（课时管理） ============

@workbench_bp.route('/progress')
@login_required
def progress():
    classes = _all_classes()
    pclass_id = request.args.get('pclass_id', type=int)
    if pclass_id is None and classes:
        pclass_id = classes[0].id
    period_class = db.session.get(SchoolClass, pclass_id) if pclass_id else None
    periods = (ClassPeriod.query.filter_by(class_id=pclass_id)
               .order_by(ClassPeriod.order_no, ClassPeriod.id).all()) if pclass_id else []
    # 源文件溯源：进度表导入的课时关联资源库文件
    source_map = {}
    source_ids = [p.source_file_id for p in periods if p.source_file_id]
    if source_ids:
        for r in Resource.query.filter(Resource.id.in_(source_ids)).all():
            source_map[r.id] = r
    # 课时编辑弹窗数据
    periods_data = {p.id: {
        'order_no': p.order_no, 'content': p.content or p.name, 'week': p.week or '',
        'section': p.section or '', 'hours': p.hours or '', 'homework': p.homework or '',
        'course_name': p.course_name or '', 'sport_item': p.sport_item or '',
        'location': p.location or '', 'note': p.note or '',
    } for p in periods}
    return render_template('workbench/progress.html', active='workbench',
                           classes=classes, period_class=period_class, periods=periods,
                           pclass_id=pclass_id, source_map=source_map,
                           project_items=PROJECT_ITEMS, sport_venues=SPORT_VENUES,
                           course_names=COURSE_NAMES, periods_data=periods_data)


# ============ 学生名册 ============

@workbench_bp.route('/students')
@login_required
def students():
    classes = _all_classes()
    cid = request.args.get('class_id', type=int)
    if cid is None and classes:
        cid = classes[0].id
    selected = db.session.get(SchoolClass, cid) if cid else None
    student_list = (Student.query.filter_by(class_id=cid)
                    .order_by(Student.student_no).all()) if cid else []
    counts = {c.id: Student.query.filter_by(class_id=c.id).count() for c in classes}
    bindings_map = {}
    for b in ClassSportBinding.query.order_by(ClassSportBinding.id).all():
        bindings_map.setdefault(b.class_id, []).append(b.sport_item)
    return render_template('workbench/students.html', active='workbench',
                           classes=classes, selected=selected, students=student_list,
                           counts=counts, sport_items=SPORT_ITEMS, bindings_map=bindings_map)


@workbench_bp.route('/students/add', methods=['POST'])
@login_required
def student_add():
    cid = _int_or_none(request.form.get('class_id'))
    name = request.form.get('name', '').strip()
    if not name or not cid:
        flash('请填写姓名并选择班级', 'error')
    else:
        db.session.add(Student(name=name, student_no=request.form.get('student_no', '').strip(),
                               gender=request.form.get('gender', '男'), class_id=cid,
                               note=request.form.get('note', '')))
        db.session.commit()
        flash('已添加学生', 'success')
    return redirect(url_for('workbench.students', class_id=cid))


@workbench_bp.route('/students/<int:sid>/edit', methods=['POST'])
@login_required
def student_edit(sid):
    s = db.get_or_404(Student, sid)
    s.name = request.form.get('name', '').strip()
    s.student_no = request.form.get('student_no', '').strip()
    s.gender = request.form.get('gender', '男')
    s.class_id = _int_or_none(request.form.get('class_id')) or s.class_id
    s.note = request.form.get('note', '')
    db.session.commit()
    flash('已保存学生信息', 'success')
    return redirect(url_for('workbench.students', class_id=s.class_id))


@workbench_bp.route('/students/<int:sid>/delete', methods=['POST'])
@login_required
def student_delete(sid):
    s = db.get_or_404(Student, sid)
    cid = s.class_id
    db.session.delete(s)
    db.session.commit()
    flash('已删除学生', 'success')
    return redirect(url_for('workbench.students', class_id=cid))


@workbench_bp.route('/students/import', methods=['POST'])
@login_required
def students_import():
    cid = _int_or_none(request.form.get('class_id'))
    if not cid:
        flash('请先选择班级', 'error')
        return redirect(url_for('workbench.students'))
    f = request.files.get('file')
    if not f or not f.filename:
        flash('请选择要导入的文件', 'error')
        return redirect(url_for('workbench.students', class_id=cid))
    students_list, err = _parse_roster(f)
    if err:
        flash(err, 'error')
        return redirect(url_for('workbench.students', class_id=cid))
    for s in students_list:
        db.session.add(Student(student_no=s['no'], name=s['name'], gender=s['gender'], class_id=cid))
    db.session.commit()
    flash(f'成功导入 {len(students_list)} 名学生', 'success')
    return redirect(url_for('workbench.students', class_id=cid))


def _parse_roster(file):
    """解析学生名册，返回 (list_of_dict, error)。支持 xlsx/xls/csv。"""
    filename = (file.filename or '').lower()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            wb = load_workbook(file.stream, read_only=True, data_only=True)
            ws = wb.active
            rows = [[('' if c is None else str(c).strip()) for c in row] for row in ws.iter_rows(values_only=True)]
        elif filename.endswith('.csv'):
            raw = file.stream.read()
            text = None
            for enc in ('utf-8-sig', 'gbk', 'utf-8'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                return [], 'CSV 编码无法识别，请另存为 UTF-8 或 GBK'
            rows = [r for r in csv.reader(io.StringIO(text))]
        else:
            return [], '仅支持 .xlsx / .xls / .csv 文件'
    except Exception as e:
        return [], f'文件解析失败：{e}'

    if not rows:
        return [], '文件为空'

    header = rows[0]
    col = {}
    for i, h in enumerate(header):
        hh = str(h).replace(' ', '')
        if hh in ('姓名', 'name', '名字'):
            col['name'] = i
        elif hh in ('学号', 'student_no', '工号'):
            col['no'] = i
        elif hh in ('性别', 'gender'):
            col['gender'] = i
    if 'name' not in col:
        return [], '未找到「姓名」列，请检查表头（需包含：姓名、学号、性别）'

    result = []
    for r in rows[1:]:
        if not r or all(not c for c in r):
            continue
        name = r[col['name']] if 'name' in col and len(r) > col['name'] else ''
        if not name:
            continue
        no = r[col['no']] if 'no' in col and len(r) > col['no'] else ''
        gender = r[col['gender']] if 'gender' in col and len(r) > col['gender'] else ''
        if gender not in ('男', '女'):
            gender = '男'
        result.append({'name': name, 'no': no, 'gender': gender})
    return result, None


# ============ 教学反思 / 听课记录 ============

@workbench_bp.route('/reflections')
@login_required
def reflections():
    kind = request.args.get('kind', '教学反思')
    if kind not in REFLECTION_KINDS:
        kind = '教学反思'
    items = Reflection.query.filter_by(kind=kind).order_by(Reflection.id.desc()).all()
    return render_template('workbench/reflections.html',
                           active='workbench',
                           kind=kind, items=items, classes=_all_classes(), class_map=_class_map())


@workbench_bp.route('/reflections/add', methods=['POST'])
@login_required
def reflection_add():
    kind = request.form.get('kind', '教学反思')
    if kind not in REFLECTION_KINDS:
        kind = '教学反思'
    title = request.form.get('title', '').strip()
    if not title:
        flash('请填写标题', 'error')
    else:
        db.session.add(Reflection(
            kind=kind, title=title, content=request.form.get('content', ''),
            class_id=_int_or_none(request.form.get('class_id')),
            course_name=request.form.get('course_name', '').strip(),
            date=request.form.get('date', ''),
        ))
        db.session.commit()
        flash('已保存', 'success')
    return redirect(url_for('workbench.reflections', kind=kind))


@workbench_bp.route('/reflections/<int:rid>/edit', methods=['GET', 'POST'])
@login_required
def reflection_edit(rid):
    r = db.get_or_404(Reflection, rid)
    if request.method == 'POST':
        r.title = request.form.get('title', '').strip()
        r.content = request.form.get('content', '')
        r.class_id = _int_or_none(request.form.get('class_id'))
        r.course_name = request.form.get('course_name', '').strip()
        r.date = request.form.get('date', '')
        db.session.commit()
        flash('已保存修改', 'success')
        return redirect(url_for('workbench.reflections', kind=r.kind))
    return render_template('workbench/reflection_edit.html',
                           active='workbench',
                           r=r, classes=_all_classes())


@workbench_bp.route('/reflections/<int:rid>/delete', methods=['POST'])
@login_required
def reflection_delete(rid):
    r = db.get_or_404(Reflection, rid)
    kind = r.kind
    db.session.delete(r)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('workbench.reflections', kind=kind))


# ============ 教师待办 ============

@workbench_bp.route('/todos')
@login_required
def todos():
    items = Todo.query.order_by(Todo.done.asc(), Todo.id.desc()).all()
    return render_template('workbench/todos.html', active='workbench',
                           items=items, categories=TODO_CATEGORIES)


@workbench_bp.route('/todos/add', methods=['POST'])
@login_required
def todo_add():
    title = request.form.get('title', '').strip()
    if not title:
        flash('请填写待办内容', 'error')
    else:
        db.session.add(Todo(title=title, category=request.form.get('category', '其他'),
                            due_date=request.form.get('due_date', ''),
                            note=request.form.get('note', '')))
        db.session.commit()
        flash('已添加待办', 'success')
    return redirect(url_for('workbench.todos'))


@workbench_bp.route('/todos/<int:tid>/toggle', methods=['POST'])
@login_required
def todo_toggle(tid):
    t = db.get_or_404(Todo, tid)
    t.done = not t.done
    db.session.commit()
    return redirect(url_for('workbench.todos'))


@workbench_bp.route('/todos/<int:tid>/edit', methods=['POST'])
@login_required
def todo_edit(tid):
    t = db.get_or_404(Todo, tid)
    t.title = request.form.get('title', '').strip()
    t.category = request.form.get('category', '其他')
    t.due_date = request.form.get('due_date', '')
    t.note = request.form.get('note', '')
    db.session.commit()
    flash('已保存待办', 'success')
    return redirect(url_for('workbench.todos'))


@workbench_bp.route('/todos/<int:tid>/delete', methods=['POST'])
@login_required
def todo_delete(tid):
    t = db.get_or_404(Todo, tid)
    db.session.delete(t)
    db.session.commit()
    flash('已删除待办', 'success')
    return redirect(url_for('workbench.todos'))
