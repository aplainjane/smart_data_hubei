from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static')
CORS(app)  # 启用跨域支持（如果你的网页也用 fetch 访问 API）

# === 1️⃣ 默认首页：返回 static/index.html ===
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# === 2️⃣ 提供一个 GET API ===
@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "你好，这里是 Flask 后端！"})

# === 3️⃣ 提供一个 POST API ===
@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    print("收到前端数据:", data)
    return jsonify({"status": "ok", "received": data})

# === 4️⃣ 启动服务 ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
