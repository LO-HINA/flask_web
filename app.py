from flask import Flask, render_template, request, jsonify,redirect
from exsitions import db, mail
from models import User, EmailCode
from datetime import datetime, timedelta
import random
import string
from flask_mail import Message
from flask import g, session
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
# 新增这行（加MAIL配置，和Render环境变量对应）
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))  # 端口转整数
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'  # 字符串转布尔
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 新增，关闭修改跟踪
# 绑定扩展到Flask应用
db.init_app(app)
mail.init_app(app)
with app.app_context():
    db.create_all()



@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')


# 1. 请求前置钩子：自动识别登录用户
@app.before_request
def before_request():
    user_id = session.get("user_id")
    if user_id:
        # 从数据库查当前登录用户
        g.user = db.session.get(User, user_id)
    else:
        g.user = None

# 2. 上下文处理器：把用户信息注入所有模板
@app.context_processor
def context_processor():
    return {
        "user": g.user  # 模板里直接用 {{ user }}
    }

@app.route('/logout')
def logout():
    # 清空session里的user_id，退出登录
    session.pop('user_id', None)
    # 跳回首页（或刷新当前页）
    return redirect('/')

# ===================== 接口实现（简洁版，和你之前风格一致） =====================
# 发送验证码接口
@app.route('/send_code', methods=['POST'])
def send_code():
    email = request.json.get('email')
    if not email:
        return jsonify({'result': False, 'message': '请输入邮箱'})

    # 邮箱已注册校验
    if db.session.scalar(db.select(User).where(User.email == email)):
        return jsonify({'result': False, 'message': '该邮箱已注册'})

    # 生成6位验证码
    code = ''.join(random.choices(string.digits, k=6))

    # 删除旧验证码，保存新验证码
    db.session.query(EmailCode).filter(EmailCode.email == email).delete()
    new_code = EmailCode(email=email, code=code)
    db.session.add(new_code)

    # 真实发送（上线时取消注释，替换config里的邮箱信息）
    msg = Message('注册验证码', recipients=[email], body=f'你的验证码：{code}，5分钟内有效')
    mail.send(msg)

    db.session.commit()
    return jsonify({'result': True, 'message': '验证码已发送'})


# 注册接口（完全沿用你的写法，只补安全校验）
@app.route('/register', methods=['GET', 'POST'])
def reg():
    if request.method == 'GET':
        return render_template('bash.html')  # 指向你的主页面，不是单独注册页
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        code = request.form.get('code')  # 前端传的是code，不是checkword

        # 1. 验证码校验
        code_model = db.session.scalar(
            db.select(EmailCode).where(EmailCode.email == email, EmailCode.code == code)
        )
        if not code_model or (datetime.now() - code_model.create_time) > timedelta(minutes=5) or code_model.is_used:
            return jsonify({'result': False, 'message': '验证码错误/已过期/已使用'})

        # 2. 用户名/邮箱唯一性校验
        if db.session.scalar(db.select(User).where(User.username == username)):
            return jsonify({'result': False, 'message': '用户名已存在'})
        if db.session.scalar(db.select(User).where(User.email == email)):
            return jsonify({'result': False, 'message': '邮箱已注册'})

        # 3. 创建用户（密码加密）
        user = User(username=username, email=email)
        user.set_password(password)  # 密码加密，核心！
        code_model.is_used = True  # 标记验证码已用

        # 4. 提交数据库（加异常回滚）
        try:
            db.session.add(user)
            db.session.commit()
            return jsonify({'result': True, 'message': '注册成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'result': False, 'message': f'注册失败：{str(e)[:20]}'})

# 登录接口
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = db.session.scalar(db.select(User).where(User.username == username))
    if user and user.check_password(password):
        session['user_id'] = user.id
        return jsonify({'result': True, 'message': '登录成功'})
    return jsonify({'result': False, 'message': '用户名或密码错误'})



@app.route('/hina/dress/1')
def hina_dress_1():
    return render_template('hina_dress_1.html')


@app.route('/hina/dress/2')  # 自定义URL路径，比如项目1的详情页
def hina_dress_2():
    # 可以返回模板或简单响应，根据你的需求改
    return render_template('hina_dress_2.html')  # 推荐：新建对应的详情页模板
    # 临时测试：return "这是项目1的详情页"


@app.route('/hina/dress/3')
def hina_dress_3():
    return render_template('hina_dress_3.html')


@app.route('/hoshino/dress/1')
def hoshino_dress_1():
    return render_template('hoshino_dress_1.html')


@app.route('/hoshino/dress/2')
def hoshino_dress_2():
    return render_template('hoshino_dress_2.html')


@app.route('/hoshino/dress/3')
def hoshino_dress_3():
    return render_template('hoshino_dress_3.html')

@app.route('/azusa/dress/1')
def azusa_dress_1():
    return render_template('azusa_dress_1.html')

@app.route('/wink/dress/1')
def wink_dress_1():
    return render_template('wink_dress_1.html')


if __name__ == '__main__':
    app.run(debug=False, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')