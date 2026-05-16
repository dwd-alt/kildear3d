import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import sys

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kildear3d_secret_key_2025')
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# CORS для всех источников (для теста)
CORS(app, resources={r"/*": {"origins": "*"}})

# Используем /tmp для Render (единственная доступная для записи директория)
DB_PATH = '/tmp/orders.db'

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'kildear3d2025')

# Инициализация БД
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
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
        conn.commit()
        conn.close()
        print(f"✅ База данных создана: {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

# Проверка health перед запуском
if not init_db():
    print("⚠️ Проблема с БД, но продолжаем...")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ МАРШРУТЫ ============

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Kildear3D</title></head>
        <body>
            <h1>🚀 Сервер работает!</h1>
            <p>Файл index.html не найден, но API работает.</p>
            <p>Проверьте: <a href="/api/health">/api/health</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"Ошибка: {e}", 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM orders')
        count = c.fetchone()[0]
        conn.close()
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'orders_count': count,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 200  # Возвращаем 200 даже при ошибке, чтобы фронт мог обработать

@app.route('/api/orders', methods=['POST', 'OPTIONS'])
def create_order():
    """Создание заказа"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Получаем данные
        if not request.is_json:
            print("❌ Не JSON запрос")
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 200
        
        data = request.get_json(silent=True)
        if not data:
            print("❌ Пустые данные")
            return jsonify({'success': False, 'error': 'Empty data'}), 200
        
        print(f"📥 Получены данные: {data}")
        
        # Валидация
        if not data.get('modelName'):
            return jsonify({'success': False, 'error': 'modelName is required'}), 200
        if not data.get('customerName'):
            return jsonify({'success': False, 'error': 'customerName is required'}), 200
        if not data.get('contactInfo'):
            return jsonify({'success': False, 'error': 'contactInfo is required'}), 200
        
        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders 
            (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        conn.commit()
        order_id = c.lastrowid
        conn.close()
        
        print(f"✅ Заказ #{order_id} создан")
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        }), 200
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получение списка заказов"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        
        orders = [dict(row) for row in rows]
        return jsonify(orders), 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify([]), 200

# ============ АДМИН-ПАНЕЛЬ ============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Вход</title></head>
        <body>
            <form method="POST">
                <input name="username" placeholder="Логин"><br>
                <input name="password" type="password" placeholder="Пароль"><br>
                <button type="submit">Войти</button>
                <p style="color:red;">Неверные данные</p>
            </form>
        </body>
        </html>
        """
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Вход в админку</title></head>
    <body>
        <form method="POST">
            <input name="username" placeholder="Логин"><br>
            <input name="password" type="password" placeholder="Пароль"><br>
            <button type="submit">Войти</button>
        </form>
    </body>
    </html>
    """

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        
        orders = [dict(row) for row in rows]
        
        # Простой HTML для админки
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Админ-панель</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                table {{ width: 100%; border-collapse: collapse; background: white; }}
                th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
                th {{ background: #333; color: white; }}
                .status-new {{ background: #3498db; color: white; padding: 2px 8px; border-radius: 4px; }}
                .status-processing {{ background: #f39c12; color: white; padding: 2px 8px; border-radius: 4px; }}
                .status-completed {{ background: #27ae60; color: white; padding: 2px 8px; border-radius: 4px; }}
                .status-cancelled {{ background: #e74c3c; color: white; padding: 2px 8px; border-radius: 4px; }}
                .logout {{ background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; display: inline-block; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <a href="/admin/logout" class="logout">🚪 Выход</a>
            <h1>📋 Заявки ({len(orders)})</h1>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Модель</th>
                    <th>Заказчик</th>
                    <th>Контакты</th>
                    <th>Пластик</th>
                    <th>Статус</th>
                    <th>Дата</th>
                </tr>
        """
        
        for order in orders:
            status_class = f"status-{order['status']}"
            status_text = {
                'new': '🆕 Новая',
                'processing': '⚙️ В работе',
                'completed': '✅ Завершена',
                'cancelled': '❌ Отменена'
            }.get(order['status'], order['status'])
            
            html += f"""
                <tr>
                    <td>{order['id']}</td>
                    <td>{order['model_name'][:50]}</td>
                    <td>{order['customer_name']}</td>
                    <td>{order['contact_info']}</td>
                    <td>{order['plastic']}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td>{order['timestamp']}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"<h1>Ошибка</h1><pre>{e}</pre>", 500

# ============ ЗАПУСК ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(f"🚀 Сервер запущен на порту {port}")
    print(f"🌐 Сайт: http://0.0.0.0:{port}/")
    print(f"🔐 Админка: http://0.0.0.0:{port}/admin/login")
    print(f"📡 API Health: http://0.0.0.0:{port}/api/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
