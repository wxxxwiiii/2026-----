from flask import Blueprint, render_template, redirect, url_for, request, flash, session

from models import User
from security import login_required, current_user_id, hash_password, verify_password
from extensions import db
from services.settings import get_setting, set_setting

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and verify_password(password, user.password_hash):
            session['user_id'] = user.id
            nxt = request.args.get('next') or url_for('home.index')
            return redirect(nxt)
        flash('用户名或密码错误', 'error')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # 保存各 AI 服务商密钥
        if request.form.get('deepseek_api_key') is not None:
            set_setting('deepseek_api_key', request.form.get('deepseek_api_key', '').strip())
            set_setting('qwen_api_key', request.form.get('qwen_api_key', '').strip())
            set_setting('ernie_api_key', request.form.get('ernie_api_key', '').strip())
            set_setting('gpt_api_key', request.form.get('gpt_api_key', '').strip())
            flash('AI 模型密钥已保存', 'success')
        # 更新账号信息
        elif request.form.get('name') is not None:
            user = db.session.get(User, current_user_id())
            user.name = request.form.get('name', '').strip() or user.name
            db.session.commit()
            flash('账号信息已保存', 'success')
        # 修改密码
        elif request.form.get('new_password') is not None:
            user = db.session.get(User, current_user_id())
            if verify_password(request.form.get('old_password', ''), user.password_hash):
                user.password_hash = hash_password(request.form.get('new_password', ''))
                db.session.commit()
                flash('密码已修改', 'success')
            else:
                flash('原密码错误', 'error')
        return redirect(url_for('auth.settings'))

    keys = {
        'deepseek': get_setting('deepseek_api_key', ''),
        'qwen': get_setting('qwen_api_key', ''),
        'ernie': get_setting('ernie_api_key', ''),
        'gpt': get_setting('gpt_api_key', ''),
    }
    user = db.session.get(User, current_user_id())
    users = User.query.order_by(User.id).all()
    from models import School
    schools = School.query.order_by(School.id).all()
    return render_template('settings.html', keys=keys, user=user, users=users, schools=schools, active='settings')


@auth_bp.route('/settings/accounts/add', methods=['POST'])
@login_required
def account_add():
    username = request.form.get('username', '').strip()
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')
    if not username or not password:
        flash('用户名和密码不能为空', 'error')
    elif User.query.filter_by(username=username).first():
        flash('该用户名已存在', 'error')
    else:
        db.session.add(User(username=username, name=name, password_hash=hash_password(password)))
        db.session.commit()
        flash('账号已创建', 'success')
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/accounts/<int:uid>/delete', methods=['POST'])
@login_required
def account_delete(uid):
    if uid == current_user_id():
        flash('不能删除当前登录账号', 'error')
    else:
        user = db.get_or_404(User, uid)
        db.session.delete(user)
        db.session.commit()
        flash('账号已删除', 'success')
    return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/accounts/<int:uid>/school', methods=['POST'])
@login_required
def account_school(uid):
    user = db.get_or_404(User, uid)
    school_id = request.form.get('school_id', type=int)
    user.school_id = school_id
    db.session.commit()
    flash('所属院校已更新', 'success')
    return redirect(url_for('auth.settings'))
