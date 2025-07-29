import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from models import db, User, Habit, HabitLog

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    habit_data = []
    for habit in habits:
        logs = HabitLog.query.filter_by(habit_id=habit.id).order_by(HabitLog.date).all()
        streak = calculate_streak(logs)
        dates = [log.date.strftime('%Y-%m-%d') for log in logs]
        habit_data.append({
            'id': habit.id,
            'name': habit.name,
            'streak': streak,
            'dates': dates
        })
    return render_template('index.html', habits=habit_data)

def calculate_streak(logs):
    if not logs:
        return 0
    streak = 1
    logs = sorted(logs, key=lambda l: l.date, reverse=True)
    last_date = logs[0].date
    for log in logs[1:]:
        if last_date - log.date == timedelta(days=1):
            streak += 1
            last_date = log.date
        else:
            break
    # Check if today is included
    if logs[0].date != date.today():
        streak = 0
    return streak

@app.route('/add_habit', methods=['POST'])
@login_required
def add_habit():
    name = request.form['name']
    if not name.strip():
        flash('Habit name cannot be empty.', 'danger')
        return redirect(url_for('index'))
    habit = Habit(name=name.strip(), user_id=current_user.id)
    db.session.add(habit)
    db.session.commit()
    flash('Habit added!', 'success')
    return redirect(url_for('index'))

@app.route('/log/<int:habit_id>', methods=['POST'])
@login_required
def log_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    today = date.today()
    if HabitLog.query.filter_by(habit_id=habit.id, date=today).first():
        flash('Already logged for today!', 'info')
    else:
        log = HabitLog(habit_id=habit.id, date=today)
        db.session.add(log)
        db.session.commit()
        flash('Habit logged for today!', 'success')
    return redirect(url_for('index'))

@app.route('/progress/<int:habit_id>')
@login_required
def progress(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    logs = HabitLog.query.filter_by(habit_id=habit.id).order_by(HabitLog.date).all()
    dates = [log.date.strftime('%Y-%m-%d') for log in logs]
    return jsonify({'dates': dates, 'name': habit.name})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists('habits.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
