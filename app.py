import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kildear3d_secret_key_2025')
app.config['JSON_AS_ASCII'] = False

# CORS настройки
CORS(app, resources={r"/*": {"origins": "*"}})

# Получаем URL базы данных из переменных окружения Render
DATABASE_URL = os.environ.get('DATABASE_URL')

# Если DATABASE_URL нет, используем SQLite для локальной разработки
if not DATABASE_URL:
    print("⚠️ DATABASE_URL не найден, используем SQLite для локальной разработки")
    import sqlite3
    DB_PATH = 'orders.db'
    USE_SQLITE = True
else:
    USE_SQLITE = False
    # Для PostgreSQL
    urllib.parse.uses_netloc.append("postgres")
    url = urllib.parse.urlparse(DATABASE_URL)

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'kildear3d2025')

def get_db_connection():
    """Получение соединения с БД"""
    if USE_SQLITE:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn

def init_db():
    """Инициализация базы данных"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if USE_SQLITE:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    contact_info TEXT NOT NULL,
                    plastic TEXT,
                    model_link TEXT,
                    requirements TEXT,
                    timestamp TEXT,
                    status TEXT DEFAULT 'new'
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    contact_info TEXT NOT NULL,
                    plastic TEXT,
                    model_link TEXT,
                    requirements TEXT,
                    timestamp TEXT,
                    status TEXT DEFAULT 'new'
                )
            ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Инициализируем БД при запуске
init_db()

# ============ МАРШРУТЫ ============

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Файл index.html не найден", 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as count FROM orders')
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': 'PostgreSQL' if not USE_SQLITE else 'SQLite',
            'orders_count': count,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание заказа"""
    try:
        # Проверяем JSON
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Empty data'}), 400
        
        print(f"📥 Получены данные: {data}")
        
        # Валидация
        required = ['modelName', 'customerName', 'contactInfo']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Сохраняем в БД
        conn = get_db_connection()
        cur = conn.cursor()
        
        if USE_SQLITE:
            cur.execute('''
                INSERT INTO orders 
                (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            ''', (
                data['modelName'],
                data['customerName'],
                data['contactInfo'],
                data.get('plastic', 'Не указан'),
                data.get('modelLink', ''),
                data.get('requirements', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'new'
            ))
            order_id = cur.fetchone()[0]
        else:
            cur.execute('''
                INSERT INTO orders 
                (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                data['modelName'],
                data['customerName'],
                data['contactInfo'],
                data.get('plastic', 'Не указан'),
                data.get('modelLink', ''),
                data.get('requirements', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'new'
            ))
            order_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Заказ #{order_id} создан")
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        }), 201
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получение списка заказов"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if USE_SQLITE:
            cur.execute('SELECT * FROM orders ORDER BY id DESC')
            rows = cur.fetchall()
            orders = [dict(row) for row in rows]
        else:
            cur.execute('SELECT * FROM orders ORDER BY id DESC')
            rows = cur.fetchall()
            orders = []
            for row in rows:
                orders.append({
                    'id': row[0],
                    'model_name': row[1],
                    'customer_name': row[2],
                    'contact_info': row[3],
                    'plastic': row[4],
                    'model_link': row[5],
                    'requirements': row[6],
                    'timestamp': row[7],
                    'status': row[8]
                })
        
        cur.close()
        conn.close()
        
        return jsonify(orders), 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify([]), 200

# ============ АДМИН-ПАНЕЛЬ (упрощенная) ============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Вход</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <form method="POST" style="max-width: 300px; margin: 0 auto;">
                <h1>🔐 Вход в админку</h1>
                <input name="username" placeholder="Логин" style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                <input name="password" type="password" placeholder="Пароль" style="width: 100%; padding: 10px; margin: 10px 0;"><br>
                <button type="submit" style="padding: 10px 20px; background: #333; color: white; border: none;">Войти</button>
                <p style="color: red;">Неверные данные</p>
            </form>
        </body>
        </html>
        '''
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Вход</title></head>
    <body style="font-family: Arial; padding: 40px; text-align: center;">
        <form method="POST" style="max-width: 300px; margin: 0 auto;">
            <h1>🔐 Вход в админку</h1>
            <input name="username" placeholder="Логин" style="width: 100%; padding: 10px; margin: 10px 0;"><br>
            <input name="password" type="password" placeholder="Пароль" style="width: 100%; padding: 10px; margin: 10px 0;"><br>
            <button type="submit" style="padding: 10px 20px; background: #333; color: white; border: none;">Войти</button>
        </form>
    </body>
    </html>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if USE_SQLITE:
            cur.execute('SELECT * FROM orders ORDER BY id DESC')
            rows = cur.fetchall()
            orders = [dict(row) for row in rows]
        else:
            cur.execute('SELECT * FROM orders ORDER BY id DESC')
            rows = cur.fetchall()
            orders = []
            for row in rows:
                orders.append({
                    'id': row[0],
                    'model_name': row[1],
                    'customer_name': row[2],
                    'contact_info': row[3],
                    'plastic': row[4],
                    'requirements': row[6],
                    'timestamp': row[7],
                    'status': row[8]
                })
        
        cur.close()
        conn.close()
        
        # Простая админка
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Админ-панель</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; border-radius: 10px; display: flex; justify-content: space-between; }
                .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background: #34495e; color: white; }
                tr:hover { background: #f9f9f9; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                .status-new { background: #3498db; color: white; }
                .status-processing { background: #f39c12; color: white; }
                .status-completed { background: #27ae60; color: white; }
                .status-cancelled { background: #e74c3c; color: white; }
                .btn { background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Kildear3D Админ-панель</h1>
                <a href="/admin/logout" class="btn">Выйти</a>
            </div>
            <div class="container">
                <h2>Всего заявок: ''' + str(len(orders)) + '''</h2>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Модель</th>
                            <th>Заказчик</th>
                            <th>Контакты</th>
                            <th>Пластик</th>
                            <th>Статус</th>
                            <th>Дата</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        
        for order in orders:
            status_class = f"status-{order['status']}"
            status_text = {
                'new': 'Новая',
                'processing': 'В работе',
                'completed': 'Завершена',
                'cancelled': 'Отменена'
            }.get(order['status'], order['status'])
            
            html += f'''
                <tr>
                    <td>{order['id']}</td>
                    <td>{order['model_name'][:50]}</td>
                    <td>{order['customer_name']}</td>
                    <td>{order['contact_info']}</td>
                    <td>{order['plastic']}</td>
                    <td><span class="status {status_class}">{status_text}</span></td>
                    <td>{order['timestamp']}</td>
                </tr>
            '''
        
        html += '''
                    </tbody>
                </table>
            </div>
            <script>
                setInterval(() => location.reload(), 30000);
            </script>
        </body>
        </html>
        '''
        return html
        
    except Exception as e:
        return f"<h1>Ошибка</h1><pre>{e}</pre>", 500

# ============ ЗАПУСК ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(f"🚀 Сервер запущен на порту {port}")
    print(f"🌐 Сайт: http://localhost:{port}/")
    print(f"🔐 Админка: http://localhost:{port}/admin/login")
    print(f"📡 API Health: http://localhost:{port}/api/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
