from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kildear3d-secret-key-2025'

# Используем SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== МОДЕЛИ ====================

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    contact_info = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'customer_name': self.customer_name,
            'contact_info': self.contact_info,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# ==================== АУТЕНТИФИКАЦИЯ ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        print(f"Получен заказ: {data}")
        
        order = Order(
            model_name=data['modelName'],
            customer_name=data['customerName'],
            contact_info=data['contactInfo'],
            description=data.get('description', '')
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({'success': True, 'order_id': order.id})
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== АДМИН-ПАНЕЛЬ ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Неверный логин или пароль')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin.html')

@app.route('/api/admin/stats')
@login_required
def admin_stats():
    return jsonify({
        'total_orders': Order.query.count(),
        'new_orders': Order.query.filter_by(status='new').count(),
        'in_progress_orders': Order.query.filter_by(status='in_progress').count(),
        'completed_orders': Order.query.filter_by(status='completed').count(),
    })

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
    order.status = data.get('status')
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/orders/<int:order_id>', methods=['DELETE'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'success': True})

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password='admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Админ создан: admin / admin123")

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск Kildear3D")
    print("=" * 50)
    init_db()
    print("\n📌 http://localhost:5000")
    print("🔐 Админ: http://localhost:5000/admin (admin/admin123)")
    print("=" * 50)
    app.run(debug=True, port=5000)
