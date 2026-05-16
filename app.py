from flask import Flask, request, jsonify, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        print(f"Получен заказ: {data}")
        
        # Просто сохраняем в файл для теста
        import json
        with open('orders.txt', 'a', encoding='utf-8') as f:
            f.write(f"{data}\n")
        
        return jsonify({'success': True, 'message': 'Заказ получен'})
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)from flask import Flask, request, jsonify, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        print(f"Получен заказ: {data}")
        
        # Просто сохраняем в файл для теста
        import json
        with open('orders.txt', 'a', encoding='utf-8') as f:
            f.write(f"{data}\n")
        
        return jsonify({'success': True, 'message': 'Заказ получен'})
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
