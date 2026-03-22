from flask import Flask
from exsitions import db
from models import User, EmailCode
import os  # 新增

app = Flask(__name__)
# 替换原来的 config 引用
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 初始化数据库
with app.app_context():
    db.create_all()  # 创建所有表
    print("数据库表创建成功！")