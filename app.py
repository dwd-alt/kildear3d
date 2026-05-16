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
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Настройка CORS для Render
CORS(app, origins=[
    'https://*.onrender.com',
    'http://localhost:5000',
    'http://127.0.0.1:5000'
], supports_credentials=True)

# Проверяем доступность директории /tmp
TMP_DIR = '/tmp'
DB_PATH = os.path.join(TMP_DIR, 'orders.db')

# Проверяем, можем ли мы писать в /tmp
try:
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR, exist_ok=True)
    # Тестовый файл
    test_file = os.path.join(TMP_DIR, 'test_write.txt')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    logger.info(f"✅ Директория {TMP_DIR} доступна для записи")
except Exception as e:
    logger.error(f"❌ Ошибка доступа к {TMP_DIR}: {e}")
    # Используем текущую директорию как fallback
    DB_PATH = 'orders.db'
    logger.info(f"⚠️ Используем локальную БД: {DB_PATH}")

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'kildear3d2025')


# Инициализация базы данных
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
        
        # Проверяем, существует ли таблица
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        if c.fetchone():
            logger.info("✅ Таблица orders существует")
            # Проверяем структуру таблицы
            c.execute("PRAGMA table_info(orders)")
            columns = [col[1] for col in c.fetchall()]
            logger.info(f"📊 Структура таблицы: {columns}")
        else:
            logger.error("❌ Таблица orders не создалась")
            
        conn.commit()
        conn.close()
        logger.info(f"✅ База данных инициализирована: {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        logger.error(traceback.format_exc())
        return False


# Инициализируем БД при старте
if not init_db():
    logger.error("⚠️ Не удалось инициализировать БД, но продолжаем работу")


# Декоратор для защиты админ-панели
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ============ ОСНОВНЫЕ МАРШРУТЫ ============

@app.route('/')
def index():
    try:
        # Пробуем разные пути для index.html
        possible_paths = ['index.html', 'templates/index.html', '../index.html']
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        # Если файл не найден, возвращаем встроенную форму
        return render_template_string('''
            <!DOCTYPE html>
            <html>
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
                    h1 { color: #333; margin-bottom: 10px; }
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
                    .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                    .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                    .hidden { display: none; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📦 Kildear3D</h1>
                    <div class="subtitle">3D печать на заказ</div>
                    
                    <div id="successMessage" class="success hidden"></div>
                    <div id="errorMessage" class="error hidden"></div>
                    
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
                            <label>Контактные данные (телефон/email) *</label>
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
                        
                        <button type="submit">📩 Отправить заявку</button>
                    </form>
                </div>
                
                <script>
                    document.getElementById('orderForm').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        
                        const formData = {
                            modelName: document.getElementById('modelName').value,
                            customerName: document.getElementById('customerName').value,
                            contactInfo: document.getElementById('contactInfo').value,
                            plastic: document.getElementById('plastic').value,
                            modelLink: document.getElementById('modelLink').value,
                            requirements: document.getElementById('requirements').value
                        };
                        
                        const successDiv = document.getElementById('successMessage');
                        const errorDiv = document.getElementById('errorMessage');
                        
                        successDiv.classList.add('hidden');
                        errorDiv.classList.add('hidden');
                        
                        try {
                            const response = await fetch('/api/orders', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(formData)
                            });
                            
                            const data = await response.json();
                            
                            if (response.ok && data.success) {
                                successDiv.textContent = '✅ Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.';
                                successDiv.classList.remove('hidden');
                                document.getElementById('orderForm').reset();
                            } else {
                                throw new Error(data.error || 'Ошибка при отправке');
                            }
                        } catch (error) {
                            errorDiv.textContent = '❌ Ошибка: ' + error.message + '. Пожалуйста, попробуйте позже.';
                            errorDiv.classList.remove('hidden');
                        }
                    });
                </script>
            </body>
            </html>
        ''')
    except Exception as e:
        logger.error(f"Ошибка загрузки index.html: {e}")
        return f"Ошибка сервера: {str(e)}", 500


# ============ API ДЛЯ ЗАЯВОК ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        # Проверяем БД
        db_ok = False
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM orders")
            count = c.fetchone()[0]
            conn.close()
            db_ok = True
        
        return jsonify({
            'status': 'ok',
            'time': datetime.now().isoformat(),
            'database_exists': os.path.exists(DB_PATH),
            'database_accessible': db_ok,
            'orders_count': count if db_ok else 0
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание нового заказа"""
    try:
        # Проверяем Content-Type
        if not request.is_json:
            logger.warning("Не JSON запрос")
            return jsonify({'error': 'Content-Type должен быть application/json'}), 415

        data = request.get_json(silent=True)
        if not data:
            logger.warning("Пустые данные")
            return jsonify({'error': 'Пустые данные'}), 400

        logger.info(f"Получены данные: {data}")

        # Проверяем обязательные поля
        required_fields = ['modelName', 'customerName', 'contactInfo']
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({'error': f'Поле {field} обязательно для заполнения'}), 400

        # Подготавливаем данные
        model_name = str(data['modelName']).strip()
        customer_name = str(data['customerName']).strip()
        contact_info = str(data['contactInfo']).strip()
        plastic = str(data.get('plastic', 'Не указан')).strip()
        model_link = str(data.get('modelLink', '')).strip()
        requirements = str(data.get('requirements', '')).strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"Сохраняем заявку: {model_name}, {customer_name}")

        # Сохраняем в базу
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, 'new'))
        
        conn.commit()
        order_id = c.lastrowid
        conn.close()

        logger.info(f"✅ Заявка #{order_id} успешно создана!")
        
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно создана'
        }), 201

    except sqlite3.Error as e:
        logger.error(f"Ошибка БД: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Ошибка базы данных. Пожалуйста, попробуйте позже.'}), 500
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получение списка заказов"""
    try:
        if not os.path.exists(DB_PATH):
            return jsonify({'error': 'База данных не инициализирована'}), 500
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()

        orders = [dict(row) for row in rows]
        return jsonify(orders), 200
    except Exception as e:
        logger.error(f"Ошибка получения заказов: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


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
        input:focus { outline: none; border-color: #667eea; }
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
        .header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .header h1 { color: #FFD966; }
        .logout-btn { background: #e74c3c; padding: 10px 20px; border-radius: 8px; text-decoration: none; color: white; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
        .stat-card { background: white; border-radius: 16px; padding: 20px; flex: 1; min-width: 150px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 4px solid #FFB347; }
        .stat-number { font-size: 32px; font-weight: bold; color: #FFB347; }
        .orders-table { background: white; border-radius: 16px; overflow-x: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #34495e; color: white; }
        tr:hover { background: #f9f9f9; }
        .status { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; }
        .status-new { background: #3498db; color: white; }
        .status-processing { background: #f39c12; color: white; }
        .status-completed { background: #27ae60; color: white; }
        .status-cancelled { background: #e74c3c; color: white; }
        .view-btn { background: #FFB347; color: #1e2a2f; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; }
        .view-btn:hover { background: #ff9f2e; }
        .refresh-btn { background: #3498db; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; margin-left: 10px; }
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
            <div class="stat-card"><div class="stat-number">{{ orders|length if orders else 0 }}</div><div>Всего заявок</div></div>
            <div class="stat-card"><div class="stat-number">{{ orders|selectattr('status', 'equalto', 'new')|list|length if orders else 0 }}</div><div>Новые</div></div>
        </div>
        <div class="orders-table">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Модель</th>
                        <th>Заказчик</th>
                        <th>Связь</th>
                        <th>Пластик</th>
                        <th>Статус</th>
                        <th>Дата</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {% if orders %}
                        {% for order in orders %}
                        <tr>
                            <td>{{ order.id }}</td>
                            <td>{{ order.model_name[:40] }}{% if order.model_name|length > 40 %}...{% endif %}</td>
                            <td>{{ order.customer_name }}</td>
                            <td>{{ order.contact_info }}</td>
                            <td>{{ order.plastic }}</td>
                            <td><span class="status status-{{ order.status }}">{% if order.status == 'new' %}🆕 Новая{% elif order.status == 'processing' %}⚙️ В работе{% elif order.status == 'completed' %}✅ Завершена{% else %}❌ Отменена{% endif %}</span></td>
                            <td>{{ order.timestamp[:16] if order.timestamp else '' }}</td>
                            <td><a href="/admin/order/{{ order.id }}" class="view-btn">🔍 Подробнее</a></td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="8" style="text-align: center; padding: 40px;">📭 Пока нет заявок</td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''

ORDER_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Заявка #{{ order.id }} - Kildear3D</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 24px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 20px; }
        .back-btn { background: #95a5a6; padding: 10px 20px; border-radius: 8px; text-decoration: none; color: white; display: inline-block; margin-bottom: 20px; }
        .info-block { background: #f9f9f9; border-radius: 16px; padding: 20px; margin-bottom: 20px; }
        .info-label { font-weight: bold; color: #555; margin-bottom: 5px; }
        .info-value { margin-bottom: 15px; word-wrap: break-word; color: #333; }
        .status-select { padding: 10px; border-radius: 8px; border: 1px solid #ddd; margin-top: 10px; width: 200px; font-size: 14px; }
        pre { background: #eee; padding: 15px; border-radius: 12px; overflow-x: auto; white-space: pre-wrap; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin" class="back-btn">← Назад к заявкам</a>
        <h1>📄 Заявка #{{ order.id }}</h1>
        <div class="info-block">
            <div class="info-label">📦 Название модели</div>
            <div class="info-value">{{ order.model_name }}</div>
            <div class="info-label">👤 Заказчик</div>
            <div class="info-value">{{ order.customer_name }}</div>
            <div class="info-label">📞 Связь</div>
            <div class="info-value">{{ order.contact_info }}</div>
            <div class="info-label">🎨 Пластик/цвет</div>
            <div class="info-value">{{ order.plastic }}</div>
            <div class="info-label">📅 Дата заявки</div>
            <div class="info-value">{{ order.timestamp }}</div>
            <div class="info-label">📊 Статус</div>
            <div class="info-value">
                <select id="statusSelect" class="status-select" data-id="{{ order.id }}">
                    <option value="new" {% if order.status == 'new' %}selected{% endif %}>🆕 Новая</option>
                    <option value="processing" {% if order.status == 'processing' %}selected{% endif %}>⚙️ В работе</option>
                    <option value="completed" {% if order.status == 'completed' %}selected{% endif %}>✅ Завершена</option>
                    <option value="cancelled" {% if order.status == 'cancelled' %}selected{% endif %}>❌ Отменена</option>
                </select>
            </div>
        </div>
        {% if order.model_link %}
        <div class="info-block">
            <div class="info-label">🔗 Ссылка на модель</div>
            <div class="info-value"><a href="{{ order.model_link }}" target="_blank" style="color:#FFB347;">{{ order.model_link }}</a></div>
        </div>
        {% endif %}
        {% if order.requirements %}
        <div class="info-block">
            <div class="info-label">📝 Требования / Описание</div>
            <div class="info-value"><pre>{{ order.requirements }}</pre></div>
        </div>
        {% endif %}
    </div>
    <script>
        document.getElementById('statusSelect')?.addEventListener('change', async function() {
            try {
                const response = await fetch(`/admin/order/${this.dataset.id}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: this.value })
                });
                if(response.ok) {
                    alert('✅ Статус обновлён!');
                } else {
                    const error = await response.json();
                    alert('❌ Ошибка: ' + (error.error || 'Неизвестная ошибка'));
                }
            } catch(e) {
                alert('❌ Ошибка соединения');
            }
        });
    </script>
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
            session.permanent = True
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
    try:
        if not os.path.exists(DB_PATH):
            return "❌ База данных не инициализирована. Пожалуйста, проверьте права доступа.", 500
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT id, model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status FROM orders ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()

        orders = [dict(row) for row in rows]
        return render_template_string(ADMIN_PAGE, orders=orders)
    except Exception as e:
        logger.error(f"Ошибка в админ-панели: {e}")
        logger.error(traceback.format_exc())
        return f"Ошибка: {e}", 500


@app.route('/admin/order/<int:order_id>')
@login_required
def view_order(order_id):
    try:
        if not os.path.exists(DB_PATH):
            return "❌ База данных не инициализирована", 500
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return "Заявка не найдена", 404
        order = dict(row)
        return render_template_string(ORDER_PAGE, order=order)
    except Exception as e:
        logger.error(f"Ошибка просмотра заказа: {e}")
        return f"Ошибка: {e}", 500


@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
            
        status = data.get('status')
        if status not in ['new', 'processing', 'completed', 'cancelled']:
            return jsonify({'error': 'Неверный статус'}), 400
            
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Статус обновлен'})
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {e}")
        return jsonify({'error': str(e)}), 500


# ============ ЗАПУСК ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(f"🚀 Сервер Kildear3D запущен!")
    print(f"🌐 САЙТ: http://localhost:{port}/")
    print(f"📊 АДМИН-ПАНЕЛЬ: http://localhost:{port}/admin/login")
    print(f"🔑 Логин: {ADMIN_USERNAME}")
    print(f"🔐 Пароль: {ADMIN_PASSWORD}")
    print(f"💾 БАЗА ДАННЫХ: {DB_PATH}")
    print("=" * 50)
    
    # Запускаем с debug=False для продакшена
    app.run(host='0.0.0.0', port=port, debug=False)
