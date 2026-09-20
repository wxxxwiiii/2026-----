from flask import Blueprint, render_template

from security import login_required

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
@login_required
def index():
    from models import SchoolClass, Student, Schedule, Todo, Reflection
    stats = {
        'classes': SchoolClass.query.count(),
        'students': Student.query.count(),
        'schedule': Schedule.query.count(),
        'todos': Todo.query.filter_by(done=False).count(),
    }
    recent_todos = Todo.query.filter_by(done=False).order_by(Todo.id.desc()).limit(5).all()
    recent_reflections = Reflection.query.order_by(Reflection.id.desc()).limit(5).all()
    return render_template('dashboard.html', active='home', stats=stats,
                           recent_todos=recent_todos, recent_reflections=recent_reflections)
