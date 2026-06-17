from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

def register_auth_routes(app, get_db_connection):
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user_id = request.form['id_employee']
            password = request.form['password']
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM Employee WHERE id_employee = ?', (user_id,)).fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id_employee']
                session['role'] = user['empl_role']
                session['name'] = f"{user['empl_name']} {user['empl_surname']}"
                return redirect(url_for('dashboard'))
            else:
                flash('Невірний логін або пароль!', 'danger')
        return render_template('login.html')

    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('dashboard.html', role=session['role'], name=session['name'])

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))