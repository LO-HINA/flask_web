from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_mail import Mail

# 规定用法，方便后来sql操作
class Base(DeclarativeBase):
    """SQLAlchemy2.0 + 中定义「基础模型类」的配置,给外键，主键，索引之类的命名，因为正常情况下是ix_123、fk_abcd 这种无意义的字符，方便对数据库管理"""
    # MetaData：SQLAlchemy中用于存储数据库表结构、约束等元信息的类；
    metadata = MetaData(naming_convention={  # naming_convention：约束命名规则字典，key 是约束类型缩写，value 是命名模板
        # ix: index，索引。
        "ix": 'ix_%(column_0_label)s',# 所以以后索引就可以ix_vegetable_category_id（蔬菜表 category_id 字段的索引），简化了后面无意义的字符串
        # un: unique，唯一约束
        "uq": "uq_%(table_name)s_%(column_0_name)s",# 同理，uq_vegetable_name（蔬菜表 name 字段的唯一约束）
        # ck: Check，检查约束
        "ck": "ck_%(table_name)s_%(constraint_name)s",# ck_vegetable_price_gt0（蔬菜表 price>0 的检查约束）
        # fk: Foreign Key，外键约束
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        # pk: Primary Key，主键约束
        "pk": "pk_%(table_name)s"
    })



db = SQLAlchemy(model_class=Base)
migrate = Migrate()
mail = Mail()