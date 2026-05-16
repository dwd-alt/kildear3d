import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kildear3d_secret_key_2025'
CORS(app)

DB_PATH = 'orders.db'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'kildear3d2025'


# Инициализация базы данных
def init_db():
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
    print("✅ База данных инициализирована")


init_db()


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
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "Файл index.html не найден", 404


# ============ API ДЛЯ ЗАЯВОК ============

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        print("Получены данные:", data)

        # Проверяем обязательные поля
        if not data.get('modelName'):
            return jsonify({'error': 'Укажите название модели'}), 400
        if not data.get('customerName'):
            return jsonify({'error': 'Укажите ваше имя'}), 400
        if not data.get('contactInfo'):
            return jsonify({'error': 'Укажите контактные данные'}), 400

        # Сохраняем в базу
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

        print(f"✅ Заявка #{order_id} успешно создана!")
        return jsonify({'success': True, 'id': order_id}), 201

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM orders ORDER BY id DESC')
    orders = c.fetchall()
    conn.close()

    result = []
    for order in orders:
        result.append({
            'id': order[0],
            'model_name': order[1],
            'customer_name': order[2],
            'contact_info': order[3],
            'plastic': order[4],
            'model_link': order[5],
            'requirements': order[6],
            'timestamp': order[7],
            'status': order[8]
        })
    return jsonify(result)


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
        .header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
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
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Kildear3D — Админ-панель</h1>
        <a href="/admin/logout" class="logout-btn">🚪 Выход</a>
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
                            <td colspan="8" style="text-align: center;">Нет заявок</td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
    <script>setInterval(() => location.reload(), 30000);</script>
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
            const response = await fetch(`/admin/order/${this.dataset.id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: this.value })
            });
            if(response.ok) {
                alert('✅ Статус обновлён!');
            } else {
                alert('❌ Ошибка при обновлении');
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
    conn.row_factory = sqlite3.Row  # Важно! Позволяет обращаться по именам колонок
    c = conn.cursor()
    c.execute(
        'SELECT id, model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status FROM orders ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()

    # Преобразуем Row в словари для удобства в шаблоне
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
    order = dict(row)
    return render_template_string(ORDER_PAGE, order=order)


@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    status = request.json.get('status')
    if status not in ['new', 'processing', 'completed', 'cancelled']:
        return jsonify({'error': 'Неверный статус'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ============ ЗАПУСК ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(f"🚀 Сервер Kildear3D запущен!")
    print(f"🌐 САЙТ: http://localhost:{port}/")
    print(f"📊 АДМИН-ПАНЕЛЬ: http://localhost:{port}/admin/login")
    print(f"🔑 Логин: {ADMIN_USERNAME}")
    print(f"🔐 Пароль: {ADMIN_PASSWORD}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=port)