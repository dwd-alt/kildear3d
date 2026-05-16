import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from functools import wraps
import logging
import traceback
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kildear3d_secret_key_2025')
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Настройка CORS - разрешаем все для тестирования
CORS(app, origins='*', supports_credentials=True, methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# База данных
DB_PATH = '/tmp/orders.db'

# Проверка доступа к /tmp
try:
    os.makedirs('/tmp', exist_ok=True)
    test_file = '/tmp/test_write.txt'
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    logger.info("✅ /tmp доступен для записи")
except Exception as e:
    logger.error(f"❌ Ошибка доступа к /tmp: {e}")
    DB_PATH = 'orders.db'
    logger.info(f"⚠️ Используем локальную БД: {DB_PATH}")

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
        logger.info(f"✅ База данных инициализирована: {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Главная страница - отдаем ваш HTML
@app.route('/')
def index():
    try:
        # Пытаемся прочитать ваш index.html
        if os.path.exists('index.html'):
            with open('index.html', 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.error("index.html не найден")
            return "Файл index.html не найден. Пожалуйста, поместите его в ту же директорию, что и app.py", 404
    except Exception as e:
        logger.error(f"Ошибка загрузки index.html: {e}")
        return f"Ошибка загрузки: {e}", 500

# API endpoint для заказов
@app.route('/api/orders', methods=['POST', 'OPTIONS'])
def create_order():
    """Создание нового заказа"""
    # Обработка preflight запроса CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Получаем данные из запроса
        if not request.data:
            logger.error("Пустой запрос")
            return jsonify({'error': 'Пустой запрос'}), 400
        
        data = request.get_json()
        
        if not data:
            logger.error("Не удалось распарсить JSON")
            return jsonify({'error': 'Неверный формат данных'}), 400
        
        logger.info(f"Получены данные: {json.dumps(data, ensure_ascii=False)}")
        
        # Проверяем обязательные поля
        required_fields = ['modelName', 'customerName', 'contactInfo']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Сохраняем в базу данных
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('''
            INSERT INTO orders (
                model_name, 
                customer_name, 
                contact_info, 
                plastic, 
                model_link, 
                requirements, 
                timestamp, 
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['modelName'],
            data['customerName'],
            data['contactInfo'],
            data.get('plastic', 'Не указан'),
            data.get('modelLink', ''),
            data.get('requirements', ''),
            timestamp,
            'new'
        ))
        
        conn.commit()
        order_id = c.lastrowid
        conn.close()
        
        logger.info(f"✅ Заявка #{order_id} успешно создана!")
        
        response_data = {
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 201
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании заказа: {e}")
        logger.error(traceback.format_exc())
        
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

# Получение списка заказов
@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        
        orders = [dict(row) for row in rows]
        
        response = jsonify(orders)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        logger.error(f"Ошибка получения заказов: {e}")
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

# Проверка здоровья
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        db_exists = os.path.exists(DB_PATH)
        response = jsonify({
            'status': 'ok',
            'time': datetime.now().isoformat(),
            'database_exists': db_exists,
            'server': 'running'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ============ АДМИН-ПАНЕЛЬ ============

LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Вход в админ-панель Kildear3D</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            border-radius: 24px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .logo { text-align: center; font-size: 48px; margin-bottom: 20px; }
        input {
            width: 100%;
            padding: 14px 18px;
            margin-bottom: 20px;
            border-radius: 12px;
            border: 1px solid #ddd;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #5a67d8; }
        .error { color: #e74c3c; text-align: center; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🔐</div>
        <h1>Kildear3D Админ</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Админ-панель Kildear3D</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { color: #FFD966; }
        .logout-btn { background: #e74c3c; padding: 10px 20px; border-radius: 8px; text-decoration: none; color: white; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 16px; padding: 20px; flex: 1; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-number { font-size: 32px; font-weight: bold; color: #FFB347; }
        table { width: 100%; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #34495e; color: white; }
        .status { padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status-new { background: #3498db; color: white; }
        .refresh-btn { background: #3498db; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; }
        .view-btn { background: #FFB347; padding: 4px 12px; border-radius: 6px; text-decoration: none; color: #333; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Kildear3D — Админ-панель</h1>
        <div>
            <a href="/admin" class="refresh-btn">🔄 Обновить</a>
            <a href="/admin/logout" class="logout-btn">🚪 Выход</a>
        </div>
    </div>
    <div class="container">
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{{ orders|length }}</div><div>Всего заявок</div></div>
            <div class="stat-card"><div class="stat-number">{{ orders|selectattr('status', 'equalto', 'new')|list|length }}</div><div>Новые</div></div>
        </div>
        <table>
            <thead>
                <tr><th>ID</th><th>Модель</th><th>Заказчик</th><th>Статус</th><th>Дата</th><th>Действия</th></tr>
            </thead>
            <tbody>
                {% for order in orders %}
                <tr>
                    <td>{{ order.id }}</td>
                    <td>{{ order.model_name[:50] }}</td>
                    <td>{{ order.customer_name }}</td>
                    <td><span class="status status-{{ order.status }}">{{ order.status }}</span></td>
                    <td>{{ order.timestamp[:16] }}</td>
                    <td><a href="/admin/order/{{ order.id }}" class="view-btn">Подробнее</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template_string(LOGIN_PAGE, error='Неверные логин или пароль')
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    orders = [dict(row) for row in rows]
    return render_template_string(ADMIN_DASHBOARD, orders=orders)

@app.route('/admin/order/<int:order_id>')
@login_required
def view_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Заявка не найдена", 404
    order = dict(row)
    return render_template_string('''
        <h1>Заявка #{{ order.id }}</h1>
        <pre>{{ order | tojson(indent=2) }}</pre>
        <a href="/admin">Назад</a>
    ''', order=order)

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Сервер Kildear3D запущен!")
    print(f"🌐 Сайт: http://localhost:{port}/")
    print(f"📊 Админ-панель: http://localhost:{port}/admin/login")
    print(f"🔑 Логин: {ADMIN_USERNAME}")
    print(f"🔐 Пароль: {ADMIN_PASSWORD}")
    print(f"💾 База данных: {DB_PATH}")
    print("=" * 60)
    print("\n⚠️  Убедитесь, что файл index.html находится в той же папке, что и app.py")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
