from flask import Flask, request, jsonify
import os
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    
    # Создаем таблицу для заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            service_type TEXT NOT NULL,
            order_details TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', methods=['GET'])
def get_services():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_dir, 'services-data.json')
        
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return jsonify(data), 200
        
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return jsonify([]), 500

@app.route('/create-order', methods=['POST', 'OPTIONS'])
def create_order():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Получаем данные из запроса
        order_data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['customer_name', 'customer_email', 'service_type', 'order_details']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Подключаемся к базе данных
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # Вставляем данные заказа
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_email, customer_phone, service_type, order_details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            order_data['customer_name'],
            order_data['customer_email'],
            order_data.get('customer_phone', ''),
            order_data['service_type'],
            json.dumps(order_data['order_details'], ensure_ascii=False)
        ))
        
        # Получаем ID созданного заказа
        order_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Order created successfully'
        }), 201
        
    except Exception as e:
        print(f"Ошибка при создании заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # Получаем все заказы
        cursor.execute('''
            SELECT id, customer_name, customer_email, customer_phone, service_type, 
                   order_details, order_date, status 
            FROM orders 
            ORDER BY order_date DESC
        ''')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'customer_phone': row[3],
                'service_type': row[4],
                'order_details': json.loads(row[5]),
                'order_date': row[6],
                'status': row[7]
            })
        
        conn.close()
        
        return jsonify(orders), 200
        
    except Exception as e:
        print(f"Ошибка при получении заказов: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, customer_name, customer_email, customer_phone, service_type, 
                   order_details, order_date, status 
            FROM orders 
            WHERE id = ?
        ''', (order_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            order = {
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'customer_phone': row[3],
                'service_type': row[4],
                'order_details': json.loads(row[5]),
                'order_date': row[6],
                'status': row[7]
            }
            return jsonify(order), 200
        else:
            return jsonify({'error': 'Order not found'}), 404
            
    except Exception as e:
        print(f"Ошибка при получении заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Инициализируем базу данных при запуске
    init_db()
    app.run(debug=True, host='0.0.0.0', port=10000)
