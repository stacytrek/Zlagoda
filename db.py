import sqlite3
from flask import session

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;') 
    conn.row_factory = sqlite3.Row 
    return conn

def check_manager_role():
    """Допоміжна функція для перевірки прав"""
    return session.get('role') in ['Менеджер', 'Головний менеджер']