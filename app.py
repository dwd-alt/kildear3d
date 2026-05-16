import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kildear3d_secret_key_2025')
app.config['JSON_AS_ASCII'] = False

# Настройка CORS - РАЗРЕШАЕМ ВСЕ для тестирования
CORS(app, origins='*', supports_credentials=True)

# База данных
DB_PATH = '/tmp/orders.db'

# Проверка и создание директории /tmp
try:
    os.makedirs('/tmp', exist_ok=True)
    logger.info("✅ Директория /tmp доступна")
except Exception as e:
    logger.error(f"❌ Ошибка с /tmp: {e}")
    DB_PATH = 'orders.db'

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
                model_name TEXT,
                customer_name TEXT,
                contact_info TEXT,
                plastic TEXT,
                model_link TEXT,
                requirements TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'new'
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"✅ База данных готова: {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return False

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ГЛАВНАЯ СТРАНИЦА (ВСТРОЕННАЯ ФОРМА)
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kildear3D - 3D печать на заказ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 10px; text-align: center; }
        .subtitle { color: #666; margin-bottom: 30px; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        textarea { resize: vertical; min-height: 100px; }
        button {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { background: #5a67d8; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { text-align: center; margin-top: 10px; color: #667eea; display: none; }
        .required { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📦 Kildear3D</h1>
        <div class="subtitle">3D печать на заказ</div>
        
        <div id="successMessage" class="message success"></div>
        <div id="errorMessage" class="message error"></div>
        <div id="loading" class="loading">⏳ Отправка...</div>
        
        <form id="orderForm">
            <div class="form-group">
                <label>Название модели <span class="required">*</span></label>
                <input type="text" id="modelName" required>
            </div>
            
            <div class="form-group">
                <label>Ваше имя <span class="required">*</span></label>
                <input type="text" id="customerName" required>
            </div>
            
            <div class="form-group">
                <label>Контактные данные (телефон/email) <span class="required">*</span></label>
                <input type="text" id="contactInfo" required>
            </div>
            
            <div class="form-group">
                <label>Тип пластика / цвет</label>
                <input type="text" id="plastic" placeholder="Например: PLA, черный">
            </div>
            
            <div class="form-group">
                <label>Ссылка на модель (если есть)</label>
                <input type="url" id="modelLink" placeholder="https://...">
            </div>
            
            <div class="form-group">
                <label>Дополнительные требования</label>
                <textarea id="requirements" placeholder="Опишите пожелания по печати..."></textarea>
            </div>
            
            <button type="submit" id="submitBtn">📩 Отправить заявку</button>
        </form>
    </div>
    
    <script>
        const form = document.getElementById('orderForm');
        const submitBtn = document.getElementById('submitBtn');
        const successDiv = document.getElementById('successMessage');
        const errorDiv = document.getElementById('errorMessage');
        const loadingDiv = document.getElementById('loading');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Скрываем старые сообщения
            successDiv.style.display = 'none';
            errorDiv.style.display = 'none';
            
            // Собираем данные
            const formData = {
                modelName: document.getElementById('modelName').value.trim(),
                customerName: document.getElementById('customerName').value.trim(),
                contactInfo: document.getElementById('contactInfo').value.trim(),
                plastic: document.getElementById('plastic').value.trim() || 'Не указан',
                modelLink: document.getElementById('modelLink').value.trim(),
                requirements: document.getElementById('requirements').value.trim()
            };
            
            // Валидация
            if (!formData.modelName || !formData.customerName || !formData.contactInfo) {
                errorDiv.textContent = '❌ Пожалуйста, заполните все обязательные поля';
                errorDiv.style.display = 'block';
                return;
            }
            
            // Показываем загрузку
            submitBtn.disabled = true;
            loadingDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/orders', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                // Проверяем статус ответа
                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(`Сервер вернул ошибку ${response.status}: ${text || 'нет данных'}`);
                }
                
                // Пытаемся получить JSON
                let data;
                try {
                    data = await response.json();
                } catch (e) {
                    throw new Error('Сервер вернул неверный ответ');
                }
                
                if (data.success) {
                    successDiv.textContent = '✅ Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.';
                    successDiv.style.display = 'block';
                    form.reset();
                } else {
                    throw new Error(data.error || 'Неизвестная ошибка');
                }
                
            } catch (error) {
                console.error('Ошибка:', error);
                errorDiv.textContent = '❌ ' + error.message;
                errorDiv.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                loadingDiv.style.display = 'none';
            }
        });
    </script>
</body>
</html>
    ''')

# API ENDPOINTS
@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        return jsonify({
            'status': 'ok',
            'time': datetime.now().isoformat(),
            'database': os.path.exists(DB_PATH)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание нового заказа"""
    try:
        # Получаем данные
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        logger.info(f"Получены данные: {data}")
        
        # Проверяем обязательные поля
        required = ['modelName', 'customerName', 'contactInfo']
        for field in required:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['modelName'].strip(),
            data['customerName'].strip(),
            data['contactInfo'].strip(),
            data.get('plastic', 'Не указан').strip(),
            data.get('modelLink', '').strip(),
            data.get('requirements', '').strip(),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new'
        ))
        conn.commit()
        order_id = c.lastrowid
        conn.close()
        
        logger.info(f"✅ Заявка #{order_id} создана")
        
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        }), 201
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
        return jsonify({'error': str(e)}), 500

# АДМИН-ПАНЕЛЬ
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

ADMIN_PAGE = '''
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
        .orders-table { background: white; border-radius: 16px; overflow-x: auto; padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #34495e; color: white; }
        .status { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-new { background: #3498db; color: white; }
        .refresh-btn { background: #3498db; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; margin-left: 10px; }
        .view-btn { background: #FFB347; padding: 6px 12px; border-radius: 6px; text-decoration: none; color: #333; }
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
        </div>
        <div class="orders-table">
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
    return render_template_string(ADMIN_PAGE, orders=orders)

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
    return render_template_string('''
        <h1>Заявка #{{ order.id }}</h1>
        <pre>{{ order | tojson(indent=2) }}</pre>
        <a href="/admin">Назад</a>
    ''', order=dict(row))

# ЗАПУСК
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(f"🚀 Сервер Kildear3D запущен!")
    print(f"🌐 САЙТ: http://localhost:{port}/")
    print(f"📊 АДМИН: http://localhost:{port}/admin/login")
    print(f"🔑 Логин: {ADMIN_USERNAME}")
    print(f"🔐 Пароль: {ADMIN_PASSWORD}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
