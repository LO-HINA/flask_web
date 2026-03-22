# init_db.py
from flask import Flask
from exsitions import db
from models import User, EmailCode
import config

app = Flask(__name__)
app.config.from_object(config.config['default'])
db.init_app(app)

# 初始化数据库
with app.app_context():
    db.create_all()  # 创建所有表
    print("数据库表创建成功！")