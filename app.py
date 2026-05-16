from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kildear3d-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost/kildear3d')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== МОДЕЛИ ====================

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    contact_info = db.Column(db.String(255), nullable=False)
    plastic = db.Column(db.String(100), nullable=False)
    model_link = db.Column(db.Text)
    requirements = db.Column(db.Text)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Plastic(db.Model):
    __tablename__ = 'plastics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    color_code = db.Column(db.String(20))
    price_per_gram = db.Column(db.Float, default=1.5)
    in_stock = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'color_code': self.color_code,
            'price_per_gram': self.price_per_gram,
            'in_stock': self.in_stock,
            'display_name': f"{self.name} {self.color}"
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

@app.route('/api/plastics', methods=['GET'])
def get_plastics():
    plastics = Plastic.query.filter_by(in_stock=True).all()
    return jsonify([p.to_dict() for p in plastics])

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
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
        
        return jsonify({'success': True, 'order_id': order.id})
    except Exception as e:
        db.session.rollback()
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
            session['admin_id'] = admin.id
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

# API для админ-панели
@app.route('/api/admin/stats')
@login_required
def admin_stats():
    return jsonify({
        'total_orders': Order.query.count(),
        'new_orders': Order.query.filter_by(status='new').count(),
        'in_progress_orders': Order.query.filter_by(status='in_progress').count(),
        'completed_orders': Order.query.filter_by(status='completed').count(),
        'total_plastics': Plastic.query.count()
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

@app.route('/api/admin/plastics', methods=['GET'])
@login_required
def admin_plastics():
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
    plastic.color_code = data.get('color_code')
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

# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создание администратора по умолчанию
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password='admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Администратор создан: admin / admin123")
        
        # Создание демо-пластиков
        if Plastic.query.count() == 0:
            demo = [
                Plastic(name='PLA', color='Белый', color_code='#FFFFFF', price_per_gram=1.5),
                Plastic(name='PLA', color='Черный', color_code='#000000', price_per_gram=1.5),
                Plastic(name='PLA', color='Красный', color_code='#FF4444', price_per_gram=1.5),
                Plastic(name='PLA', color='Зеленый', color_code='#44FF44', price_per_gram=1.5),
                Plastic(name='ABS', color='Желтый', color_code='#FFD700', price_per_gram=2.0),
            ]
            for p in demo:
                db.session.add(p)
            db.session.commit()
            print("✅ Демо-пластики созданы")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
