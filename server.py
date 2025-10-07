from flask import Flask
import os
import json

app = Flask(__name__)

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
            return data, 200
        
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return []
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)