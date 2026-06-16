import sqlite3
import random
import string
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date


app = Flask(__name__)
# Секретний ключ потрібен для безпечної роботи сесій (авторизації)
app.secret_key = 'super_secret_zlagoda_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;') # Обов'язково вмикаємо зовнішні ключі
    conn.row_factory = sqlite3.Row # Дозволяє звертатися до колонок за іменами (напр., row['empl_name'])
    return conn

# Головна сторінка: якщо авторизований — на дашборд, якщо ні — на логін
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Авторизація
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id_employee']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Employee WHERE id_employee = ?', (user_id,)).fetchone()
        conn.close()

        # Перевіряємо чи є користувач і чи сходиться хеш пароля
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id_employee']
            session['role'] = user['empl_role']
            session['name'] = f"{user['empl_name']} {user['empl_surname']}"
            return redirect(url_for('dashboard'))
        else:
            flash('Невірний логін або пароль!', 'danger')

    return render_template('login.html')

# Робоча панель (Дашборд)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'], name=session['name'])


# --- РОБОТА З ПРАЦІВНИКАМИ ---
@app.route('/employees')
def employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    role = session.get('role')
    user_id = session.get('user_id')

    # Параметри пошуку
    search_surname = request.args.get('surname', '').strip()
    role_filter = request.args.get('role_filter', '')

    # Додано city, street, zip_code для відображення повної адреси (Вимога 11)
    query = '''
        SELECT id_employee, empl_surname, empl_name, empl_patronymic, empl_role, 
               salary, phone_number, city, street, zip_code 
        FROM Employee 
        WHERE 1=1
    '''
    params = []

    if role == 'Касир':
        # Касир бачить ТІЛЬКИ свій профіль (Вимога 15)
        query += ' AND id_employee = ?'
        params.append(user_id)
    else:
        # Менеджер може шукати за прізвищем (Вимога 11)
        if search_surname:
            query += ' AND empl_surname LIKE ?'
            params.append(f'%{search_surname}%')
        
        # Менеджер може відфільтрувати лише касирів (Вимога 5)
        if role_filter == 'Касир':
            query += " AND empl_role = 'Касир'"

    query += ' ORDER BY empl_surname ASC'
    
    emps = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('employees.html', employees=emps, 
                           search_surname=search_surname, role_filter=role_filter)


