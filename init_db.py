import sqlite3
from werkzeug.security import generate_password_hash


def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Вмикаємо зовнішні ключі (обов'язково для SQLite)
    cursor.execute('PRAGMA foreign_keys = ON;')

    # 1. Таблиця: Категорія
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Category (
            category_number INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name VARCHAR(50) NOT NULL
        )
    ''')

    # 2. Таблиця: Товар
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Product (
            id_product INTEGER PRIMARY KEY AUTOINCREMENT,
            category_number INTEGER NOT NULL,
            product_name VARCHAR(50) NOT NULL,
            characteristics VARCHAR(100) NOT NULL,
            FOREIGN KEY (category_number) REFERENCES Category (category_number) ON UPDATE CASCADE ON DELETE NO ACTION
        )
    ''')

    # 3. Таблиця: Працівник
    # Додано password_hash для виконання вимоги шифрування паролів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Employee (
            id_employee VARCHAR(10) PRIMARY KEY,
            empl_surname VARCHAR(50) NOT NULL,
            empl_name VARCHAR(50) NOT NULL,
            empl_patronymic VARCHAR(50),
            empl_role VARCHAR(10) NOT NULL,
            salary DECIMAL(13,4) NOT NULL,
            date_of_birth DATE NOT NULL,
            date_of_start DATE NOT NULL,
            phone_number VARCHAR(13) NOT NULL,
            city VARCHAR(50) NOT NULL,
            street VARCHAR(50) NOT NULL,
            zip_code VARCHAR(9) NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        )
    ''')

    # 4. Таблиця: Карта клієнта
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Customer_Card (
            card_number VARCHAR(13) PRIMARY KEY,
            cust_surname VARCHAR(50) NOT NULL,
            cust_name VARCHAR(50) NOT NULL,
            cust_patronymic VARCHAR(50),
            phone_number VARCHAR(13) NOT NULL,
            city VARCHAR(50),
            street VARCHAR(50),
            zip_code VARCHAR(9),
            percent INTEGER NOT NULL
        )
    ''')

    # 5. Таблиця: Товар у магазині
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Store_Product (
            UPC VARCHAR(12) PRIMARY KEY,
            UPC_prom VARCHAR(12),
            id_product INTEGER NOT NULL,
            selling_price DECIMAL(13,4) NOT NULL,
            products_number INTEGER NOT NULL,
            promotional_product BOOLEAN NOT NULL,
            FOREIGN KEY (UPC_prom) REFERENCES Store_Product (UPC) ON UPDATE CASCADE ON DELETE SET NULL,
            FOREIGN KEY (id_product) REFERENCES Product (id_product) ON UPDATE CASCADE ON DELETE NO ACTION
        )
    ''')

    # 6. Таблиця: Чек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Receipt (
            check_number VARCHAR(10) PRIMARY KEY,
            id_employee VARCHAR(10) NOT NULL,
            card_number VARCHAR(13),
            print_date DATETIME NOT NULL,
            sum_total DECIMAL(13,4) NOT NULL,
            vat DECIMAL(13,4) NOT NULL,
            FOREIGN KEY (id_employee) REFERENCES Employee (id_employee) ON UPDATE CASCADE ON DELETE NO ACTION,
            FOREIGN KEY (card_number) REFERENCES Customer_Card (card_number) ON UPDATE CASCADE ON DELETE NO ACTION
        )
    ''')

    # 7. Таблиця: Продаж (Sale)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sale (
            UPC VARCHAR(12) NOT NULL,
            check_number VARCHAR(10) NOT NULL,
            product_number INTEGER NOT NULL,
            selling_price DECIMAL(13,4) NOT NULL,
            PRIMARY KEY (UPC, check_number),
            FOREIGN KEY (UPC) REFERENCES Store_Product (UPC) ON UPDATE CASCADE ON DELETE NO ACTION,
            FOREIGN KEY (check_number) REFERENCES Receipt (check_number) ON UPDATE CASCADE ON DELETE CASCADE
        )
    ''')

    # Створення дефолтного менеджера (щоб можна було зайти в систему вперше)
    cursor.execute('SELECT COUNT(*) FROM Employee')
    if cursor.fetchone()[0] == 0:
        hashed_pw = generate_password_hash('admin_zlagoda')
        cursor.execute('''
            INSERT INTO Employee 
            (id_employee, empl_surname, empl_name, empl_role, salary, date_of_birth, date_of_start, phone_number, city, street, zip_code, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('M001', 'Менеджер', 'Головний', 'Менеджер', 25000.00, '2000-01-01', '2023-01-01', '+380990000000', 'Київ',
              'Хрещатик', '01001', hashed_pw))

    conn.commit()
    conn.close()
    print("Структуру бази даних 'ZLAGODA' успішно створено!")


if __name__ == '__main__':
    init_db()