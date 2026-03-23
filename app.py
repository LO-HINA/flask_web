from flask import Flask, render_template, request, jsonify,redirect,abort
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
    # 增加一个过滤：如果是请求静态文件（images/css/js），直接返回，不去查数据库
    if request.endpoint == 'static':
        return

    user_id = session.get("user_id")
    if user_id:
        # 使用 get 能直接利用缓存，比 select 稍微快一点
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
    # 统一用 try-except 包裹，防止后端直接炸出 500 HTML 页面
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'result': False, 'message': '请输入邮箱'})

            # --- 第一步：限流检查（放在最前面！） ---
        last_code = db.session.scalar(
            db.select(EmailCode).where(EmailCode.email == email)
            .order_by(EmailCode.create_time.desc())
            )
        if last_code and (datetime.now() - last_code.create_time) < timedelta(seconds=60):
            return jsonify({'result': False, 'message': '发送太频繁，请60秒后再试'})

        # 1. 校验是否已注册
        if db.session.scalar(db.select(User).where(User.email == email)):
            return jsonify({'result': False, 'message': '该邮箱已注册'})

        # 2. 生成验证码
        code = ''.join(random.choices(string.digits, k=6))

        # 3. 先处理数据库：删除旧的，存入新的
        db.session.query(EmailCode).filter(EmailCode.email == email).delete()
        new_code = EmailCode(email=email, code=code)
        db.session.add(new_code)

        # 核心改变：先 commit！确保存进去了
        db.session.commit()

        # 4. 最后尝试发邮件
        try:
            msg = Message('注册验证码', recipients=[email], body=f'你的验证码：{code}，5分钟内有效')
            mail.send(msg)
            return jsonify({'result': True, 'message': '验证码已发送'})
        except Exception as mail_err:
            # 如果邮件发失败了，虽然数据库有记录，但也要告诉前端
            return jsonify({'result': False, 'message': '邮件服务繁忙，请稍后再试'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'result': False, 'message': f'服务器内部错误: {str(e)[:30]}'})


# 注册接口（完全沿用你的写法，只补安全校验）
@app.route('/register', methods=['POST'])
def reg():
    # 1. 统一数据获取：改为从 request.form 获取（对应你前端的 FormData）
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    code = request.form.get('code')

    # 2. 基础非空校验
    if not all([email, username, password, code]):
        return jsonify({'result': False, 'message': '请填写完整信息'})

    try:
        # 3. 严格验证码校验
        # 必须同时满足：邮箱匹配、验证码匹配、未被使用、5分钟内有效
        code_model = db.session.scalar(
            db.select(EmailCode).where(
                EmailCode.email == email,
                EmailCode.code == code,
                EmailCode.is_used == False  # 必须未被使用
            )
        )

        # 检查是否存在记录
        if not code_model:
            return jsonify({'result': False, 'message': '验证码错误'})

        # 检查是否过期（5分钟）
        if (datetime.now() - code_model.create_time) > timedelta(minutes=5):
            return jsonify({'result': False, 'message': '验证码已过期'})

        # 4. 查重逻辑（防止用户名或邮箱冲突）
        if db.session.scalar(db.select(User).where(User.username == username)):
            return jsonify({'result': False, 'message': '用户名已被占用'})
        if db.session.scalar(db.select(User).where(User.email == email)):
            return jsonify({'result': False, 'message': '邮箱已被注册'})

        # 5. 执行入库事务
        # 将“创建用户”和“标记验证码失效”绑在一起，要么全成功，要么全失败
        new_user = User(username=username, email=email)
        new_user.set_password(password)  # 必须调用加密方法

        code_model.is_used = True  # 标记此验证码已失效

        db.session.add(new_user)
        db.session.commit()  # 统一提交

        return jsonify({'result': True, 'message': '注册成功！'})

    except Exception as e:
        db.session.rollback()  # 万一报错，全部撤回，保证数据库干净
        return jsonify({'result': False, 'message': f'注册系统异常: {str(e)[:20]}'})
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


# 第一步：定义允许的角色和服装ID范围（防止非法访问）
ALLOWED_CHARACTERS = {
    "hina": [1, 2, 3],  # hina 支持 dress_id 1/2/3
    "hoshino": [1, 2, 3],  # hoshino 支持 dress_id 1/2/3
    "azusa": [1],  # azusa 只支持 dress_id 1
    "wink": [1]  # wink 只支持 dress_id 1
}


# 第二步：单个动态路由覆盖所有场景
@app.route('/<character>/dress/<int:dress_id>')
def character_dress(character, dress_id):

    # 1. 校验角色是否合法
    if character not in ALLOWED_CHARACTERS:
        abort(404)  # 非法角色返回404

    # 2. 校验服装ID是否合法
    if dress_id not in ALLOWED_CHARACTERS[character]:
        abort(404)  # 非法ID返回404

    # 3. 动态拼接模板名并渲染（和你原有模板命名规则一致）
    template_name = f"{character}_dress_{dress_id}.html"

    template_path = os.path.join(app.template_folder, template_name)
    if not os.path.exists(template_path):
        abort(404) # 如果你忘了建这个 HTML，返回 404 而不是让后端崩溃 500

    return render_template(template_name)


if __name__ == '__main__':
    app.run(debug=False, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')