@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    # Захист: сторінка доступна тільки Менеджеру
    if session.get('role') != 'Менеджер':
        flash('У вас немає прав для додавання працівників.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Збираємо дані з форми
        id_employee = request.form['id_employee']
        surname = request.form['empl_surname']
        name = request.form['empl_name']
        patronymic = request.form['empl_patronymic']
        role = request.form['empl_role']
        salary = float(request.form['salary'])
        dob = request.form['date_of_birth']
        start_date = request.form['date_of_start']
        phone = request.form['phone_number']
        city = request.form['city']
        street = request.form['street']
        zip_code = request.form['zip_code']
        password = request.form['password']

        # Перевірка 1: Зарплата >= 0
        if salary < 0:
            flash('Зарплата не може бути від\'ємною!', 'danger')
            return redirect(url_for('add_employee'))

        # Перевірка 2: Вік >= 18 років
        dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))

        if age < 18:
            flash('Працівнику має бути не менше 18 років!', 'danger')
            return redirect(url_for('add_employee'))

        # Хешуємо пароль
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            # Чистий SQL для вставки
            conn.execute('''
                INSERT INTO Employee (id_employee, empl_surname, empl_name, empl_patronymic, empl_role, 
                                      salary, date_of_birth, date_of_start, phone_number, city, street, zip_code, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_employee, surname, name, patronymic, role, salary, dob, start_date, phone, city, street, zip_code,
                  hashed_pw))
            conn.commit()
            flash('Працівника успішно додано!', 'success')
            return redirect(url_for('employees'))
        except sqlite3.IntegrityError:
            flash('Помилка: Працівник з таким ID вже існує!', 'danger')
        finally:
            conn.close()

    return render_template('add_employee.html')

#Редагування працівника
@app.route('/edit_employee/<emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    if session.get('role') != 'Менеджер':
        flash('У вас немає прав для редагування працівників.', 'danger')
        return redirect(url_for('employees'))

    # Захист: менеджер не може редагувати себе
    if emp_id == session.get('user_id'):
        flash('Ви не можете редагувати власні дані!', 'danger')
        return redirect(url_for('employees'))

    conn = get_db_connection()
    target_emp = conn.execute('SELECT empl_role FROM Employee WHERE id_employee = ?', (emp_id,)).fetchone()
    
    if not target_emp:
        conn.close()
        flash('Працівника не знайдено.', 'danger')
        return redirect(url_for('employees'))

    # Захист: менеджер не може редагувати інших менеджерів
    if target_emp['empl_role'] == 'Менеджер':
        conn.close()
        flash('У вас немає прав редагувати дані інших менеджерів!', 'danger')
        return redirect(url_for('employees'))

    if request.method == 'POST':
        surname = request.form['empl_surname']
        name = request.form['empl_name']
        patronymic = request.form['empl_patronymic']
        role = request.form['empl_role']
        salary = float(request.form['salary'])
        phone = request.form['phone_number']
        city = request.form['city']
        street = request.form['street']
        zip_code = request.form['zip_code']

        if salary < 0:
            flash('Зарплата не може бути від\'ємною!', 'danger')
            return redirect(url_for('edit_employee', emp_id=emp_id))

        conn.execute('''
            UPDATE Employee 
            SET empl_surname = ?, empl_name = ?, empl_patronymic = ?, empl_role = ?, 
                salary = ?, phone_number = ?, city = ?, street = ?, zip_code = ?
            WHERE id_employee = ?
        ''', (surname, name, patronymic, role, salary, phone, city, street, zip_code, emp_id))
        conn.commit()
        conn.close()
        
        flash('Дані працівника успішно оновлено!', 'success')
        return redirect(url_for('employees'))

    # Для GET-запиту
    emp = conn.execute('SELECT * FROM Employee WHERE id_employee = ?', (emp_id,)).fetchone()
    conn.close()
    return render_template('edit_employee.html', employee=emp)

# --- РОБОТА З КАТЕГОРІЯМИ ---
@app.route('/categories')
def categories():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Запит згідно з ТЗ: виводимо всі категорії, відсортовані за назвою
    cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
    conn.close()

    return render_template('categories.html', categories=cats, role=session.get('role'))


@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено. Тільки Менеджер може додавати категорії.', 'danger')
        return redirect(url_for('categories'))

    if request.method == 'POST':
        name = request.form['category_name'].strip() # .strip() прибирає зайві пробіли по краях
        conn = get_db_connection()

        # ПЕРЕВІРКА НА ДУБЛІКАТ
        existing = conn.execute('SELECT * FROM Category WHERE category_name = ?', (name,)).fetchone()
        if existing:
            flash(f'Категорія з назвою "{name}" вже існує!', 'danger')
            conn.close()
            return redirect(url_for('add_category'))

        conn.execute('INSERT INTO Category (category_name) VALUES (?)', (name,))
        conn.commit()
        conn.close()

        flash('Категорію успішно додано!', 'success')
        return redirect(url_for('categories'))

    return render_template('add_category.html')


# --- РОБОТА З ТОВАРАМИ ---
@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Отримуємо параметри фільтрації з URL
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')

    # Базовий запит
    query = '''
        SELECT p.id_product, p.product_name, p.characteristics, c.category_name, c.category_number 
        FROM Product p
        JOIN Category c ON p.category_number = c.category_number
        WHERE 1=1
    '''
    params = []

    # Додаємо фільтр за назвою
    if search_query:
        query += ' AND p.product_name LIKE ?'
        params.append(f'%{search_query}%')
    
    # Додаємо фільтр за категорією
    if category_filter:
        query += ' AND p.category_number = ?'
        params.append(category_filter)

    query += ' ORDER BY p.product_name ASC'

    prods = conn.execute(query, params).fetchall()
    
    # Отримуємо категорії для випадаючого списку у фільтрі
    cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
    conn.close()

    return render_template('products.html', products=prods, categories=cats, 
                           search=search_query, selected_category=category_filter)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено. Тільки Менеджер може додавати товари.', 'danger')
        return redirect(url_for('products'))

    conn = get_db_connection()

    if request.method == 'POST':
        category_number = request.form['category_number']
        product_name = request.form['product_name'].strip()
        characteristics = request.form['characteristics']

        # ПЕРЕВІРКА НА ДУБЛІКАТ ТОВАРУ
        existing = conn.execute('SELECT * FROM Product WHERE product_name = ?', (product_name,)).fetchone()
        if existing:
            flash(f'Товар з назвою "{product_name}" вже існує!', 'danger')
            conn.close()
            return redirect(url_for('add_product'))

        conn.execute('''
            INSERT INTO Product (category_number, product_name, characteristics) 
            VALUES (?, ?, ?)
        ''', (category_number, product_name, characteristics))
        conn.commit()
        conn.close()

        flash('Товар успішно додано!', 'success')
        return redirect(url_for('products'))

    cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
    conn.close()
    return render_template('add_product.html', categories=cats)


# --- РОБОТА З ТОВАРАМИ В МАГАЗИНІ (НА ВІТРИНІ) ---
@app.route('/store_products')
def store_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    role = session.get('role')
    
    # Отримуємо параметри фільтрації
    upc_filter = request.args.get('upc', '').strip()
    promo_filter = request.args.get('promo', '')

    query = '''
        SELECT sp.UPC, p.product_name, sp.selling_price, sp.products_number, sp.promotional_product 
        FROM Store_Product sp
        JOIN Product p ON sp.id_product = p.id_product
        WHERE 1=1
    '''
    params = []

    # Фільтр за UPC
    if upc_filter:
        query += ' AND sp.UPC = ?'
        params.append(upc_filter)
    
    # Фільтр за акційністю (1 - акційний, 0 - звичайний)
    if promo_filter in ['1', '0']:
        query += ' AND sp.promotional_product = ?'
        params.append(int(promo_filter))

    # РОЗУМНЕ СОРТУВАННЯ ЗА ТЗ
    if role == 'Менеджер':
        query += ' ORDER BY sp.products_number ASC'  # Менеджер бачить сортування за кількістю
    else:
        query += ' ORDER BY p.product_name ASC'      # Касир бачить сортування за назвою

    s_prods = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('store_products.html', store_products=s_prods, 
                           upc=upc_filter, promo=promo_filter)


@app.route('/add_store_product', methods=['GET', 'POST'])
def add_store_product():
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено.', 'danger')
        return redirect(url_for('store_products'))

    conn = get_db_connection()

    if request.method == 'POST':
        upc = request.form['upc']
        id_product = request.form['id_product']
        price = float(request.form['selling_price'])
        number = int(request.form['products_number'])
        # Чекбокс повертає 'on' якщо відмічений, інакше None
        is_prom = 1 if request.form.get('promotional_product') else 0

        # Обмеження цілісності згідно з ТЗ
        if price < 0 or number < 0:
            flash('Ціна та кількість не можуть бути від\'ємними!', 'danger')
            return redirect(url_for('add_store_product'))

        try:
            conn.execute('''
                INSERT INTO Store_Product (UPC, id_product, selling_price, products_number, promotional_product) 
                VALUES (?, ?, ?, ?, ?)
            ''', (upc, id_product, price, number, is_prom))
            conn.commit()
            flash('Товар успішно виставлено на вітрину!', 'success')
            return redirect(url_for('store_products'))
        except sqlite3.IntegrityError:
            flash('Помилка: Товар з таким UPC (штрих-кодом) вже існує!', 'danger')
        finally:
            conn.close()

    # Отримуємо список базових товарів для випадаючого списку
    products = conn.execute('SELECT id_product, product_name FROM Product ORDER BY product_name ASC').fetchall()
    conn.close()

    return render_template('add_store_product.html', products=products)

# ==========================================
# РЕДАГУВАННЯ КАТЕГОРІЙ
# ==========================================
@app.route('/edit_category/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено. Тільки Менеджер може редагувати категорії.', 'danger')
        return redirect(url_for('categories'))

    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['category_name'].strip()

        # ПЕРЕВІРКА НА ДУБЛІКАТ (але виключаємо саму себе з пошуку)
        existing = conn.execute('SELECT * FROM Category WHERE category_name = ? AND category_number != ?', (name, id)).fetchone()
        if existing:
            flash(f'Категорія з назвою "{name}" вже існує!', 'danger')
            conn.close()
            return redirect(url_for('edit_category', id=id))

        conn.execute('UPDATE Category SET category_name = ? WHERE category_number = ?', (name, id))
        conn.commit()
        conn.close()
        flash('Категорію успішно оновлено!', 'success')
        return redirect(url_for('categories'))

    cat = conn.execute('SELECT * FROM Category WHERE category_number = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit_category.html', category=cat)

# ==========================================
# РЕДАГУВАННЯ ТОВАРІВ (БАЗОВИХ)
# ==========================================
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено. Тільки Менеджер може редагувати товари.', 'danger')
        return redirect(url_for('products'))

    conn = get_db_connection()
    if request.method == 'POST':
        cat_number = request.form['category_number']
        prod_name = request.form['product_name'].strip()
        chars = request.form['characteristics']
        
        # ПЕРЕВІРКА НА ДУБЛІКАТ (виключаємо поточний товар)
        existing = conn.execute('SELECT * FROM Product WHERE product_name = ? AND id_product != ?', (prod_name, id)).fetchone()
        if existing:
            flash(f'Товар з назвою "{prod_name}" вже існує!', 'danger')
            conn.close()
            return redirect(url_for('edit_product', id=id))

        conn.execute('''
            UPDATE Product 
            SET category_number = ?, product_name = ?, characteristics = ? 
            WHERE id_product = ?
        ''', (cat_number, prod_name, chars, id))
        conn.commit()
        conn.close()
        flash('Товар успішно оновлено!', 'success')
        return redirect(url_for('products'))

    prod = conn.execute('SELECT * FROM Product WHERE id_product = ?', (id,)).fetchone()
    cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
    conn.close()
    return render_template('edit_product.html', product=prod, categories=cats)

# ==========================================
# РЕДАГУВАННЯ ТОВАРІВ У МАГАЗИНІ (НА ВІТРИНІ)
# ==========================================
@app.route('/edit_store_product/<upc>', methods=['GET', 'POST'])
def edit_store_product(upc):
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено.', 'danger')
        return redirect(url_for('store_products'))

    conn = get_db_connection()
    if request.method == 'POST':
        price = float(request.form['selling_price'])
        number = int(request.form['products_number'])
        is_prom = 1 if request.form.get('promotional_product') else 0

        if price < 0 or number < 0:
            flash('Ціна та кількість не можуть бути від\'ємними!', 'danger')
            return redirect(url_for('edit_store_product', upc=upc))

        conn.execute('''
            UPDATE Store_Product 
            SET selling_price = ?, products_number = ?, promotional_product = ? 
            WHERE UPC = ?
        ''', (price, number, is_prom, upc))
        conn.commit()
        conn.close()
        flash('Товар на вітрині оновлено!', 'success')
        return redirect(url_for('store_products'))

    sp = conn.execute('SELECT * FROM Store_Product WHERE UPC = ?', (upc,)).fetchone()
    conn.close()
    return render_template('edit_store_product.html', store_product=sp)


# --- РОБОТА З КЛІЄНТАМИ ---
@app.route('/customers')
def customers():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    search_surname = request.args.get('surname', '').strip()
    percent_filter = request.args.get('percent', '')

    query = 'SELECT * FROM Customer_Card WHERE 1=1'
    params = []

    if search_surname:
        query += ' AND cust_surname LIKE ?'
        params.append(f'%{search_surname}%')

    if percent_filter:
        query += ' AND percent = ?'
        params.append(percent_filter)

    query += ' ORDER BY cust_surname ASC'

    custs = conn.execute(query, params).fetchall()
    
    # Дістаємо всі існуючі відсотки для випадаючого списку фільтрації
    percents = conn.execute('SELECT DISTINCT percent FROM Customer_Card ORDER BY percent ASC').fetchall()
    conn.close()

    return render_template('customers.html', customers=custs, 
                           search_surname=search_surname, percent_filter=percent_filter,
                           percents=percents)


@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    # Доступ є і у Менеджера, і у Касира, тому перевіряємо лише авторизацію
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        card_number = request.form['card_number']
        surname = request.form['cust_surname']
        name = request.form['cust_name']
        patronymic = request.form['cust_patronymic']
        phone = request.form['phone_number']
        city = request.form['city']
        street = request.form['street']
        zip_code = request.form['zip_code']
        percent = int(request.form['percent'])

        # Перевірка на від'ємний відсоток
        if percent < 0:
            flash('Відсоток знижки не може бути від\'ємним!', 'danger')
            return redirect(url_for('add_customer'))

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO Customer_Card (card_number, cust_surname, cust_name, cust_patronymic, phone_number, city, street, zip_code, percent) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (card_number, surname, name, patronymic, phone, city, street, zip_code, percent))
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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        surname = request.form['cust_surname']
        name = request.form['cust_name']
        patronymic = request.form['cust_patronymic']
        phone = request.form['phone_number']
        city = request.form['city']
        street = request.form['street']
        zip_code = request.form['zip_code']
        percent = int(request.form['percent'])

        if percent < 0:
            flash('Відсоток не може бути від\'ємним!', 'danger')
            return redirect(url_for('edit_customer', card_number=card_number))

        conn.execute('''
            UPDATE Customer_Card
            SET cust_surname=?, cust_name=?, cust_patronymic=?, phone_number=?, city=?, street=?, zip_code=?, percent=?
            WHERE card_number=?
        ''', (surname, name, patronymic, phone, city, street, zip_code, percent, card_number))
        conn.commit()
        conn.close()
        
        flash('Дані клієнта успішно оновлено!', 'success')
        return redirect(url_for('customers'))

    customer = conn.execute('SELECT * FROM Customer_Card WHERE card_number = ?', (card_number,)).fetchone()
    conn.close()
    return render_template('edit_customer.html', customer=customer)


# --- РОБОТА З ЧЕКАМИ ---
@app.route('/receipts')
def receipts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    role = session.get('role')
    user_id = session.get('user_id')

    # Отримуємо параметри фільтрації з URL
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    cashier_id = request.args.get('cashier_id', '')

    # Базовий запит
    query = '''
        SELECT r.check_number, r.print_date, r.sum_total, r.vat, 
               e.empl_surname, e.empl_name, 
               c.percent
        FROM Receipt r
        JOIN Employee e ON r.id_employee = e.id_employee
        LEFT JOIN Customer_Card c ON r.card_number = c.card_number
        WHERE 1=1
    '''
    params = []

    # 1. Фільтр за датами (додаємо час, щоб захопити весь день)
    if date_from:
        query += ' AND r.print_date >= ?'
        params.append(date_from + ' 00:00:00')
    if date_to:
        query += ' AND r.print_date <= ?'
        params.append(date_to + ' 23:59:59')

    # 2. Фільтр за працівником залежно від ролі
    if role == 'Касир':
        # Касир бачить ТІЛЬКИ свої чеки
        query += ' AND r.id_employee = ?'
        params.append(user_id)
    else:
        # Менеджер може фільтрувати за конкретним касиром
        if cashier_id:
            query += ' AND r.id_employee = ?'
            params.append(cashier_id)

    query += ' ORDER BY r.print_date DESC'

    recs = conn.execute(query, params).fetchall()

    # Підрахунок загальної суми для всіх відфільтрованих чеків (Вимоги 19, 20)
    total_sum = sum(r['sum_total'] for r in recs)

    # Отримуємо список касирів для випадаючого списку (тільки для менеджера)
    cashiers = []
    if role == 'Менеджер':
        cashiers = conn.execute("SELECT id_employee, empl_surname, empl_name FROM Employee WHERE empl_role != 'Менеджер' ORDER BY empl_surname ASC").fetchall()

    conn.close()

    return render_template('receipts.html', receipts=recs, 
                           total_sum=total_sum, date_from=date_from, 
                           date_to=date_to, cashier_id=cashier_id, 
                           cashiers=cashiers)


@app.route('/add_receipt', methods=['GET', 'POST'])
def add_receipt():
    # Тільки Касир має право продавати товари
    if session.get('role') != 'Касир':
        flash('Доступ заборонено! Створювати чеки може лише Касир.', 'danger')
        return redirect(url_for('receipts'))

    conn = get_db_connection()

    if request.method == 'POST':
        card_number = request.form.get('card_number') or None
        upcs = request.form.getlist('upc[]')
        quantities = request.form.getlist('quantity[]')

        if not upcs:
            flash('Кошик порожній! Додайте хоча б один товар.', 'danger')
            return redirect(url_for('add_receipt'))

        # 1. ОБ'ЄДНУЄМО ДУБЛІКАТИ ТА ПЕРЕВІРЯЄМО НА ВІД'ЄМНІ ЧИСЛА
        cart = {}
        for upc, qty_str in zip(upcs, quantities):
            try:
                qty = int(qty_str)
            except ValueError:
                flash('Кількість товару має бути числом!', 'danger')
                return redirect(url_for('add_receipt'))
            
            if qty <= 0:
                flash('Кількість товару повинна бути більшою за нуль!', 'danger')
                return redirect(url_for('add_receipt'))
            
            # Додаємо кількість, якщо товар вже є в кошику
            cart[upc] = cart.get(upc, 0) + qty

        import random
        import string
        from datetime import datetime
        
        check_number = 'C' + ''.join(random.choices(string.digits, k=9))
        id_employee = session['user_id']
        print_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sum_total = 0.0
        discount = 0

        if card_number:
            card = conn.execute('SELECT percent FROM Customer_Card WHERE card_number = ?', (card_number,)).fetchone()
            if card:
                discount = card['percent']

        items_to_insert = []
        
        # 2. ПЕРЕВІРЯЄМО НАЯВНІСТЬ ТОВАРУ НА СКЛАДІ
        for upc, total_qty in cart.items():
            prod = conn.execute(
                'SELECT selling_price, products_number, promotional_product FROM Store_Product WHERE UPC = ?',
                (upc,)).fetchone()

            if not prod:
                flash(f'Товар зі штрих-кодом {upc} не знайдено!', 'danger')
                return redirect(url_for('add_receipt'))

            if prod['products_number'] < total_qty:
                flash(f'Помилка: На складі всього {prod["products_number"]} одиниць товару (UPC: {upc}), а ви намагаєтесь продати {total_qty}!', 'danger')
                return redirect(url_for('add_receipt'))

            price = float(prod['selling_price'])
            if prod['promotional_product']:
                price = price * 0.8

            items_to_insert.append({'upc': upc, 'qty': total_qty, 'price': price})
            sum_total += price * total_qty

        # Розрахунок знижки та ПДВ
        sum_total = sum_total * (1 - discount / 100.0)
        vat = sum_total * 0.2

        try:
            # Створюємо чек
            conn.execute('''
                INSERT INTO Receipt (check_number, id_employee, card_number, print_date, sum_total, vat)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (check_number, id_employee, card_number, print_date, sum_total, vat))

            # Списуємо товари
            for item in items_to_insert:
                conn.execute('''
                    INSERT INTO Sale (UPC, check_number, product_number, selling_price)
                    VALUES (?, ?, ?, ?)
                ''', (item['upc'], check_number, item['qty'], item['price']))

                conn.execute('''
                    UPDATE Store_Product
                    SET products_number = products_number - ?
                    WHERE UPC = ?
                ''', (item['qty'], item['upc']))

            conn.commit()
            flash('Чек успішно створено та збережено!', 'success')
            return redirect(url_for('receipts'))
        except Exception as e:
            conn.rollback()
            flash(f'Виникла помилка при збереженні: {str(e)}', 'danger')
        finally:
            conn.close()

    # GET-запит
    store_prods = conn.execute('''
        SELECT sp.UPC, p.product_name, sp.selling_price, sp.promotional_product, sp.products_number
        FROM Store_Product sp
        JOIN Product p ON sp.id_product = p.id_product
        WHERE sp.products_number > 0
    ''').fetchall()

    customers = conn.execute(
        'SELECT card_number, cust_surname, cust_name, percent FROM Customer_Card ORDER BY cust_surname ASC').fetchall()
    conn.close()

    return render_template('add_receipt.html', products=store_prods, customers=customers)

