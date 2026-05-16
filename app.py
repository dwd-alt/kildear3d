from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import re
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/kildear3d')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ==================== МОДЕЛИ БАЗЫ ДАННЫХ ====================

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    contact_info = db.Column(db.String(255), nullable=False)
    plastic = db.Column(db.String(100), nullable=False)
    model_link = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='new')  # new, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'customer_name': self.customer_name,
            'contact_info': self.contact_info,
            'plastic': self.plastic,
            'model_link': self.model_link,
            'requirements': self.requirements,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Plastic(db.Model):
    __tablename__ = 'plastics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # PLA, ABS, PETG и т.д.
    color = db.Column(db.String(50), nullable=False)  # Белый, Черный, Красный
    color_code = db.Column(db.String(20), nullable=True)  # #FFFFFF для отображения
    icon = db.Column(db.String(50), default='fas fa-palette')
    price_per_gram = db.Column(db.Float, default=1.5)
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'color_code': self.color_code,
            'icon': self.icon,
            'price_per_gram': self.price_per_gram,
            'in_stock': self.in_stock,
            'display_name': f"{self.name} {self.color}"
        }


class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== АУТЕНТИФИКАЦИЯ ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== API ЭНДПОИНТЫ ДЛЯ ФРОНТЕНДА ====================

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание нового заказа с фронтенда"""
    try:
        data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['modelName', 'customerName', 'contactInfo', 'plastic']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        order = Order(
            model_name=data['modelName'],
            customer_name=data['customerName'],
            contact_info=data['contactInfo'],
            plastic=data['plastic'],
            model_link=data.get('modelLink'),
            requirements=data.get('requirements')
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'message': 'Заявка успешно создана'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== АДМИН-ПАНЕЛЬ (HTML) ====================

ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в админ-панель Kildear3D</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0a1928, #030c17);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: rgba(20, 35, 55, 0.95);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 32px;
            width: 100%;
            max-width: 400px;
            border: 1px solid #ffb34760;
        }
        h2 {
            color: #FFD966;
            margin-bottom: 30px;
            text-align: center;
        }
        input {
            width: 100%;
            padding: 14px 18px;
            margin-bottom: 20px;
            border-radius: 28px;
            border: 1.5px solid #3a5670;
            background: #0f1e2c;
            color: #fff3e0;
            font-family: 'Inter', sans-serif;
            font-size: 16px;
        }
        input:focus {
            border-color: #FFB347;
            outline: none;
        }
        button {
            width: 100%;
            background: linear-gradient(95deg, #F6A800, #FF8C42);
            border: none;
            color: #1e2a2f;
            font-weight: 800;
            padding: 14px;
            border-radius: 44px;
            cursor: pointer;
            font-size: 1.1rem;
        }
        button:hover {
            transform: scale(0.98);
        }
        .error {
            color: #ff6b6b;
            text-align: center;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>🔐 Вход в админ-панель</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админ-панель Kildear3D</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0e1a;
            color: #eef4ff;
        }
        .sidebar {
            width: 260px;
            background: #0f172a;
            position: fixed;
            height: 100vh;
            padding: 20px;
            border-right: 1px solid #ffb34740;
        }
        .sidebar h3 {
            color: #FFD966;
            margin-bottom: 30px;
            font-size: 1.3rem;
        }
        .sidebar nav a {
            display: block;
            padding: 12px 16px;
            color: #cbd5e1;
            text-decoration: none;
            border-radius: 12px;
            margin-bottom: 8px;
            transition: 0.2s;
        }
        .sidebar nav a:hover, .sidebar nav a.active {
            background: #ffb34720;
            color: #FFB347;
        }
        .sidebar nav a i {
            margin-right: 12px;
            width: 24px;
        }
        .logout-btn {
            position: absolute;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: #dc2626;
            text-align: center;
            padding: 12px;
            border-radius: 12px;
            color: white;
            text-decoration: none;
        }
        .main-content {
            margin-left: 260px;
            padding: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1e293b;
            border-radius: 20px;
            padding: 20px;
            border: 1px solid #ffb34740;
        }
        .stat-card h3 {
            font-size: 0.9rem;
            color: #94a3b8;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #FFD966;
        }
        .orders-table, .plastics-table {
            background: #1e293b;
            border-radius: 20px;
            padding: 20px;
            overflow-x: auto;
            margin-bottom: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            color: #FFB347;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-new { background: #3b82f6; }
        .status-in_progress { background: #eab308; }
        .status-completed { background: #22c55e; }
        .status-cancelled { background: #ef4444; }
        button {
            background: #ffb347;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            cursor: pointer;
            margin: 2px;
        }
        button.danger { background: #dc2626; color: white; }
        button.warning { background: #eab308; }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-content {
            background: #1e293b;
            border-radius: 24px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
        }
        .modal-content input, .modal-content select {
            width: 100%;
            padding: 12px;
            margin-bottom: 15px;
            border-radius: 12px;
            border: 1px solid #ffb347;
            background: #0f172a;
            color: white;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab-btn {
            background: #334155;
            padding: 10px 20px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
        }
        .tab-btn.active {
            background: #FFB347;
            color: #1e293b;
        }
        .tab-pane {
            display: none;
        }
        .tab-pane.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3><i class="fas fa-cube"></i> Kildear3D Admin</h3>
        <nav>
            <a href="#" onclick="showTab('orders')" class="active" id="tab-orders-btn"><i class="fas fa-shopping-cart"></i> Заказы</a>
            <a href="#" onclick="showTab('plastics')" id="tab-plastics-btn"><i class="fas fa-palette"></i> Пластики</a>
        </nav>
        <a href="/admin/logout" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Выйти</a>
    </div>
    
    <div class="main-content">
        <div class="stats-grid" id="stats-grid"></div>
        
        <div id="tab-orders" class="tab-pane active">
            <div class="orders-table">
                <h2><i class="fas fa-shopping-cart"></i> Заказы</h2>
                <table id="orders-table">
                    <thead>
                        <tr><th>ID</th><th>Модель</th><th>Клиент</th><th>Контакты</th><th>Пластик</th><th>Статус</th><th>Дата</th><th>Действия</th></tr>
                    </thead>
                    <tbody id="orders-tbody"></tbody>
                </table>
            </div>
        </div>
        
        <div id="tab-plastics" class="tab-pane">
            <div class="plastics-table">
                <h2><i class="fas fa-palette"></i> Пластики <button onclick="openPlasticModal()" style="background:#22c55e; margin-left:10px;"><i class="fas fa-plus"></i> Добавить</button></h2>
                <table>
                    <thead><tr><th>ID</th><th>Название</th><th>Цвет</th><th>Цена/гр</th><th>В наличии</th><th>Действия</th></tr></thead>
                    <tbody id="plastics-tbody"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <!-- Модальное окно для пластика -->
    <div id="plasticModal" class="modal">
        <div class="modal-content">
            <h3 id="plasticModalTitle">Добавить пластик</h3>
            <input type="hidden" id="plasticId">
            <input type="text" id="plasticName" placeholder="Название (PLA, ABS...)" required>
            <input type="text" id="plasticColor" placeholder="Цвет (Белый, Черный...)" required>
            <input type="text" id="plasticColorCode" placeholder="HEX код цвета (опционально)">
            <input type="number" id="plasticPrice" step="0.1" placeholder="Цена за грамм (₽)" required>
            <select id="plasticStock">
                <option value="true">В наличии</option>
                <option value="false">Нет в наличии</option>
            </select>
            <button onclick="savePlastic()">Сохранить</button>
            <button onclick="closePlasticModal()" style="background:#6b7280;">Отмена</button>
        </div>
    </div>
    
    <script>
        let currentTab = 'orders';
        
        function showTab(tab) {
            currentTab = tab;
            document.getElementById('tab-orders').classList.toggle('active', tab === 'orders');
            document.getElementById('tab-plastics').classList.toggle('active', tab === 'plastics');
            document.getElementById('tab-orders-btn').classList.toggle('active', tab === 'orders');
            document.getElementById('tab-plastics-btn').classList.toggle('active', tab === 'plastics');
            if (tab === 'orders') loadOrders();
            if (tab === 'plastics') loadPlastics();
        }
        
        function loadStats() {
            fetch('/api/admin/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('stats-grid').innerHTML = `
                        <div class="stat-card"><h3>Всего заказов</h3><div class="value">${data.total_orders}</div></div>
                        <div class="stat-card"><h3>Новых</h3><div class="value">${data.new_orders}</div></div>
                        <div class="stat-card"><h3>В работе</h3><div class="value">${data.in_progress_orders}</div></div>
                        <div class="stat-card"><h3>Завершено</h3><div class="value">${data.completed_orders}</div></div>
                        <div class="stat-card"><h3>Всего пластиков</h3><div class="value">${data.total_plastics}</div></div>
                    `;
                });
        }
        
        function loadOrders() {
            fetch('/api/admin/orders')
                .then(r => r.json())
                .then(orders => {
                    const tbody = document.getElementById('orders-tbody');
                    tbody.innerHTML = orders.map(order => `
                        <tr>
                            <td>${order.id}</td>
                            <td>${escapeHtml(order.model_name)}</td>
                            <td>${escapeHtml(order.customer_name)}</td>
                            <td>${escapeHtml(order.contact_info)}</td>
                            <td>${escapeHtml(order.plastic)}</td>
                            <td>
                                <select onchange="updateOrderStatus(${order.id}, this.value)" class="status-badge status-${order.status}">
                                    <option value="new" ${order.status === 'new' ? 'selected' : ''}>🆕 Новый</option>
                                    <option value="in_progress" ${order.status === 'in_progress' ? 'selected' : ''}>⚙️ В работе</option>
                                    <option value="completed" ${order.status === 'completed' ? 'selected' : ''}>✅ Завершен</option>
                                    <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>❌ Отменен</option>
                                </select>
                            </td>
                            <td>${new Date(order.created_at).toLocaleDateString()}</td>
                            <td>
                                <button onclick="viewOrder(${order.id})"><i class="fas fa-eye"></i></button>
                                <button class="danger" onclick="deleteOrder(${order.id})"><i class="fas fa-trash"></i></button>
                            </td>
                        </tr>
                    `).join('');
                });
        }
        
        function loadPlastics() {
            fetch('/api/admin/plastics')
                .then(r => r.json())
                .then(plastics => {
                    const tbody = document.getElementById('plastics-tbody');
                    tbody.innerHTML = plastics.map(p => `
                        <tr>
                            <td>${p.id}</td>
                            <td>${escapeHtml(p.name)}</td>
                            <td><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:${p.color_code || '#ccc'};margin-right:8px;"></span>${escapeHtml(p.color)}</td>
                            <td>${p.price_per_gram} ₽</td>
                            <td>${p.in_stock ? '✅ Да' : '❌ Нет'}</td>
                            <td>
                                <button onclick="editPlastic(${p.id})"><i class="fas fa-edit"></i></button>
                                <button class="danger" onclick="deletePlastic(${p.id})"><i class="fas fa-trash"></i></button>
                            </td>
                        </tr>
                    `).join('');
                });
        }
        
        function updateOrderStatus(id, status) {
            fetch(`/api/admin/orders/${id}/status`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(() => { loadOrders(); loadStats(); });
        }
        
        function deleteOrder(id) {
            if(confirm('Удалить заказ?')) {
                fetch(`/api/admin/orders/${id}`, {method: 'DELETE'})
                    .then(() => { loadOrders(); loadStats(); });
            }
        }
        
        function openPlasticModal(plastic = null) {
            document.getElementById('plasticModal').style.display = 'flex';
            if(plastic) {
                document.getElementById('plasticModalTitle').innerText = 'Редактировать пластик';
                document.getElementById('plasticId').value = plastic.id;
                document.getElementById('plasticName').value = plastic.name;
                document.getElementById('plasticColor').value = plastic.color;
                document.getElementById('plasticColorCode').value = plastic.color_code || '';
                document.getElementById('plasticPrice').value = plastic.price_per_gram;
                document.getElementById('plasticStock').value = plastic.in_stock;
            } else {
                document.getElementById('plasticModalTitle').innerText = 'Добавить пластик';
                document.getElementById('plasticId').value = '';
                document.getElementById('plasticName').value = '';
                document.getElementById('plasticColor').value = '';
                document.getElementById('plasticColorCode').value = '';
                document.getElementById('plasticPrice').value = '';
                document.getElementById('plasticStock').value = 'true';
            }
        }
        
        function closePlasticModal() {
            document.getElementById('plasticModal').style.display = 'none';
        }
        
        function savePlastic() {
            const id = document.getElementById('plasticId').value;
            const data = {
                name: document.getElementById('plasticName').value,
                color: document.getElementById('plasticColor').value,
                color_code: document.getElementById('plasticColorCode').value,
                price_per_gram: parseFloat(document.getElementById('plasticPrice').value),
                in_stock: document.getElementById('plasticStock').value === 'true'
            };
            
            const url = id ? `/api/admin/plastics/${id}` : '/api/admin/plastics';
            const method = id ? 'PUT' : 'POST';
            
            fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(() => {
                closePlasticModal();
                loadPlastics();
                loadStats();
            });
        }
        
        function editPlastic(id) {
            fetch('/api/admin/plastics')
                .then(r => r.json())
                .then(plastics => {
                    const plastic = plastics.find(p => p.id === id);
                    if(plastic) openPlasticModal(plastic);
                });
        }
        
        function deletePlastic(id) {
            if(confirm('Удалить пластик?')) {
                fetch(`/api/admin/plastics/${id}`, {method: 'DELETE'})
                    .then(() => { loadPlastics(); loadStats(); });
            }
        }
        
        function viewOrder(id) {
            fetch('/api/admin/orders')
                .then(r => r.json())
                .then(orders => {
                    const order = orders.find(o => o.id === id);
                    if(order) {
                        alert(`Заказ #${order.id}\\nМодель: ${order.model_name}\\nКлиент: ${order.customer_name}\\nКонтакты: ${order.contact_info}\\nТребования: ${order.requirements || '-'}`);
                    }
                });
        }
        
        function escapeHtml(text) {
            if(!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        loadStats();
        loadOrders();
        
        setInterval(() => {
            if(currentTab === 'orders') loadOrders();
            loadStats();
        }, 30000);
    </script>
</body>
</html>
'''


# ==================== АДМИН-ПАНЕЛЬ (API И РОУТЫ) ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Для простоты — проверка по умолчанию (измените пароль!)
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error='Неверный логин или пароль')
    
    return render_template_string(ADMIN_LOGIN_TEMPLATE)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE)


# API для админ-панели
@app.route('/api/admin/stats')
@login_required
def admin_stats():
    stats = {
        'total_orders': Order.query.count(),
        'new_orders': Order.query.filter_by(status='new').count(),
        'in_progress_orders': Order.query.filter_by(status='in_progress').count(),
        'completed_orders': Order.query.filter_by(status='completed').count(),
        'cancelled_orders': Order.query.filter_by(status='cancelled').count(),
        'total_plastics': Plastic.query.count()
    }
    return jsonify(stats)


@app.route('/api/admin/orders')
@login_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def update_order_status(order_id):
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    order.status = data.get('status', order.status)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/admin/orders/<int:order_id>', methods=['DELETE'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'success': True})


# CRUD для пластиков
@app.route('/api/admin/plastics', methods=['GET'])
@login_required
def get_plastics():
    plastics = Plastic.query.all()
    return jsonify([p.to_dict() for p in plastics])


@app.route('/api/admin/plastics', methods=['POST'])
@login_required
def create_plastic():
    data = request.get_json()
    plastic = Plastic(
        name=data['name'],
        color=data['color'],
        color_code=data.get('color_code'),
        price_per_gram=data.get('price_per_gram', 1.5),
        in_stock=data.get('in_stock', True)
    )
    db.session.add(plastic)
    db.session.commit()
    return jsonify(plastic.to_dict()), 201


@app.route('/api/admin/plastics/<int:plastic_id>', methods=['PUT'])
@login_required
def update_plastic(plastic_id):
    plastic = Plastic.query.get_or_404(plastic_id)
    data = request.get_json()
    plastic.name = data.get('name', plastic.name)
    plastic.color = data.get('color', plastic.color)
    plastic.color_code = data.get('color_code', plastic.color_code)
    plastic.price_per_gram = data.get('price_per_gram', plastic.price_per_gram)
    plastic.in_stock = data.get('in_stock', plastic.in_stock)
    db.session.commit()
    return jsonify(plastic.to_dict())


@app.route('/api/admin/plastics/<int:plastic_id>', methods=['DELETE'])
@login_required
def delete_plastic(plastic_id):
    plastic = Plastic.query.get_or_404(plastic_id)
    db.session.delete(plastic)
    db.session.commit()
    return jsonify({'success': True})


# Публичный API для получения списка пластиков (для фронтенда)
@app.route('/api/plastics', methods=['GET'])
def get_public_plastics():
    plastics = Plastic.query.filter_by(in_stock=True).all()
    return jsonify([p.to_dict() for p in plastics])


# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создание тестового администратора, если нет
        if not Admin.query.filter_by(username='admin').first():
            # В реальном проекте используйте хеширование паролей!
            admin = Admin(username='admin', password_hash='admin123')
            db.session.add(admin)
            db.session.commit()
            print("Создан тестовый администратор: admin / admin123")
        
        # Создание демо-пластиков, если их нет
        if Plastic.query.count() == 0:
            demo_plastics = [
                Plastic(name='PLA', color='Белый', color_code='#FFFFFF', price_per_gram=1.5),
                Plastic(name='PLA', color='Черный', color_code='#000000', price_per_gram=1.5),
                Plastic(name='PLA', color='Красный', color_code='#FF4444', price_per_gram=1.5),
                Plastic(name='PLA', color='Зеленый', color_code='#44FF44', price_per_gram=1.5),
                Plastic(name='ABS', color='Желтый', color_code='#FFD700', price_per_gram=2.0),
            ]
            for p in demo_plastics:
                db.session.add(p)
            db.session.commit()
            print("Созданы демо-пластики")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
