from flask import Flask, request, jsonify
import os
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Конфигурация базы данных
DATABASE = 'services.db'

def init_db():
    """Инициализация базы данных и создание таблиц"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Создание таблицы услуг
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            category TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_email TEXT,
            service_id INTEGER NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')
    
    # Добавляем тестовые услуги если таблица пустая
    cursor.execute('SELECT COUNT(*) FROM services')
    if cursor.fetchone()[0] == 0:
        sample_services = [
            ('УПР доставка', 'Персональная доставка с примеркой', 1000.0, 'delivery', '🚚'),
            ('Этикетки', 'Качественные этикетки для продукции', 150.0, 'accessories', '🏷️'),
            ('Часы с принтом', 'Настенные часы с индивидуальным дизайном', 900.0, 'accessories', '⏰'),
            ('Печать на футболках', 'Качественная печать на футболках различных размеров', 500.0, 'clothing', '👕'),
            ('Печать на кружках', 'Печать на керамических кружках', 400.0, 'accessories', '☕'),
            ('Визитки', 'Печать визиток на качественной бумаге', 300.0, 'polygraphy', '📇'),
            ('Листовки', 'Печать рекламных листовок', 200.0, 'polygraphy', '📄'),
            ('Брендированные ручки', 'Ручки с логотипом компании', 150.0, 'souvenirs', '✏️')
        ]
        
        cursor.executemany('''
            INSERT INTO services (name, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_services)
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Основной маршрут для получения услуг из базы данных
@app.route('/', methods=['GET'])
def get_services():
    """Получение всех услуг из базы данных в формате для фронтенда"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем все услуги из базы данных
        cursor.execute('''
            SELECT s.*, 
                   CASE 
                       WHEN s.category = 'clothing' THEN 'Печать на одежде'
                       WHEN s.category = 'accessories' THEN 'Аксессуары'
                       WHEN s.category = 'headwear' THEN 'Головные уборы'
                       WHEN s.category = 'premium' THEN 'Премиум'
                       WHEN s.category = 'polygraphy' THEN 'Полиграфия'
                       WHEN s.category = 'souvenirs' THEN 'Сувениры'
                       WHEN s.category = 'delivery' THEN 'Доставка'
                       ELSE s.category
                   END as section_title
            FROM services s
            ORDER BY s.category, s.name
        ''')
        services = cursor.fetchall()
        
        conn.close()
        
        # Преобразуем в формат, ожидаемый фронтендом
        sections = {}
        for service in services:
            category = service['category']
            if category not in sections:
                sections[category] = {
                    'section': category,
                    'title': service['section_title'],
                    'services': []
                }
            
            sections[category]['services'].append({
                'id': service['id'],
                'name': service['name'],
                'description': service['description'],
                'price': f"{int(service['price'])} ₽",
                'image': service['image_url'],
                'section': category
            })
        
        # Преобразуем словарь в список
        result = list(sections.values())
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Ошибка при загрузке данных из базы: {e}")
        return jsonify([]), 500

