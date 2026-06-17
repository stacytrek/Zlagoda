from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from datetime import datetime, date
import sqlite3
from db import check_manager_role

def register_users_routes(app, get_db_connection):
    @app.route('/employees')
    def employees():
        if 'user_id' not in session: return redirect(url_for('login'))
        conn = get_db_connection()
        role, user_id = session.get('role'), session.get('user_id')
        search_surname = request.args.get('surname', '').strip()
        role_filter = request.args.get('role_filter', '')

        query = 'SELECT id_employee, empl_surname, empl_name, empl_patronymic, empl_role, salary, phone_number, city, street, zip_code FROM Employee WHERE 1=1'
        params = []
        if role == 'Касир':
            query += ' AND id_employee = ?'
            params.append(user_id)
        else:
            if search_surname:
                query += ' AND empl_surname LIKE ?'
                params.append(f'%{search_surname}%')
            if role_filter == 'Касир':
                query += " AND empl_role = 'Касир'"
        query += ' ORDER BY empl_surname ASC'
        emps = conn.execute(query, params).fetchall()
        conn.close()
        return render_template('employees.html', employees=emps, search_surname=search_surname, role_filter=role_filter)

    @app.route('/add_employee', methods=['GET', 'POST'])
    def add_employee():
        if session.get('role') != 'Менеджер':
            flash('У вас немає прав для додавання працівників.', 'danger')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            id_employee, surname, name = request.form['id_employee'], request.form['empl_surname'], request.form['empl_name']
            patronymic, role, salary = request.form['empl_patronymic'], request.form['empl_role'], float(request.form['salary'])
            dob, start_date, phone = request.form['date_of_birth'], request.form['date_of_start'], request.form['phone_number']
            city, street, zip_code, password = request.form['city'], request.form['street'], request.form['zip_code'], request.form['password']

            if salary < 0:
                flash("Зарплата не може бути від'ємною!", 'danger')
                return redirect(url_for('add_employee'))

            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            if age < 18:
                flash('Працівнику має бути не менше 18 років!', 'danger')
                return redirect(url_for('add_employee'))

            hashed_pw = generate_password_hash(password)
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO Employee VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             (id_employee, surname, name, patronymic, role, salary, dob, start_date, phone, city, street, zip_code, hashed_pw))
                conn.commit()
                flash('Працівника успішно додано!', 'success')
                return redirect(url_for('employees'))
            except sqlite3.IntegrityError:
                flash('Помилка: Працівник з таким ID вже існує!', 'danger')
            finally:
                conn.close()
        return render_template('add_employee.html')

    @app.route('/edit_employee/<emp_id>', methods=['GET', 'POST'])
    def edit_employee(emp_id):
        if session.get('role') != 'Менеджер':
            flash('У вас немає прав для редагування.', 'danger')
            return redirect(url_for('employees'))
        if emp_id == session.get('user_id'):
            flash('Ви не можете редагувати власні дані!', 'danger')
            return redirect(url_for('employees'))

        conn = get_db_connection()
        target_emp = conn.execute('SELECT empl_role FROM Employee WHERE id_employee = ?', (emp_id,)).fetchone()
        if target_emp and target_emp['empl_role'] == 'Менеджер':
            conn.close()
            flash('Ви не можете редагувати інших менеджерів!', 'danger')
            return redirect(url_for('employees'))

        if request.method == 'POST':
            salary = float(request.form['salary'])
            if salary < 0:
                flash("Зарплата не може бути від'ємною!", 'danger')
                return redirect(url_for('edit_employee', emp_id=emp_id))
            
            conn.execute('''UPDATE Employee SET empl_surname=?, empl_name=?, empl_patronymic=?, empl_role=?, salary=?, phone_number=?, city=?, street=?, zip_code=? WHERE id_employee=?''',
                         (request.form['empl_surname'], request.form['empl_name'], request.form['empl_patronymic'], request.form['empl_role'], salary, request.form['phone_number'], request.form['city'], request.form['street'], request.form['zip_code'], emp_id))
            conn.commit()
            conn.close()
            flash('Дані працівника оновлено!', 'success')
            return redirect(url_for('employees'))

        emp = conn.execute('SELECT * FROM Employee WHERE id_employee = ?', (emp_id,)).fetchone()
        conn.close()
        return render_template('edit_employee.html', employee=emp)

    @app.route('/delete_employee/<id>')
    def delete_employee(id):
        if session.get('role') != 'Менеджер': return redirect(url_for('employees'))
        if id == session.get('user_id'):
            flash('Ви не можете видалити самі себе!', 'danger')
            return redirect(url_for('employees'))

        conn = get_db_connection()
        try:
            target_emp = conn.execute('SELECT empl_role FROM Employee WHERE id_employee = ?', (id,)).fetchone()
            if target_emp['empl_role'] == 'Менеджер':
                flash('Помилка доступу: ви не можете звільняти інших менеджерів!', 'danger')
                return redirect(url_for('employees'))
            conn.execute('DELETE FROM Employee WHERE id_employee = ?', (id,))
            conn.commit()
            flash('Працівника успішно видалено.', 'success')
        except sqlite3.IntegrityError:
            flash('Неможливо видалити працівника: існують чеки, які він створив.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('employees'))

    @app.route('/customers')
    def customers():
        if 'user_id' not in session: return redirect(url_for('login'))
        conn = get_db_connection()
        search_surname = request.args.get('surname', '').strip()
        percent_filter = request.args.get('percent', '')
        query, params = 'SELECT * FROM Customer_Card WHERE 1=1', []
        if search_surname:
            query += ' AND cust_surname LIKE ?'
            params.append(f'%{search_surname}%')
        if percent_filter:
            query += ' AND percent = ?'
            params.append(percent_filter)
        query += ' ORDER BY cust_surname ASC'
        custs = conn.execute(query, params).fetchall()
        percents = conn.execute('SELECT DISTINCT percent FROM Customer_Card ORDER BY percent ASC').fetchall()
        conn.close()
        return render_template('customers.html', customers=custs, search_surname=search_surname, percent_filter=percent_filter, percents=percents)

    @app.route('/add_customer', methods=['GET', 'POST'])
    def add_customer():
        if 'user_id' not in session: return redirect(url_for('login'))
        if request.method == 'POST':
            percent = int(request.form['percent'])
            if percent < 0:
                flash("Відсоток знижки не може бути від'ємним!", 'danger')
                return redirect(url_for('add_customer'))
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO Customer_Card VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             (request.form['card_number'], request.form['cust_surname'], request.form['cust_name'], request.form['cust_patronymic'], request.form['phone_number'], request.form['city'], request.form['street'], request.form['zip_code'], percent))
                conn.commit()
                flash('Картку клієнта успішно додано!', 'success')
                return redirect(url_for('customers'))
            except sqlite3.IntegrityError:
                flash('Помилка: Картка з таким номером вже існує!', 'danger')
            finally:
                conn.close()
        return render_template('add_customer.html')

    @app.route('/edit_customer/<card_number>', methods=['GET', 'POST'])
    def edit_customer(card_number):
        if 'user_id' not in session: return redirect(url_for('login'))
        conn = get_db_connection()
        if request.method == 'POST':
            percent = int(request.form['percent'])
            if percent < 0:
                flash("Відсоток не може бути від'ємним!", 'danger')
                return redirect(url_for('edit_customer', card_number=card_number))
            conn.execute('UPDATE Customer_Card SET cust_surname=?, cust_name=?, cust_patronymic=?, phone_number=?, city=?, street=?, zip_code=?, percent=? WHERE card_number=?',
                         (request.form['cust_surname'], request.form['cust_name'], request.form['cust_patronymic'], request.form['phone_number'], request.form['city'], request.form['street'], request.form['zip_code'], percent, card_number))
            conn.commit()
            conn.close()
            flash('Дані клієнта успішно оновлено!', 'success')
            return redirect(url_for('customers'))
        customer = conn.execute('SELECT * FROM Customer_Card WHERE card_number = ?', (card_number,)).fetchone()
        conn.close()
        return render_template('edit_customer.html', customer=customer)

    @app.route('/delete_customer/<card_number>')
    def delete_customer(card_number):
        if not check_manager_role(): return redirect(url_for('customers'))
        conn = get_db_connection()
        try:
            conn.execute('DELETE FROM Customer_Card WHERE card_number = ?', (card_number,))
            conn.commit()
            flash('Картку клієнта видалено.', 'success')
        except sqlite3.IntegrityError:
            flash('Помилка: існують чеки з цією карткою.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('customers'))