import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import traceback

app = Flask(__name__)
app.secret_key = 'kildear3d_secret_key_2025'
app.config['JSON_AS_ASCII'] = False

# Включаем CORS для всех
CORS(app, resources={r"/*": {"origins": "*"}})

# Данные для подключения к PostgreSQL из вашего скриншота
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://kildear3d_user:2Tjwclw1l54A3cVndJoMunuNSPU5JBrw7adpg-d846ch8js32c739ktuvg-a/kildear3d')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'kildear3d2025'

def get_db_connection():
    """Получение соединения с PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return None

def init_db():
    """Создание таблицы если не существует"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
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
            print("✅ База данных PostgreSQL подключена и готова")
            return True
        else:
            print("❌ Не удалось подключиться к БД")
            return False
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

# Инициализируем БД
init_db()

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
    """Главная страница"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Kildear3D</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🚀 Kildear3D Сервер работает!</h1>
            <p>API доступен по адресу: <a href="/api/health">/api/health</a></p>
            <p>Админ-панель: <a href="/admin/login">/admin/login</a></p>
        </body>
        </html>
        """

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM orders')
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return jsonify({
                'status': 'ok',
                'database': 'connected',
                'orders_count': count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/orders', methods=['POST', 'OPTIONS'])
def create_order():
    """Создание заказа"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("=" * 50)
        print(f"📥 Получен POST запрос")
        
        # Получаем JSON данные
        data = request.get_json(silent=True)
        
        if not data:
            print("❌ Нет JSON данных")
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 200
        
        print(f"📦 Данные: {data}")
        
        # Валидация
        if not data.get('modelName'):
            return jsonify({'success': False, 'error': 'modelName is required'}), 200
        if not data.get('customerName'):
            return jsonify({'success': False, 'error': 'customerName is required'}), 200
        if not data.get('contactInfo'):
            return jsonify({'success': False, 'error': 'contactInfo is required'}), 200
        
        # Сохраняем в базу
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO orders 
            (model_name, customer_name, contact_info, plastic, model_link, requirements, timestamp, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            data['modelName'],
            data['customerName'],
            data['contactInfo'],
            data.get('plastic', 'PLA белый'),
            data.get('modelLink', ''),
            data.get('requirements', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new'
        ))
        
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Заказ #{order_id} успешно создан!")
        
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка успешно отправлена!'
        }), 201
        
    except Exception as e:
        print(f"❌ Ошибка: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получение списка заказов"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([]), 200
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM orders ORDER BY id DESC')
        orders = cur.fetchall()
        cur.close()
        conn.close()
        
        # Преобразуем для JSON
        result = []
        for order in orders:
            result.append({
                'id': order['id'],
                'model_name': order['model_name'],
                'customer_name': order['customer_name'],
                'contact_info': order['contact_info'],
                'plastic': order['plastic'],
                'model_link': order['model_link'],
                'requirements': order['requirements'],
                'timestamp': order['timestamp'],
                'status': order['status']
            })
        
        return jsonify(result), 200
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
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Вход</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <form method="POST" style="max-width: 300px; margin: 0 auto;">
                <h1>🔐 Вход в админку</h1>
                <input name="username" placeholder="Логин" style="width:100%; padding:10px; margin:10px 0;"><br>
                <input name="password" type="password" placeholder="Пароль" style="width:100%; padding:10px; margin:10px 0;"><br>
                <button type="submit" style="padding:10px 20px;">Войти</button>
                <p style="color:red;">Неверные данные</p>
            </form>
        </body>
        </html>
        '''
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Вход</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <form method="POST" style="max-width: 300px; margin: 0 auto;">
            <h1>🔐 Вход в админку Kildear3D</h1>
            <input name="username" placeholder="Логин" style="width:100%; padding:10px; margin:10px 0;"><br>
            <input name="password" type="password" placeholder="Пароль" style="width:100%; padding:10px; margin:10px 0;"><br>
            <button type="submit" style="padding:10px 20px; background: #ffb347; border: none; cursor: pointer;">Войти</button>
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
    """Админ-панель"""
    try:
        conn = get_db_connection()
        if not conn:
            return "Ошибка подключения к БД", 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM orders ORDER BY id DESC')
        orders = cur.fetchall()
        cur.close()
        conn.close()
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Админ-панель Kildear3D</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: Arial, sans-serif; background: #f5f5f5; }
                .header { background: #2c3e50; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
                .container { max-width: 1200px; margin: 20px auto; padding: 20px; background: white; border-radius: 10px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background: #34495e; color: white; }
                tr:hover { background: #f9f9f9; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                .status-new { background: #e74c3c; color: white; }
                .status-processing { background: #f39c12; color: white; }
                .status-completed { background: #27ae60; color: white; }
                .logout { background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                .stat { display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 5px; }
                .stat-number { font-size: 24px; font-weight: bold; color: #2c3e50; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Kildear3D Админ-панель</h1>
                <a href="/admin/logout" class="logout">🚪 Выход</a>
            </div>
            <div class="container">
                <div class="stat">
                    <div class="stat-number">''' + str(len(orders)) + '''</div>
                    <div>Всего заказов</div>
                </div>
                <div class="stat">
                    <div class="stat-number">''' + str(len([o for o in orders if o['status'] == 'new'])) + '''</div>
                    <div>Новых</div>
                </div>
                
                <h2 style="margin: 20px 0;">Список заказов</h2>
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
        return f"<h1>Ошибка</h1><pre>{traceback.format_exc()}</pre>", 500

# ============ ЗАПУСК ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Kildear3D Сервер запущен!")
    print(f"🌐 Сайт: https://kildear3d.onrender.com")
    print(f"🔐 Админка: https://kildear3d.onrender.com/admin/login")
    print(f"📡 API Health: https://kildear3d.onrender.com/api/health")
    print(f"👤 Логин: {ADMIN_USERNAME}")
    print(f"🔑 Пароль: {ADMIN_PASSWORD}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
