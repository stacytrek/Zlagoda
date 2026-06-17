from flask import Flask
from init_db import init_database
from db import get_db_connection

from route_auth import register_auth_routes
from route_users import register_users_routes
from route_store import register_store_routes

app = Flask(__name__)
app.secret_key = 'super_secret_zlagoda_key'

register_auth_routes(app, get_db_connection)
register_users_routes(app, get_db_connection)
register_store_routes(app, get_db_connection)

with app.app_context():
    init_database()

if __name__ == '__main__':
    app.run(debug=True)