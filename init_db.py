import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_database():
    """Перевіряє, чи є база. Якщо немає — створює з нуля і парсить seed.txt"""
    db_path = 'database.db'

    # Якщо бази немає, ініціалізуємо її
    if not os.path.exists(db_path):
        print("Бази даних не знайдено. Запускаємо автоматичну ініціалізацію...")
        conn = sqlite3.connect(db_path)
        # Вмикаємо перевірку зовнішніх ключів
        conn.execute('PRAGMA foreign_keys = ON;')

        # 1. Створюємо структуру (з файлу schema.sql)
        if os.path.exists('schema.sql'):
            with open('schema.sql', 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
        else:
            print("⚠️ Файл schema.sql не знайдено!")

        # 2. Парсимо та виконуємо стартові дані (з файлу seed.sql)
        if os.path.exists('seed.sql'):
            manager_pw = generate_password_hash('manager123')
            cashier_pw = generate_password_hash('cashier123')

            with open('seed.sql', 'r', encoding='utf-8') as f:
                seed_queries = f.read()

            # Парсинг: Замінюємо плейсхолдери на реальні згенеровані хеші
            seed_queries = seed_queries.replace('{MANAGER_HASH}', manager_pw)
            seed_queries = seed_queries.replace('{CASHIER_HASH}', cashier_pw)

            # Виконуємо запити
            conn.executescript(seed_queries)
            print("Стартові дані з seed.sql успішно завантажено!")
        else:
            print("⚠️ Файл seed.sql не знайдено!")

        conn.commit()
        conn.close()
        
        print("Ініціалізація успішна!")
        print("🔑 Менеджер: логін M001, пароль manager123")
        print("🔑 Касир: логін K001, пароль cashier123")

if __name__ == '__main__':
    init_database()