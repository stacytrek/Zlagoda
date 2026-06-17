from flask import render_template, request, redirect, url_for, session, flash
import sqlite3
import random
import string
from datetime import datetime
from db import check_manager_role

def register_store_routes(app, get_db_connection):
    @app.route('/categories')
    def categories():
        if 'user_id' not in session: 
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        show_hits = request.args.get('hits')
        search_query = request.args.get('search', '').strip()

        if show_hits == '1':
            # Запит з подвійним запереченням
            query = '''
                SELECT cat.category_number, cat.category_name
                FROM Category cat
                WHERE NOT EXISTS (
                    SELECT card.card_number
                    FROM Customer_Card card
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM Receipt r
                        JOIN Sale s ON r.check_number = s.check_number
                        JOIN Store_Product sp ON s.UPC = sp.UPC
                        JOIN Product p ON sp.id_product = p.id_product
                        WHERE r.card_number = card.card_number 
                          AND p.category_number = cat.category_number
                    )
                )
                ORDER BY cat.category_name ASC
            '''
            params = []
        else:
            # Звичайний запит із можливістю пошуку
            query = 'SELECT category_number, category_name FROM Category WHERE 1=1'
            params = []
        
            if search_query:
                query += ' AND category_name LIKE ?'
                params.append(f'%{search_query}%')
            
            query += ' ORDER BY category_name ASC'

        cats = conn.execute(query, params).fetchall()
        conn.close()
    
        return render_template('categories.html', categories=cats, 
                                role=session.get('role'), show_hits=show_hits, 
                                search=search_query)

    @app.route('/add_category', methods=['GET', 'POST'])
    def add_category():
        if session.get('role') != 'Менеджер': return redirect(url_for('categories'))
        if request.method == 'POST':
            name = request.form['category_name'].strip()
            conn = get_db_connection()
            if conn.execute('SELECT * FROM Category WHERE category_name = ?', (name,)).fetchone():
                flash(f'Категорія "{name}" вже існує!', 'danger')
                return redirect(url_for('add_category'))
            conn.execute('INSERT INTO Category (category_name) VALUES (?)', (name,))
            conn.commit()
            conn.close()
            flash('Категорію успішно додано!', 'success')
            return redirect(url_for('categories'))
        return render_template('add_category.html')

    @app.route('/edit_category/<int:id>', methods=['GET', 'POST'])
    def edit_category(id):
        if session.get('role') != 'Менеджер': return redirect(url_for('categories'))
        conn = get_db_connection()
        if request.method == 'POST':
            name = request.form['category_name'].strip()
            if conn.execute('SELECT * FROM Category WHERE category_name = ? AND category_number != ?', (name, id)).fetchone():
                flash(f'Категорія "{name}" вже існує!', 'danger')
                return redirect(url_for('edit_category', id=id))
            conn.execute('UPDATE Category SET category_name = ? WHERE category_number = ?', (name, id))
            conn.commit()
            flash('Категорію оновлено!', 'success')
            return redirect(url_for('categories'))
        cat = conn.execute('SELECT * FROM Category WHERE category_number = ?', (id,)).fetchone()
        return render_template('edit_category.html', category=cat)

    @app.route('/products')
    def products():
        if 'user_id' not in session: return redirect(url_for('login'))
        conn, params = get_db_connection(), []
        search_query = request.args.get('search', '').strip()
        category_filter = request.args.get('category', '')
        show_hits = request.args.get('hits') # Фільтр для подвійного заперечення

        # Якщо натиснуто кнопку "Хіти" - виконуємо подвійне заперечення
        if show_hits == '1':
            query = '''
                SELECT p.id_product, p.product_name, p.characteristics, c.category_name, c.category_number 
                FROM Product p
                JOIN Category c ON p.category_number = c.category_number
                WHERE NOT EXISTS (
                    SELECT card.card_number
                    FROM Customer_Card card
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM Receipt r
                        JOIN Sale s ON r.check_number = s.check_number
                        JOIN Store_Product sp ON s.UPC = sp.UPC
                        WHERE r.card_number = card.card_number 
                          AND sp.id_product = p.id_product
                    )
                )
                ORDER BY p.product_name ASC
            '''
        else:
            # Звичайний запит
            query = '''
                SELECT p.id_product, p.product_name, p.characteristics, c.category_name, c.category_number 
                FROM Product p
                JOIN Category c ON p.category_number = c.category_number 
                WHERE 1=1
            '''
            if search_query:
                query += ' AND p.product_name LIKE ?'
                params.append(f'%{search_query}%')
            if category_filter:
                query += ' AND p.category_number = ?'
                params.append(category_filter)
            query += ' ORDER BY p.product_name ASC'

        prods = conn.execute(query, params).fetchall()
        cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
        conn.close()
        
        return render_template('products.html', products=prods, categories=cats, 
                               search=search_query, selected_category=category_filter, show_hits=show_hits)

    @app.route('/add_product', methods=['GET', 'POST'])
    def add_product():
        if session.get('role') != 'Менеджер': return redirect(url_for('products'))
        conn = get_db_connection()
        if request.method == 'POST':
            cat_num, prod_name, chars = request.form['category_number'], request.form['product_name'].strip(), request.form['characteristics']
            if conn.execute('SELECT * FROM Product WHERE product_name = ?', (prod_name,)).fetchone():
                flash(f'Товар "{prod_name}" вже існує!', 'danger')
                return redirect(url_for('add_product'))
            conn.execute('INSERT INTO Product (category_number, product_name, characteristics) VALUES (?, ?, ?)', (cat_num, prod_name, chars))
            conn.commit()
            flash('Товар успішно додано!', 'success')
            return redirect(url_for('products'))
        cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
        return render_template('add_product.html', categories=cats)

    @app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
    def edit_product(id):
        if session.get('role') != 'Менеджер': return redirect(url_for('products'))
        conn = get_db_connection()
        if request.method == 'POST':
            if conn.execute('SELECT * FROM Product WHERE product_name = ? AND id_product != ?', (request.form['product_name'].strip(), id)).fetchone():
                flash(f'Товар вже існує!', 'danger')
                return redirect(url_for('edit_product', id=id))
            conn.execute('UPDATE Product SET category_number=?, product_name=?, characteristics=? WHERE id_product=?',
                         (request.form['category_number'], request.form['product_name'].strip(), request.form['characteristics'], id))
            conn.commit()
            flash('Товар оновлено!', 'success')
            return redirect(url_for('products'))
        prod = conn.execute('SELECT * FROM Product WHERE id_product = ?', (id,)).fetchone()
        cats = conn.execute('SELECT category_number, category_name FROM Category ORDER BY category_name ASC').fetchall()
        return render_template('edit_product.html', product=prod, categories=cats)

    @app.route('/store_products')
    def store_products():
        if 'user_id' not in session: return redirect(url_for('login'))
        conn, params = get_db_connection(), []
        upc_filter, promo_filter = request.args.get('upc', '').strip(), request.args.get('promo', '')
        query = 'SELECT sp.UPC, p.product_name, sp.selling_price, sp.products_number, sp.promotional_product FROM Store_Product sp JOIN Product p ON sp.id_product = p.id_product WHERE 1=1'
        if upc_filter:
            query += ' AND sp.UPC = ?'
            params.append(upc_filter)
        if promo_filter in ['1', '0']:
            query += ' AND sp.promotional_product = ?'
            params.append(int(promo_filter))
        query += ' ORDER BY sp.products_number ASC' if session.get('role') == 'Менеджер' else ' ORDER BY p.product_name ASC'
        s_prods = conn.execute(query, params).fetchall()
        conn.close()
        return render_template('store_products.html', store_products=s_prods, upc=upc_filter, promo=promo_filter)

    @app.route('/add_store_product', methods=['GET', 'POST'])
    def add_store_product():
        if session.get('role') not in ['Менеджер', 'Головний менеджер']:
            flash('Доступ заборонено.', 'danger')
            return redirect(url_for('store_products'))

        conn = get_db_connection()

        if request.method == 'POST':
            upc = request.form['upc'].strip()
            id_product = request.form['id_product']
            price = float(request.form['selling_price'])
            number = int(request.form['products_number'])
            is_prom = 1 if request.form.get('promotional_product') else 0

            if price < 0 or number < 0:
                flash('Ціна та кількість не можуть бути від\'ємними!', 'danger')
                return redirect(url_for('add_store_product'))

            try:
                # 1. ПЕРЕВІРЯЄМО, ЧИ ІСНУЄ ВЖЕ ТАКИЙ UPC У МАГАЗИНІ
                existing = conn.execute('SELECT * FROM Store_Product WHERE UPC = ?', (upc,)).fetchone()
            
                if existing:
                # Захист: якщо штрих-код той самий, але менеджер обрав ІНШИЙ базовий товар у випадаючому списку
                    if str(existing['id_product']) != str(id_product):
                        flash('Помилка: Цей штрих-код вже закріплений за іншим товаром!', 'danger')
                        return redirect(url_for('add_store_product'))
                    
                    # Якщо товар той самий, просто ДОДАЄМО кількість до існуючої партії
                    conn.execute('''
                        UPDATE Store_Product 
                        SET products_number = products_number + ?, promotional_product = ?
                        WHERE UPC = ?
                    ''', (number, is_prom, upc))
                else:
                    # Якщо такого UPC немає, створюємо нову партію
                    conn.execute('''
                        INSERT INTO Store_Product (UPC, id_product, selling_price, products_number, promotional_product) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (upc, id_product, price, number, is_prom))

                # 2. АВТОМАТИЧНА ПЕРЕОЦІНКА ВСІХ ПАРТІЙ ЦЬОГО ТОВАРУ (Вимога ТЗ)
                # Якщо надійшла нова партія звичайного товару з новою ціною — міняємо ціни всюди
                if is_prom == 0:
                    conn.execute('UPDATE Store_Product SET selling_price = ? WHERE id_product = ? AND promotional_product = 0', (price, id_product))
                    promo_price = price * 0.8
                    conn.execute('UPDATE Store_Product SET selling_price = ? WHERE id_product = ? AND promotional_product = 1', (promo_price, id_product))

                conn.commit()
                flash('Товар успішно додано на вітрину, ціни синхронізовано!', 'success')
                return redirect(url_for('store_products'))

            except Exception as e:
                conn.rollback()
                flash(f'Виникла помилка: {e}', 'danger')
            finally:
                conn.close()

        products = conn.execute('SELECT id_product, product_name FROM Product ORDER BY product_name ASC').fetchall()
        conn.close()
        return render_template('add_store_product.html', products=products)

    @app.route('/edit_store_product/<upc>', methods=['GET', 'POST'])
    def edit_store_product(upc):
        if session.get('role') != 'Менеджер': return redirect(url_for('store_products'))
        conn = get_db_connection()
        if request.method == 'POST':
            price, number, is_prom = float(request.form['selling_price']), int(request.form['products_number']), 1 if request.form.get('promotional_product') else 0
            conn.execute('UPDATE Store_Product SET selling_price=?, products_number=?, promotional_product=? WHERE UPC=?', (price, number, is_prom, upc))
            conn.commit()
            flash('Товар на вітрині оновлено!', 'success')
            return redirect(url_for('store_products'))
        sp = conn.execute('SELECT * FROM Store_Product WHERE UPC = ?', (upc,)).fetchone()
        return render_template('edit_store_product.html', store_product=sp)

    @app.route('/receipts')
    def receipts():
        if 'user_id' not in session: return redirect(url_for('login'))
        conn, params = get_db_connection(), []
        date_from, date_to, cashier_id = request.args.get('date_from', ''), request.args.get('date_to', ''), request.args.get('cashier_id', '')
        query = 'SELECT r.check_number, r.print_date, r.sum_total, r.vat, e.empl_surname, e.empl_name, c.percent FROM Receipt r JOIN Employee e ON r.id_employee = e.id_employee LEFT JOIN Customer_Card c ON r.card_number = c.card_number WHERE 1=1'
        if date_from: query += ' AND r.print_date >= ?'; params.append(date_from + ' 00:00:00')
        if date_to: query += ' AND r.print_date <= ?'; params.append(date_to + ' 23:59:59')
        if session.get('role') == 'Касир':
            query += ' AND r.id_employee = ?'; params.append(session.get('user_id'))
        elif cashier_id:
            query += ' AND r.id_employee = ?'; params.append(cashier_id)
        query += ' ORDER BY r.print_date DESC'
        recs = conn.execute(query, params).fetchall()
        cashiers = conn.execute("SELECT id_employee, empl_surname, empl_name FROM Employee WHERE empl_role != 'Менеджер' ORDER BY empl_surname ASC").fetchall() if session.get('role') == 'Менеджер' else []
        conn.close()
        return render_template('receipts.html', receipts=recs, total_sum=sum(r['sum_total'] for r in recs), date_from=date_from, date_to=date_to, cashier_id=cashier_id, cashiers=cashiers)

    @app.route('/add_receipt', methods=['GET', 'POST'])
    def add_receipt():
        if session.get('role') != 'Касир': return redirect(url_for('receipts'))
        conn = get_db_connection()
        if request.method == 'POST':
            card_number = request.form.get('card_number') or None
            upcs, quantities, cart = request.form.getlist('upc[]'), request.form.getlist('quantity[]'), {}
            for upc, qty_str in zip(upcs, quantities):
                qty = int(qty_str)
                if qty <= 0: return redirect(url_for('add_receipt'))
                cart[upc] = cart.get(upc, 0) + qty
            
            check_number, sum_total, discount, items_to_insert = 'C' + ''.join(random.choices(string.digits, k=9)), 0.0, 0, []
            if card_number:
                card = conn.execute('SELECT percent FROM Customer_Card WHERE card_number = ?', (card_number,)).fetchone()
                if card: discount = card['percent']

            for upc, total_qty in cart.items():
                prod = conn.execute('SELECT selling_price, products_number, promotional_product FROM Store_Product WHERE UPC = ?', (upc,)).fetchone()
                if prod['products_number'] < total_qty: return redirect(url_for('add_receipt'))
                price = float(prod['selling_price']) * 0.8 if prod['promotional_product'] else float(prod['selling_price'])
                items_to_insert.append({'upc': upc, 'qty': total_qty, 'price': price})
                sum_total += price * total_qty

            sum_total, vat = sum_total * (1 - discount / 100.0), sum_total * (1 - discount / 100.0) * 0.2
            try:
                conn.execute('INSERT INTO Receipt VALUES (?, ?, ?, ?, ?, ?)', (check_number, session['user_id'], card_number, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), sum_total, vat))
                for item in items_to_insert:
                    conn.execute('INSERT INTO Sale VALUES (?, ?, ?, ?)', (item['upc'], check_number, item['qty'], item['price']))
                    conn.execute('UPDATE Store_Product SET products_number = products_number - ? WHERE UPC = ?', (item['qty'], item['upc']))
                conn.commit()
                flash('Чек збережено!', 'success')
                return redirect(url_for('receipts'))
            except Exception: conn.rollback()
            finally: conn.close()
        
        store_prods = conn.execute('SELECT sp.UPC, p.product_name, sp.selling_price, sp.promotional_product, sp.products_number FROM Store_Product sp JOIN Product p ON sp.id_product = p.id_product WHERE sp.products_number > 0').fetchall()
        customers = conn.execute('SELECT card_number, cust_surname, cust_name, percent FROM Customer_Card ORDER BY cust_surname ASC').fetchall()
        return render_template('add_receipt.html', products=store_prods, customers=customers)

    @app.route('/receipt/<check_number>')
    def receipt_details(check_number):
        if 'user_id' not in session: return redirect(url_for('login'))
        conn = get_db_connection()
        receipt_info = conn.execute('SELECT r.check_number, r.print_date, r.sum_total, r.vat, e.empl_surname, e.empl_name, c.card_number, c.percent FROM Receipt r JOIN Employee e ON r.id_employee = e.id_employee LEFT JOIN Customer_Card c ON r.card_number = c.card_number WHERE r.check_number = ?', (check_number,)).fetchone()
        items = conn.execute('SELECT p.product_name, s.product_number as qty, s.selling_price, (s.product_number * s.selling_price) as total_price FROM Sale s JOIN Store_Product sp ON s.UPC = sp.UPC JOIN Product p ON sp.id_product = p.id_product WHERE s.check_number = ?', (check_number,)).fetchall()
        conn.close()
        return render_template('receipt_details.html', receipt=receipt_info, items=items)

    @app.route('/product_sales', methods=['GET', 'POST'])
    def product_sales():
        if session.get('role') not in ['Менеджер', 'Головний менеджер']: 
            return redirect(url_for('dashboard'))

        conn = get_db_connection()
        sales_data = []
        date_from = request.form.get('date_from', '') if request.method == 'POST' else ''
        date_to = request.form.get('date_to', '') if request.method == 'POST' else ''

        if request.method == 'POST' and date_from and date_to:
            query = '''
                SELECT p.product_name, SUM(s.product_number) as total_sold
                FROM Sale s
                JOIN Receipt r ON s.check_number = r.check_number
                JOIN Store_Product sp ON s.UPC = sp.UPC
                JOIN Product p ON sp.id_product = p.id_product
                WHERE r.print_date >= ? AND r.print_date <= ?
                GROUP BY p.id_product, p.product_name
                ORDER BY total_sold DESC
            '''
            sales_data = conn.execute(query, (date_from + ' 00:00:00', date_to + ' 23:59:59')).fetchall()

        conn.close()
        return render_template('product_sales.html', sales_data=sales_data, date_from=date_from, date_to=date_to)
    
    @app.route('/delete_category/<int:id>')
    def delete_category(id):
        if not check_manager_role(): return redirect(url_for('categories'))
        conn = get_db_connection()
        try: conn.execute('DELETE FROM Category WHERE category_number = ?', (id,)); conn.commit(); flash('Категорію видалено.', 'success')
        except sqlite3.IntegrityError: flash('Помилка: існують товари цієї категорії.', 'danger')
        return redirect(url_for('categories'))

    @app.route('/delete_product/<int:id>')
    def delete_product(id):
        if not check_manager_role(): return redirect(url_for('products'))
        conn = get_db_connection()
        try: conn.execute('DELETE FROM Product WHERE id_product = ?', (id,)); conn.commit(); flash('Товар видалено.', 'success')
        except sqlite3.IntegrityError: flash('Помилка: товар виставлено у магазині.', 'danger')
        return redirect(url_for('products'))

    @app.route('/delete_store_product/<upc>')
    def delete_store_product(upc):
        if not check_manager_role(): return redirect(url_for('store_products'))
        conn = get_db_connection()
        try: conn.execute('DELETE FROM Store_Product WHERE UPC = ?', (upc,)); conn.commit(); flash('Товар видалено.', 'success')
        except sqlite3.IntegrityError: flash('Помилка: товар є у чеках.', 'danger')
        return redirect(url_for('store_products'))

    @app.route('/delete_receipt/<check_number>')
    def delete_receipt(check_number):
        if not check_manager_role(): return redirect(url_for('receipts'))
        conn = get_db_connection()
        conn.execute('DELETE FROM Receipt WHERE check_number = ?', (check_number,)); conn.commit(); flash('Чек видалено.', 'success')
        return redirect(url_for('receipts'))
    
    @app.route('/cashier_sales', methods=['GET', 'POST'])
    def cashier_sales():
        if session.get('role') not in ['Менеджер', 'Головний менеджер']: 
            return redirect(url_for('dashboard'))

        conn = get_db_connection()
        cashier_data = []
        date_from = request.form.get('date_from', '') if request.method == 'POST' else ''
        date_to = request.form.get('date_to', '') if request.method == 'POST' else ''

        if request.method == 'POST' and date_from and date_to:
            query = '''
                SELECT e.empl_surname, e.empl_name, 
                       COUNT(DISTINCT r.check_number) as receipt_count, 
                       SUM(s.product_number) as total_items
                FROM Employee e
                JOIN Receipt r ON e.id_employee = r.id_employee
                JOIN Sale s ON r.check_number = s.check_number
                WHERE r.print_date >= ? AND r.print_date <= ?
                GROUP BY e.id_employee, e.empl_surname, e.empl_name
                ORDER BY total_items DESC
            '''
            cashier_data = conn.execute(query, (date_from + ' 00:00:00', date_to + ' 23:59:59')).fetchall()

        conn.close()
        return render_template('cashier_sales.html', cashier_data=cashier_data, date_from=date_from, date_to=date_to)