# Маршрут для добавления новой услуги в базу данных
@app.route('/add-service', methods=['POST'])
def add_service():
    """Добавление новой услуги в базу данных"""
    try:
        data = request.get_json()
        
        # Проверка обязательных полей
        if not data or not data.get('name'):
            return jsonify({'error': 'Название услуги обязательно'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Вставляем новую услугу в базу данных
        cursor.execute('''
            INSERT INTO services (name, description, price, category, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('name'), 
            data.get('description'), 
            data.get('price'), 
            data.get('category'),
            data.get('image_url')
        ))
        
        conn.commit()
        service_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'id': service_id, 
            'message': 'Услуга успешно добавлена в базу данных'
        }), 201
        
    except Exception as e:
        print(f"Ошибка при добавлении услуги: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Маршрут для получения всех услуг (простой список)
@app.route('/services', methods=['GET'])
def get_services_list():
    """Получение всех услуг в простом формате"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM services ORDER BY name')
        services = cursor.fetchall()
        
        # Преобразование в список словарей
        services_list = []
        for service in services:
            services_list.append(dict(service))
        
        conn.close()
        return jsonify(services_list), 200
        
    except Exception as e:
        print(f"Ошибка при загрузке услуг: {e}")
        return jsonify([]), 500

# Маршрут для получения конкретной услуги
@app.route('/services/<int:service_id>', methods=['GET'])
def get_service(service_id):
    """Получение конкретной услуги по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
        service = cursor.fetchone()
        
        conn.close()
        
        if service:
            return jsonify(dict(service)), 200
        else:
            return jsonify({'error': 'Услуга не найдена'}), 404
            
    except Exception as e:
        print(f"Ошибка при загрузке услуги: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# ОСНОВНОЙ МАРШРУТ ДЛЯ ОТПРАВКИ ЗАКАЗОВ
@app.route('/submit-order', methods=['POST'])
def submit_order():
    """Обработка заказов от клиентов и сохранение в базу данных"""
    try:
        data = request.get_json()
        
        # Проверка обязательных полей
        if not data:
            return jsonify({'error': 'Данные не получены'}), 400
            
        if not data.get('customer_name'):
            return jsonify({'error': 'Имя обязательно'}), 400
            
        if not data.get('customer_phone'):
            return jsonify({'error': 'Телефон обязателен'}), 400
            
        if not data.get('service_id'):
            return jsonify({'error': 'ID услуги обязателен'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование услуги
        cursor.execute('SELECT id, name FROM services WHERE id = ?', (data.get('service_id'),))
        service = cursor.fetchone()
        
        if not service:
            conn.close()
            return jsonify({'error': 'Услуга не найдена'}), 404
        
        # Сохраняем заказ в базе данных
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_email, service_id, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('customer_name'), 
            data.get('customer_phone'), 
            data.get('customer_email', ''), 
            data.get('service_id'), 
            data.get('message', '')
        ))
        
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()
        
        print(f"Новый заказ #{order_id}: {data.get('customer_name')} - {service['name']}")
        
        return jsonify({
            'id': order_id, 
            'message': 'Заказ успешно отправлен',
            'service_name': service['name']
        }), 201
        
    except Exception as e:
        print(f"Ошибка при обработке заказа: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Маршрут для получения всех заказов (для админки)
@app.route('/orders', methods=['GET'])
def get_orders():
    """Получение всех заказов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.*, s.name as service_name, s.price as service_price
            FROM orders o 
            LEFT JOIN services s ON o.service_id = s.id 
            ORDER BY o.created_at DESC
        ''')
        orders = cursor.fetchall()
        
        orders_list = []
        for order in orders:
            order_dict = dict(order)
            # Форматируем дату для удобства чтения
            order_dict['created_at'] = order_dict['created_at']
            orders_list.append(order_dict)
        
        conn.close()
        return jsonify(orders_list), 200
        
    except Exception as e:
        print(f"Ошибка при загрузке заказов: {e}")
        return jsonify([]), 500

# Маршрут для получения статистики (для админки)
@app.route('/stats', methods=['GET'])
def get_stats():
    """Получение статистики по заказам"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Общее количество заказов
        cursor.execute('SELECT COUNT(*) as total_orders FROM orders')
        total_orders = cursor.fetchone()['total_orders']
        
        # Заказы по статусам
        cursor.execute('SELECT status, COUNT(*) as count FROM orders GROUP BY status')
        status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Популярные услуги
        cursor.execute('''
            SELECT s.name, COUNT(o.id) as order_count 
            FROM orders o 
            JOIN services s ON o.service_id = s.id 
            GROUP BY s.name 
            ORDER BY order_count DESC 
            LIMIT 5
        ''')
        popular_services = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_orders': total_orders,
            'status_stats': status_stats,
            'popular_services': popular_services
        }), 200
        
    except Exception as e:
        print(f"Ошибка при загрузке статистики: {e}")
        return jsonify({'error': 'Ошибка загрузки статистики'}), 500

# Маршрут для обновления статуса заказа
@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    """Обновление статуса заказа"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Статус обязателен'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM orders WHERE id = ?', (order_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Заказ не найден'}), 404
        
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Статус заказа обновлен успешно'}), 200
        
    except Exception as e:
        print(f"Ошибка при обновлении заказа: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Маршрут для удаления услуги
@app.route('/services/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Удаление услуги из базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование услуги
        cursor.execute('SELECT id FROM services WHERE id = ?', (service_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Услуга не найдена'}), 404
        
        # Удаляем услугу
        cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Услуга успешно удалена'}), 200
        
    except Exception as e:
        print(f"Ошибка при удалении услуги: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

# Резервный маршрут для чтения из JSON файла (на случай проблем с базой)
@app.route('/json-backup', methods=['GET'])
def get_services_from_json():
    """Резервный метод получения услуг из JSON файла"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_dir, 'services-data.json')
        
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return jsonify(data), 200
        else:
            return jsonify({'error': 'JSON файл не найден'}), 404
        
    except Exception as e:
        print(f"Ошибка при загрузке данных из JSON: {e}")
        return jsonify([]), 500

# Маршрут для проверки здоровья API
@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API и базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем подключение к базе
        cursor.execute('SELECT COUNT(*) as service_count FROM services')
        service_count = cursor.fetchone()['service_count']
        
        cursor.execute('SELECT COUNT(*) as order_count FROM orders')
        order_count = cursor.fetchone()['order_count']
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'services_count': service_count,
            'orders_count': order_count,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Ошибка при проверке здоровья: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Инициализация базы данных при запуске
    init_db()
    print("База данных инициализирована")
    print("Доступные эндпоинты:")
    print("  GET  / - получение услуг для сайта")
    print("  POST /submit-order - отправка заказа")
    print("  GET  /orders - получение всех заказов (админка)")
    print("  GET  /stats - статистика (админка)")
    print("  GET  /health - проверка работы API")
    
    app.run(debug=True, host='0.0.0.0', port=10000)
