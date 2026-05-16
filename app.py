import os
import psycopg2
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kildear3d_secret_key_2025'
CORS(app)

# Данные для подключения к PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://kildear3d_user:21fjwc1a154A3cVndJoMunNSPU5JBrw7@dpg-d846ch8jsi32c739ktugv-a.singapore-postgres.render.com/kildear3d')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'kildear3d2025'

def get_db():
    """Подключение к БД"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return None

def init_db():
    """Создание таблицы"""
    conn = get_db()
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new'
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("✅ База данных готова")
        return True
    return False

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ============ ОСНОВНЫЕ МАРШРУТЫ ============

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Kildear3D - 3D печать</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #0a1928, #030c17);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
                background: rgba(20,35,55,0.95);
                padding: 30px;
                border-radius: 20px;
                border: 1px solid #ffb347;
            }
            h1 { color: #FFD966; text-align: center; margin-bottom: 20px; }
            input, select, textarea {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border-radius: 8px;
                border: 1px solid #3a5670;
                background: #0f1e2c;
                color: white;
                font-size: 14px;
            }
            button {
                width: 100%;
                padding: 14px;
                background: #ffb347;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 20px;
                font-size: 16px;
            }
            button:hover { background: #ff9f2e; }
            button:disabled { opacity: 0.7; cursor: not-allowed; }
            .checkbox {
                display: flex;
                align-items: center;
                gap: 10px;
                margin: 10px 0;
            }
            .checkbox input { width: auto; margin: 0; }
            .toast {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 8px;
                display: none;
                z-index: 1000;
            }
            .success { background: #27ae60; color: white; }
            .error { background: #e74c3c; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📝 Заказ 3D печати</h1>
            <form id="orderForm">
                <input type="text" id="modelName" placeholder="Название модели *" required>
                <input type="text" id="customerName" placeholder="Ваше имя *" required>
                <input type="text" id="contactInfo" placeholder="Telegram или телефон *" required>
                
                <select id="plastic">
                    <option>PLA белый</option>
                    <option>PLA черный</option>
                    <option>PLA красный</option>
                    <option>PLA зеленый</option>
                    <option>ABS желтый</option>
                </select>
                
                <input type="url" id="modelLink" placeholder="Ссылка на модель">
                <textarea id="requirements" rows="3" placeholder="Требования / описание"></textarea>
                
                <div class="checkbox">
                    <input type="checkbox" id="agreeData" required>
                    <label>Согласен на обработку персональных данных</label>
                </div>
                <div class="checkbox">
                    <input type="checkbox" id="agreeTerms" required>
                    <label>Принимаю условия заказа</label>
                </div>
                
                <button type="submit">📤 Отправить заявку</button>
            </form>
        </div>
        <div id="toast" class="toast"></div>

        <script>
            const form = document.getElementById('orderForm');
            const toast = document.getElementById('toast');
            
            function showToast(text, isError = false) {
                toast.textContent = text;
                toast.className = `toast ${isError ? 'error' : 'success'}`;
                toast.style.display = 'block';
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
            }
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (!document.getElementById('agreeData').checked) {
                    showToast('❌ Подтвердите согласие на обработку данных', true);
                    return;
                }
                if (!document.getElementById('agreeTerms').checked) {
                    showToast('❌ Примите условия заказа', true);
                    return;
                }
                
                const data = {
                    modelName: document.getElementById('modelName').value.trim(),
                    customerName: document.getElementById('customerName').value.trim(),
                    contactInfo: document.getElementById('contactInfo').value.trim(),
                    plastic: document.getElementById('plastic').value,
                    modelLink: document.getElementById('modelLink').value.trim(),
                    requirements: document.getElementById('requirements').value.trim()
                };
                
                if (!data.modelName || !data.customerName || !data.contactInfo) {
                    showToast('❌ Заполните все обязательные поля', true);
                    return;
                }
                
                const button = form.querySelector('button');
                const originalText = button.innerHTML;
                button.disabled = true;
                button.innerHTML = '⏳ Отправка...';
                
                try {
                    const response = await fetch('/api/orders', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showToast('✅ Заявка успешно отправлена! Я свяжусь с вами');
                        form.reset();
                    } else {
                        showToast('❌ ' + (result.error || 'Ошибка при отправке'), true);
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('❌ Ошибка соединения с сервером', true);
                } finally {
                    button.disabled = false;
                    button.innerHTML = originalText;
                }
            });
            
            // Проверка API
            fetch('/api/health')
                .then(res => res.json())
                .then(data => console.log('✅ API работает:', data))
                .catch(err => console.error('❌ API ошибка:', err));
        </script>
    </body>
    </html>
    '''

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400
        
        # Валидация
        if not data.get('modelName'):
            return jsonify({'success': False, 'error': 'Укажите название модели'}), 400
        if not data.get('customerName'):
            return jsonify({'success': False, 'error': 'Укажите ваше имя'}), 400
        if not data.get('contactInfo'):
            return jsonify({'success': False, 'error': 'Укажите контакты'}), 400
        
        # Сохраняем в БД
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'error': 'Ошибка подключения к БД'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO orders (model_name, customer_name, contact_info, plastic, model_link, requirements)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            data['modelName'],
            data['customerName'],
            data['contactInfo'],
            data.get('plastic', 'Не указан'),
            data.get('modelLink', ''),
            data.get('requirements', '')
        ))
        
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Заказ #{order_id} создан - {data['customerName']}")
        
        return jsonify({
            'success': True,
            'id': order_id,
            'message': 'Заявка создана'
        }), 201
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db()
        if not conn:
            return jsonify([]), 200
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
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
                'created_at': row[7],
                'status': row[8]
            })
        
        return jsonify(orders), 200
    except Exception as e:
        print(f"Ошибка: {e}")
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
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <form method="POST" style="max-width: 300px; margin: 0 auto;">
                <h2>Вход в админку</h2>
                <input name="username" placeholder="Логин" style="width:100%; padding:10px; margin:10px 0;">
                <input name="password" type="password" placeholder="Пароль" style="width:100%; padding:10px; margin:10px 0;">
                <button type="submit">Войти</button>
                <p style="color:red;">Неверные данные</p>
            </form>
        </body>
        </html>
        '''
    return '''
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <form method="POST" style="max-width: 300px; margin: 0 auto;">
            <h2>🔐 Вход в админку</h2>
            <input name="username" placeholder="Логин" style="width:100%; padding:10px; margin:10px 0;">
            <input name="password" type="password" placeholder="Пароль" style="width:100%; padding:10px; margin:10px 0;">
            <button type="submit">Войти</button>
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
        conn = get_db()
        if not conn:
            return "Ошибка подключения к БД", 500
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM orders ORDER BY id DESC')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Админ-панель Kildear3D</title>
            <style>
                body { font-family: Arial; background: #f5f5f5; margin: 0; padding: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
                table { width: 100%; background: white; border-collapse: collapse; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background: #34495e; color: white; }
                tr:hover { background: #f9f9f9; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                .status-new { background: #e74c3c; color: white; }
                .logout { background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                .stats { display: flex; gap: 20px; margin-bottom: 20px; }
                .stat { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Kildear3D Админ-панель</h1>
                <a href="/admin/logout" class="logout">🚪 Выход</a>
            </div>
            <div class="stats">
                <div class="stat"><strong>Всего заказов:</strong> ''' + str(len(rows)) + '''</div>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr><th>ID</th><th>Модель</th><th>Заказчик</th><th>Контакты</th><th>Пластик</th><th>Дата</th></tr>
                    </thead>
                    <tbody>
        '''
        
        for row in rows:
            html += f'''
                <tr>
                    <td>{row[0]}</td>
                    <td>{row[1][:50]}</td>
                    <td>{row[2]}</td>
                    <td>{row[3]}</td>
                    <td>{row[4]}</td>
                    <td>{row[7]}</td>
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
        
    except Exception as e:
        return f"Ошибка: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 Kildear3D сервер запущен!")
    print(f"🌐 Сайт: https://kildear3d.onrender.com")
    print(f"🔐 Админка: https://kildear3d.onrender.com/admin/login")
    print(f"📡 API: https://kildear3d.onrender.com/api/health")
    print(f"👤 Логин: {ADMIN_USERNAME}")
    print(f"🔑 Пароль: {ADMIN_PASSWORD}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
