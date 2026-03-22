# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from exsitions import Base, db

# 用户模型
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)  # 存哈希，不存明文

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 验证码模型
class EmailCode(Base):
    __tablename__ = 'email_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), nullable=False)
    code = Column(String(6), nullable=False)
    create_time = Column(DateTime, default=datetime.now)
    is_used = Column(Boolean, default=False)