# ==========================================
# ДЕТАЛІ ЧЕКА
# ==========================================
@app.route('/receipt/<check_number>')
def receipt_details(check_number):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # 1. Отримуємо загальну інформацію про чек та касира
    receipt_query = '''
        SELECT r.check_number, r.print_date, r.sum_total, r.vat, 
               e.empl_surname, e.empl_name, 
               c.card_number, c.percent
        FROM Receipt r
        JOIN Employee e ON r.id_employee = e.id_employee
        LEFT JOIN Customer_Card c ON r.card_number = c.card_number
        WHERE r.check_number = ?
    '''
    receipt_info = conn.execute(receipt_query, (check_number,)).fetchone()

    if not receipt_info:
        conn.close()
        flash('Чек не знайдено.', 'danger')
        return redirect(url_for('receipts'))

    # 2. Отримуємо список куплених товарів у цьому чеку
    items_query = '''
        SELECT p.product_name, s.product_number as qty, s.selling_price, 
               (s.product_number * s.selling_price) as total_price
        FROM Sale s
        JOIN Store_Product sp ON s.UPC = sp.UPC
        JOIN Product p ON sp.id_product = p.id_product
        WHERE s.check_number = ?
    '''
    items = conn.execute(items_query, (check_number,)).fetchall()
    conn.close()

    return render_template('receipt_details.html', receipt=receipt_info, items=items)


