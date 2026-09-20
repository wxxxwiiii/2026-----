"""后台管理：院校管理、公共文献 API 全局配置、API 调用日志。"""
import json

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from models import School, User, ApiLog
from security import login_required
from services.settings import get_public_config, set_setting, PUBLIC_API_KEYS

admin_bp = Blueprint('admin', __name__, url_prefix='/settings/admin')

PUBLIC_LABELS = {
    'nssd': '国家哲学社会科学文献中心',
    'ucdrs': '全国图书馆参考咨询联盟',
    'curriculum': '高等教育课标公开库',
    'cnki': '知网研学',
}
LIB_TYPES = [('oai', 'OAI-PMH'), ('superstar', '超星校内 API')]


@admin_bp.route('/')
@login_required
def index():
    schools = School.query.order_by(School.id).all()
    config = get_public_config()
    logs = ApiLog.query.order_by(ApiLog.id.desc()).limit(50).all()
    return render_template('admin.html', active='settings',
                           schools=schools, config=config, public_labels=PUBLIC_LABELS,
                           public_keys=PUBLIC_API_KEYS, lib_types=LIB_TYPES, logs=logs)


@admin_bp.route('/schools/add', methods=['POST'])
@login_required
def school_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash('院校名称不能为空', 'error')
    else:
        db.session.add(School(
            name=name,
            lib_type=request.form.get('lib_type', 'oai'),
            lib_endpoint=request.form.get('lib_endpoint', '').strip(),
            lib_key=request.form.get('lib_key', '').strip(),
            lib_website=request.form.get('lib_website', '').strip(),
            lib_enabled=(request.form.get('lib_enabled') == '1'),
        ))
        db.session.commit()
        flash('院校已添加', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/schools/<int:sid>/edit', methods=['POST'])
@login_required
def school_edit(sid):
    s = db.get_or_404(School, sid)
    s.name = request.form.get('name', '').strip()
    s.lib_type = request.form.get('lib_type', 'oai')
    s.lib_endpoint = request.form.get('lib_endpoint', '').strip()
    s.lib_key = request.form.get('lib_key', '').strip()
    s.lib_website = request.form.get('lib_website', '').strip()
    s.lib_enabled = (request.form.get('lib_enabled') == '1')
    db.session.commit()
    flash('院校已保存', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/schools/<int:sid>/delete', methods=['POST'])
@login_required
def school_delete(sid):
    if User.query.filter_by(school_id=sid).count() > 0:
        flash('该院校下还有教师账号，请先调整账号所属院校', 'error')
    else:
        s = db.get_or_404(School, sid)
        db.session.delete(s)
        db.session.commit()
        flash('院校已删除', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/public', methods=['POST'])
@login_required
def public_config():
    config = {}
    for k in PUBLIC_API_KEYS:
        config[k] = {
            'enabled': (request.form.get('enabled_%s' % k) == '1'),
            'api_key': request.form.get('key_%s' % k, '').strip(),
            'rate': int(request.form.get('rate_%s' % k, '10') or '10'),
        }
    set_setting('public_api_config', json.dumps(config, ensure_ascii=False))
    flash('公共文献 API 配置已保存', 'success')
    return redirect(url_for('admin.index'))
