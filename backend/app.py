from flask import Flask
from flask_cors import CORS
from backend.api.routes import api
from backend.models.database import get_db
import os
import asyncio

# 初始化Flask应用
app = Flask(__name__)

# 配置CORS，允许前端访问
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# 注册API蓝图
app.register_blueprint(api, url_prefix='/api')

# 异步初始化数据库连接
async def initialize_database_async():
    db = get_db()
    await db.initialize()

# 同步包装器以在应用启动时运行异步初始化
def initialize_database():
    asyncio.run(initialize_database_async())

initialize_database()

# 主入口
if __name__ == '__main__':
    # 获取当前文件目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 设置静态文件目录
    app.static_folder = os.path.join(current_dir, 'static')
    # 运行开发服务器
    app.run(host='0.0.0.0', port=5000, debug=True)