# ==========================================
# ВИДАЛЕННЯ ДАНИХ (Тільки Менеджер)
# ==========================================

def check_manager_role():
    """Допоміжна функція для перевірки прав"""
    return session.get('role') in ['Менеджер', 'Головний менеджер']

@app.route('/delete_employee/<id>')
def delete_employee(id):
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено.', 'danger')
        return redirect(url_for('employees'))
    
    # Захист від самогубства
    if id == session.get('user_id'):
        flash('Ви не можете видалити самі себе!', 'danger')
        return redirect(url_for('employees'))

    conn = get_db_connection()
    try:
        target_emp = conn.execute('SELECT empl_role FROM Employee WHERE id_employee = ?', (id,)).fetchone()
        
        if not target_emp:
            flash('Працівника не знайдено.', 'danger')
            return redirect(url_for('employees'))

        # Захист: менеджер не може звільнити іншого менеджера
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


@app.route('/delete_category/<int:id>')
def delete_category(id):
    if not check_manager_role():
        flash('Доступ заборонено.', 'danger')
        return redirect(url_for('categories'))

    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM Category WHERE category_number = ?', (id,))
        conn.commit()
        flash('Категорію видалено.', 'success')
    except sqlite3.IntegrityError:
        flash('Помилка: існують товари цієї категорії.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('categories'))

@app.route('/delete_product/<int:id>')
def delete_product(id):
    if not check_manager_role(): return redirect(url_for('products'))
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM Product WHERE id_product = ?', (id,))
        conn.commit()
        flash('Товар видалено.', 'success')
    except sqlite3.IntegrityError:
        flash('Помилка: товар виставлено у магазині.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('products'))

@app.route('/delete_store_product/<upc>')
def delete_store_product(upc):
    if not check_manager_role(): return redirect(url_for('store_products'))
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM Store_Product WHERE UPC = ?', (upc,))
        conn.commit()
        flash('Товар у магазині видалено.', 'success')
    except sqlite3.IntegrityError:
        flash('Помилка: товар є у чеках.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('store_products'))

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

@app.route('/delete_receipt/<check_number>')
def delete_receipt(check_number):
    if not check_manager_role(): return redirect(url_for('receipts'))
    conn = get_db_connection()
    conn.execute('DELETE FROM Receipt WHERE check_number = ?', (check_number,))
    conn.commit()
    conn.close()
    flash('Чек видалено.', 'success')
    return redirect(url_for('receipts'))

# Вихід із системи
@app.route('/logout')
def logout():
    session.clear() # Очищаємо сесію
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)