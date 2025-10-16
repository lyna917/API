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
    
    # Обновляем структуру таблицы для нового формата
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            customer_address TEXT,
            delivery_time TEXT,
            comments TEXT,
            total_services INTEGER NOT NULL,
            total_price TEXT NOT NULL,
            order_details TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для отдельных услуг в заказе
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            service_id TEXT NOT NULL,
            service_name TEXT NOT NULL,
            service_price TEXT NOT NULL,
            service_description TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
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
        required_fields = ['name', 'email', 'total_services', 'total_price']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Подключаемся к базе данных
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # Вставляем основные данные заказа
        cursor.execute('''
            INSERT INTO orders (
                customer_name, customer_email, customer_phone, customer_address,
                delivery_time, comments, total_services, total_price, order_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data['name'],
            order_data['email'],
            order_data.get('phone', ''),
            order_data.get('address', ''),
            order_data.get('delivery_time', ''),
            order_data.get('comments', ''),
            int(order_data['total_services']),
            order_data['total_price'],
            json.dumps(order_data, ensure_ascii=False)  # Сохраняем весь JSON для резервной копии
        ))
        
        # Получаем ID созданного заказа
        order_id = cursor.lastrowid
        
        # Добавляем услуги в отдельную таблицу
        total_services = int(order_data['total_services'])
        for i in range(total_services):
            service_prefix = f'service_{i}_'
            service_id = order_data.get(f'{service_prefix}id')
            service_name = order_data.get(f'{service_prefix}name')
            service_price = order_data.get(f'{service_prefix}price')
            service_description = order_data.get(f'{service_prefix}description', '')
            
            if service_id and service_name and service_price:
                cursor.execute('''
                    INSERT INTO order_services (order_id, service_id, service_name, service_price, service_description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, service_id, service_name, service_price, service_description))
        
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
        
        # Получаем все заказы с услугами
        cursor.execute('''
            SELECT o.id, o.customer_name, o.customer_email, o.customer_phone, 
                   o.customer_address, o.delivery_time, o.comments,
                   o.total_services, o.total_price, o.order_date, o.status,
                   GROUP_CONCAT(os.service_name) as service_names
            FROM orders o
            LEFT JOIN order_services os ON o.id = os.order_id
            GROUP BY o.id
            ORDER BY o.order_date DESC
        ''')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'customer_phone': row[3],
                'customer_address': row[4],
                'delivery_time': row[5],
                'comments': row[6],
                'total_services': row[7],
                'total_price': row[8],
                'order_date': row[9],
                'status': row[10],
                'service_names': row[11] if row[11] else 'No services'
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
        
        # Получаем основную информацию о заказе
        cursor.execute('''
            SELECT id, customer_name, customer_email, customer_phone, customer_address,
                   delivery_time, comments, total_services, total_price, 
                   order_details, order_date, status 
            FROM orders 
            WHERE id = ?
        ''', (order_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Order not found'}), 404
        
        # Получаем услуги для этого заказа
        cursor.execute('''
            SELECT service_id, service_name, service_price, service_description
            FROM order_services 
            WHERE order_id = ?
        ''', (order_id,))
        
        services = []
        for service_row in cursor.fetchall():
            services.append({
                'service_id': service_row[0],
                'service_name': service_row[1],
                'service_price': service_row[2],
                'service_description': service_row[3]
            })
        
        conn.close()
        
        order = {
            'id': row[0],
            'customer_name': row[1],
            'customer_email': row[2],
            'customer_phone': row[3],
            'customer_address': row[4],
            'delivery_time': row[5],
            'comments': row[6],
            'total_services': row[7],
            'total_price': row[8],
            'order_details': json.loads(row[9]),
            'order_date': row[10],
            'status': row[11],
            'services': services
        }
        
        return jsonify(order), 200
            
    except Exception as e:
        print(f"Ошибка при получении заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>/services', methods=['GET'])
def get_order_services(order_id):
    """Получить все услуги для конкретного заказа"""
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT service_id, service_name, service_price, service_description
            FROM order_services 
            WHERE order_id = ?
        ''', (order_id,))
        
        services = []
        for row in cursor.fetchall():
            services.append({
                'service_id': row[0],
                'service_name': row[1],
                'service_price': row[2],
                'service_description': row[3]
            })
        
        conn.close()
        
        return jsonify(services), 200
            
    except Exception as e:
        print(f"Ошибка при получении услуг заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>', methods=['PUT', 'OPTIONS'])
def update_order(order_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Получаем данные из запроса
        order_data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['name', 'email', 'total_services', 'total_price']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Подключаемся к базе данных
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # Проверяем существование заказа
        cursor.execute('SELECT id FROM orders WHERE id = ?', (order_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Order not found'}), 404
        
        # Обновляем основные данные заказа
        cursor.execute('''
            UPDATE orders SET
                customer_name = ?,
                customer_email = ?,
                customer_phone = ?,
                customer_address = ?,
                delivery_time = ?,
                comments = ?,
                total_services = ?,
                total_price = ?,
                order_details = ?
            WHERE id = ?
        ''', (
            order_data['name'],
            order_data['email'],
            order_data.get('phone', ''),
            order_data.get('address', ''),
            order_data.get('delivery_time', ''),
            order_data.get('comments', ''),
            int(order_data['total_services']),
            order_data['total_price'],
            json.dumps(order_data, ensure_ascii=False),
            order_id
        ))
        
        # Удаляем старые услуги
        cursor.execute('DELETE FROM order_services WHERE order_id = ?', (order_id,))
        
        # Добавляем обновленные услуги
        total_services = int(order_data['total_services'])
        for i in range(total_services):
            service_prefix = f'service_{i}_'
            service_id = order_data.get(f'{service_prefix}id')
            service_name = order_data.get(f'{service_prefix}name')
            service_price = order_data.get(f'{service_prefix}price')
            service_description = order_data.get(f'{service_prefix}description', '')
            
            if service_id and service_name and service_price:
                cursor.execute('''
                    INSERT INTO order_services (order_id, service_id, service_name, service_price, service_description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, service_id, service_name, service_price, service_description))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Order updated successfully'
        }), 200
        
    except Exception as e:
        print(f"Ошибка при обновлении заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<int:order_id>', methods=['DELETE', 'OPTIONS'])
def delete_order(order_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # Проверяем существование заказа
        cursor.execute('SELECT id FROM orders WHERE id = ?', (order_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Order not found'}), 404
        
        # Удаляем заказ (благодаря CASCADE удалятся и связанные услуги)
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Order deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Ошибка при удалении заказа: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Инициализируем базу данных при запуске
    init_db()
    app.run(debug=True, host='0.0.0.0', port=10000)
