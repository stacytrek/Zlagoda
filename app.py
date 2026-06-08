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
    # Захист сторінки: якщо не авторизований, викидаємо на логін
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Виконуємо чистий SQL запит згідно з ТЗ (сортування за прізвищем)
    query = '''
        SELECT id_employee, empl_surname, empl_name, empl_role, salary, phone_number, city 
        FROM Employee 
        ORDER BY empl_surname ASC
    '''
    # fetchall() забирає всі рядки, які знайшла база
    emps = conn.execute(query).fetchall()
    conn.close()

    return render_template('employees.html', employees=emps, role=session.get('role'))


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
        name = request.form['category_name']

        conn = get_db_connection()
        # category_number у нас AUTOINCREMENT, тому передаємо тільки назву
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
    # Використовуємо JOIN, щоб замість незрозумілого category_number вивести назву категорії
    # Сортуємо за назвою товару згідно з ТЗ
    query = '''
        SELECT p.id_product, p.product_name, p.characteristics, c.category_name 
        FROM Product p
        JOIN Category c ON p.category_number = c.category_number
        ORDER BY p.product_name ASC
    '''
    prods = conn.execute(query).fetchall()
    conn.close()

    return render_template('products.html', products=prods, role=session.get('role'))


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'Менеджер':
        flash('Доступ заборонено. Тільки Менеджер може додавати товари.', 'danger')
        return redirect(url_for('products'))

    conn = get_db_connection()

    if request.method == 'POST':
        category_number = request.form['category_number']
        product_name = request.form['product_name']
        characteristics = request.form['characteristics']

        conn.execute('''
            INSERT INTO Product (category_number, product_name, characteristics) 
            VALUES (?, ?, ?)
        ''', (category_number, product_name, characteristics))
        conn.commit()
        conn.close()

        flash('Товар успішно додано!', 'success')
        return redirect(url_for('products'))

    # Для GET-запиту (коли просто відкриваємо форму) нам треба дістати всі категорії,
    # щоб заповнити ними випадаючий список у HTML
    cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
    conn.close()

    return render_template('add_product.html', categories=cats)


# --- РОБОТА З ТОВАРАМИ В МАГАЗИНІ (НА ВІТРИНІ) ---
@app.route('/store_products')
def store_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    # JOIN з таблицею Product, щоб вивести назву товару замість id_product
    query = '''
        SELECT sp.UPC, p.product_name, sp.selling_price, sp.products_number, sp.promotional_product 
        FROM Store_Product sp
        JOIN Product p ON sp.id_product = p.id_product
        ORDER BY sp.products_number ASC
    '''
    s_prods = conn.execute(query).fetchall()
    conn.close()

    return render_template('store_products.html', store_products=s_prods, role=session.get('role'))


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


# --- РОБОТА З КЛІЄНТАМИ ---
@app.route('/customers')
def customers():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Виводимо клієнтів, відсортованих за прізвищем
    custs = conn.execute('SELECT * FROM Customer_Card ORDER BY cust_surname ASC').fetchall()
    conn.close()

    return render_template('customers.html', customers=custs, role=session.get('role'))


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


# --- РОБОТА З ЧЕКАМИ ---
@app.route('/receipts')
def receipts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Об'єднуємо Чек, Працівника (щоб бачити ПІБ касира) та Картку (щоб бачити знижку)
    query = '''
        SELECT r.check_number, r.print_date, r.sum_total, r.vat, 
               e.empl_surname, e.empl_name, 
               c.percent
        FROM Receipt r
        JOIN Employee e ON r.id_employee = e.id_employee
        LEFT JOIN Customer_Card c ON r.card_number = c.card_number
        ORDER BY r.print_date DESC
    '''
    recs = conn.execute(query).fetchall()
    conn.close()

    return render_template('receipts.html', receipts=recs, role=session.get('role'))


@app.route('/add_receipt', methods=['GET', 'POST'])
def add_receipt():
    # Захист: тільки Касир має право продавати товари
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

        # Генеруємо унікальний номер чека (наприклад, C + 9 випадкових цифр)
        check_number = 'C' + ''.join(random.choices(string.digits, k=9))
        id_employee = session['user_id']
        print_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sum_total = 0.0
        discount = 0

        # Якщо клієнт дав картку, дістаємо його відсоток знижки
        if card_number:
            card = conn.execute('SELECT percent FROM Customer_Card WHERE card_number = ?', (card_number,)).fetchone()
            if card:
                discount = card['percent']

        items_to_insert = []
        for upc, qty_str in zip(upcs, quantities):
            qty = int(qty_str)
            prod = conn.execute(
                'SELECT selling_price, products_number, promotional_product FROM Store_Product WHERE UPC = ?',
                (upc,)).fetchone()

            # Перевірка наявності товару на складі
            if prod['products_number'] < qty:
                flash(f'Помилка: На складі немає стільки товару з UPC {upc}!', 'danger')
                return redirect(url_for('add_receipt'))

            # Розрахунок ціни (акційний товар = -20% від базової ціни)
            price = float(prod['selling_price'])
            if prod['promotional_product']:
                price = price * 0.8

            items_to_insert.append({'upc': upc, 'qty': qty, 'price': price})
            sum_total += price * qty

        # Застосовуємо знижку клієнта до загальної суми
        sum_total = sum_total * (1 - discount / 100.0)
        # Рахуємо ПДВ (20% від загальної суми)
        vat = sum_total * 0.2

        try:
            # 1. Створюємо запис у таблиці Чека
            conn.execute('''
                INSERT INTO Receipt (check_number, id_employee, card_number, print_date, sum_total, vat)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (check_number, id_employee, card_number, print_date, sum_total, vat))

            # 2. Додаємо товари в чек (таблиця Sale) і списуємо їх зі складу
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
            flash(f'Виникла помилка: {str(e)}', 'danger')
        finally:
            conn.close()

    # Для GET-запиту: збираємо товари в наявності та клієнтів для випадаючих списків
    store_prods = conn.execute('''
        SELECT sp.UPC, p.product_name, sp.selling_price, sp.promotional_product
        FROM Store_Product sp
        JOIN Product p ON sp.id_product = p.id_product
        WHERE sp.products_number > 0
    ''').fetchall()

    customers = conn.execute(
        'SELECT card_number, cust_surname, cust_name, percent FROM Customer_Card ORDER BY cust_surname ASC').fetchall()
    conn.close()

    return render_template('add_receipt.html', products=store_prods, customers=customers)

# Вихід із системи
@app.route('/logout')
def logout():
    session.clear() # Очищаємо сесію
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)