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
app.secret_key = 'kildear3d_secret_key_2025'
app.config['JSON_AS_ASCII'] = False

# Разрешаем CORS для всех (для тестирования)
CORS(app, origins='*')

# База данных
DB_PATH = 'orders.db'  # Используем локальный файл вместо /tmp

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
        logger.info(f"✅ База данных создана: {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return False

init_db()

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'kildear3d2025'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============= ГЛАВНАЯ СТРАНИЦА =============
@app.route('/')
def index():
    # Простой HTML с формой (без внешних файлов)
    return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kildear3D - 3D печать на заказ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { color: #333; text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #5a67d8; }
        .message {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { text-align: center; margin-top: 10px; color: #667eea; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📦 Kildear3D</h1>
        <div class="subtitle">3D печать на заказ</div>
        
        <div id="successMsg" class="message success"></div>
        <div id="errorMsg" class="message error"></div>
        <div id="loading" class="loading">⏳ Отправка...</div>
        
        <form id="orderForm">
            <div class="form-group">
                <label>Название модели *</label>
                <input type="text" id="modelName" required>
            </div>
            <div class="form-group">
                <label>Ваше имя *</label>
                <input type="text" id="customerName" required>
            </div>
            <div class="form-group">
                <label>Контактные данные *</label>
                <input type="text" id="contactInfo" required>
            </div>
            <div class="form-group">
                <label>Пластик</label>
                <input type="text" id="plastic" placeholder="PLA, ABS и т.д.">
            </div>
            <div class="form-group">
                <label>Ссылка на модель</label>
                <input type="text" id="modelLink" placeholder="https://...">
            </div>
            <div class="form-group">
                <label>Требования</label>
                <textarea id="requirements" rows="3"></textarea>
            </div>
            <button type="submit">📩 Отправить заявку</button>
        </form>
    </div>

    <script>
        const form = document.getElementById('orderForm');
        const successDiv = document.getElementById('successMsg');
        const errorDiv = document.getElementById('errorMsg');
        const loadingDiv = document.getElementById('loading');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Скрываем старые сообщения
            successDiv.style.display = 'none';
            errorDiv.style.display = 'none';
            
            // Собираем данные
            const formData = {
                modelName: document.getElementById('modelName').value,
                customerName: document.getElementById('customerName').value,
                contactInfo: document.getElementById('contactInfo').value,
                plastic: document.getElementById('plastic').value || 'Не указан',
                modelLink: document.getElementById('modelLink').value,
                requirements: document.getElementById('requirements').value
            };
            
            // Показываем загрузку
            loadingDiv.style.display = 'block';
            
            try {
                console.log('Отправка данных:', formData);
                
                const response = await fetch('/api/orders', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                console.log('Статус ответа:', response.status);
                
                // Получаем текст ответа
                const responseText = await response.text();
                console.log('Ответ сервера (текст):', responseText);
                
                // Пытаемся распарсить JSON
                let data;
                try {
                    data = JSON.parse(responseText);
                } catch (e) {
                    console.error('Ошибка парсинга JSON:', e);
                    throw new Error('Сервер вернул неверный ответ: ' + responseText);
                }
                
                if (response.ok && data.success) {
                    successDiv.textContent = '✅ Заявка успешно отправлена!';
                    successDiv.style.display = 'block';
                    form.reset();
                } else {
                    throw new Error(data.error || 'Ошибка при отправке');
                }
                
            } catch (error) {
                console.error('Ошибка:', error);
                errorDiv.textContent = '❌ ' + error.message;
                errorDiv.style.display = 'block';
            } finally {
                loadingDiv.style.display = 'none';
            }
        });
    </script>
</body>
</html>
    '''

# ============= API =============
@app.route('/api/orders', methods=['POST', 'OPTIONS'])
def create_order():
    """Создание заказа"""
    # Обработка preflight запроса
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Логируем запрос
        logger.info("=" * 50)
        logger.info("Получен POST запрос на /api/orders")
        logger.info(f"Content-Type: {request.headers.get('Content-Type')}")
        logger.info(f"Content-Length: {request.content_length}")
        
        # Получаем данные
        data = request.get_json()
        
        if not data:
            logger.error("Нет данных в запросе")
            return jsonify({'error': 'Нет данных'}), 400
        
        logger.info(f"Данные: {data}")
        
        # Валидация
        required = ['modelName', 'customerName', 'contactInfo']
        for field in required:
            if not data.get(field):
                logger.error(f"Поле {field} не заполнено")
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
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
        
        logger.info(f"✅ Заявка #{order_id} создана успешно!")
        
        # Возвращаем успешный ответ
        response = jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 201
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        logger.error(traceback.format_exc())
        
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

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
        response = jsonify(orders)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/api/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({
        'status': 'ok',
        'time': datetime.now().isoformat(),
        'db': os.path.exists(DB_PATH)
    })

# ============= АДМИН-ПАНЕЛЬ =============
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Вход в админ-панель</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .login-form {
            background: white;
            padding: 30px;
            border-radius: 10px;
            width: 300px;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            width: 100%;
            padding: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="login-form">
        <h2>Вход в админ-панель</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
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
        return render_template_string(LOGIN_PAGE, error='Неверные данные')
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
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Админ-панель</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .header { background: #333; color: white; padding: 10px 20px; margin-bottom: 20px; }
            table { width: 100%; background: white; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #667eea; color: white; }
            .status { padding: 3px 8px; border-radius: 4px; font-size: 12px; }
            .status-new { background: #3498db; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Админ-панель Kildear3D</h1>
            <a href="/admin/logout" style="color: white;">Выйти</a>
        </div>
        <div style="margin: 20px;">
            <h2>Всего заявок: ''' + str(len(orders)) + '''</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>Модель</th><th>Заказчик</th><th>Статус</th><th>Дата</th></tr>
                </thead>
                <tbody>
    '''
    
    for order in orders:
        html += f'''
                    <tr>
                        <td>{order['id']}</td>
                        <td>{order['model_name'][:50]}</td>
                        <td>{order['customer_name']}</td>
                        <td><span class="status status-{order['status']}">{order['status']}</span></td>
                        <td>{order['timestamp']}</td>
                    </tr>
        '''
    
    html += '''
                </tbody>
            </table>
        </div>
    </body>
    </html>
    '''
    
    return html

# ============= ЗАПУСК =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Сервер Kildear3D запущен!")
    print(f"🌐 Сайт: http://localhost:{port}/")
    print(f"📊 Админка: http://localhost:{port}/admin/login")
    print(f"🔑 Логин: {ADMIN_USERNAME}")
    print(f"🔐 Пароль: {ADMIN_PASSWORD}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=True)
