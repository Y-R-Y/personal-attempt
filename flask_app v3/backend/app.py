"""
小学刷题乐园 - Flask 后端服务
提供题目 API、成绩提交、用户数据管理等接口
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime, timedelta
import hashlib
import secrets

app = Flask(__name__)
CORS(app)  # 允许跨域请求

DATABASE = 'quiz.db'
SECRET_KEY = secrets.token_hex(32)  # 用于 JWT 签名

# ============== 数据库初始化 ==============

def init_db():
    """初始化数据库，创建表并导入初始题库"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建题目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            level INTEGER NOT NULL,
            type TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建用户表（添加用户名、密码、手机号）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            student_name TEXT,
            phone TEXT,
            avatar TEXT,
            level INTEGER DEFAULT 1,
            total_questions INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            perfect_score INTEGER DEFAULT 0,
            consecutive_days INTEGER DEFAULT 1,
            last_login DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建答题记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id INTEGER,
            subject TEXT,
            user_answer TEXT,
            is_correct INTEGER,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # 创建错题表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id INTEGER,
            subject TEXT,
            wrong_count INTEGER DEFAULT 1,
            last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # 创建成就表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_id INTEGER,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 创建每日任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_date DATE,
            target_questions INTEGER DEFAULT 10,
            completed_questions INTEGER DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # AI使用记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            usage_type TEXT,  -- 'explanation', 'study_plan', 'report'
            tokens_used INTEGER,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 用户会员信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            subscription_type TEXT DEFAULT 'free',  -- 'free', 'vip_monthly', 'vip_yearly'
            start_date DATE,
            end_date DATE,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 学习计划表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_date DATE,
            plan_content TEXT,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    # 检查并添加 avatar 字段（数据库迁移）
    cursor.execute('PRAGMA table_info(users)')
    columns = [col[1] for col in cursor.fetchall()]
    if 'avatar' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN avatar TEXT')
        conn.commit()
        print("✓ 已添加 avatar 字段")
    
    # 检查并添加 total_study_time 字段（数据库迁移）
    if 'total_study_time' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN total_study_time INTEGER DEFAULT 0')
        conn.commit()
        print("✓ 已添加 total_study_time 字段")
    
    # 检查并添加AI相关字段
    if 'ai_usage_count' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN ai_usage_count INTEGER DEFAULT 0')
        conn.commit()
        print("✓ 已添加 ai_usage_count 字段")
    
    if 'monthly_ai_quota' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN monthly_ai_quota INTEGER DEFAULT 3')
        conn.commit()
        print("✓ 已添加 monthly_ai_quota 字段")
    
    # 检查是否需要导入初始题库
    cursor.execute('SELECT COUNT(*) FROM questions')
    count = cursor.fetchone()[0]
    
    if count == 0:
        import_initial_questions(cursor)
        conn.commit()
        print("✓ 初始题库已导入")
    
    conn.close()
    print("✓ 数据库初始化完成")


def import_initial_questions(cursor):
    """导入初始题库数据"""
    questions = [
        # 数学 - 一年级 (level 1)
        ('math', 1, 'choice', '5 + 3 = ?', json.dumps(['6', '7', '8', '9']), '8'),
        ('math', 1, 'choice', '10 - 4 = ?', json.dumps(['5', '6', '7', '8']), '6'),
        ('math', 1, 'choice', '7 + 6 = ?', json.dumps(['12', '13', '14', '15']), '13'),
        ('math', 1, 'choice', '15 - 8 = ?', json.dumps(['6', '7', '8', '9']), '7'),
        ('math', 1, 'choice', '9 + 9 = ?', json.dumps(['17', '18', '19', '20']), '18'),
        # 数学 - 二年级 (level 2)
        ('math', 2, 'choice', '25 + 17 = ?', json.dumps(['40', '41', '42', '43']), '42'),
        ('math', 2, 'choice', '50 - 23 = ?', json.dumps(['26', '27', '28', '29']), '27'),
        ('math', 2, 'choice', '6 × 7 = ?', json.dumps(['40', '42', '44', '48']), '42'),
        ('math', 2, 'choice', '36 ÷ 6 = ?', json.dumps(['5', '6', '7', '8']), '6'),
        ('math', 2, 'choice', '8 × 9 = ?', json.dumps(['70', '72', '74', '76']), '72'),
        # 数学 - 三年级 (level 3)
        ('math', 3, 'choice', '125 + 87 = ?', json.dumps(['202', '212', '222', '232']), '212'),
        ('math', 3, 'choice', '300 - 156 = ?', json.dumps(['134', '144', '154', '164']), '144'),
        ('math', 3, 'choice', '24 × 5 = ?', json.dumps(['100', '110', '120', '130']), '120'),
        ('math', 3, 'choice', '144 ÷ 12 = ?', json.dumps(['10', '11', '12', '13']), '12'),
        ('math', 3, 'choice', '7 × 8 + 6 = ?', json.dumps(['58', '60', '62', '64']), '62'),
        
        # 语文 - 一年级 (level 1)
        ('chinese', 1, 'choice', '"日"字的拼音是？', json.dumps(['rì', 'rì', 'yì', 'yí']), 'rì'),
        ('chinese', 1, 'choice', '"月"字有几画？', json.dumps(['3 画', '4 画', '5 画', '6 画']), '4 画'),
        ('chinese', 1, 'choice', '反义词：大 - ？', json.dumps(['小', '多', '高', '长']), '小'),
        ('chinese', 1, 'choice', '"春眠不觉晓"的下一句是？', json.dumps(['处处闻啼鸟', '夜来风雨声', '花落知多少', '举头望明月']), '处处闻啼鸟'),
        ('chinese', 1, 'choice', '"山"的反义词是？', json.dumps(['水', '石', '土', '田']), '水'),
        # 语文 - 二年级 (level 2)
        ('chinese', 2, 'choice', '"美丽"的近义词是？', json.dumps(['漂亮', '难看', '普通', '一般']), '漂亮'),
        ('chinese', 2, 'choice', '下列哪个是比喻句？', json.dumps(['他像他爸爸', '月亮像玉盘', '他好像在想什么', '他像来了']), '月亮像玉盘'),
        ('chinese', 2, 'choice', '"床前明月光"的作者是谁？', json.dumps(['杜甫', '李白', '白居易', '王维']), '李白'),
        ('chinese', 2, 'choice', '下列词语书写正确的是？', json.dumps(['已经', '已经', '以经', '己经']), '已经'),
        ('chinese', 2, 'choice', '"千里之行"的下一句是？', json.dumps(['始于足下', '成于坚持', '贵在恒心', '在于积累']), '始于足下'),
        # 语文 - 三年级 (level 3)
        ('chinese', 3, 'choice', '"欲穷千里目，更上一层楼"出自？', json.dumps(['《登鹳雀楼》', '《望庐山瀑布》', '《静夜思》', '《春晓》']), '《登鹳雀楼》'),
        ('chinese', 3, 'choice', '下列哪个成语表示专心致志？', json.dumps(['一心一意', '三心二意', '心不在焉', '漫不经心']), '一心一意'),
        ('chinese', 3, 'choice', '"飞流直下三千尺"描写的是？', json.dumps(['黄河', '长江', '瀑布', '大海']), '瀑布'),
        ('chinese', 3, 'choice', '下列哪个是拟人句？', json.dumps(['小鸟在唱歌', '他跑得像风一样', '月亮像圆盘', '花儿很红']), '小鸟在唱歌'),
        ('chinese', 3, 'choice', '"不识庐山真面目"的下一句是？', json.dumps(['只缘身在此山中', '远近高低各不同', '横看成岭侧成峰', '白云深处有人家']), '只缘身在此山中'),
        
        # 英语 - 一年级 (level 1)
        ('english', 1, 'choice', '"苹果"的英文是？', json.dumps(['apple', 'banana', 'orange', 'pear']), 'apple'),
        ('english', 1, 'choice', '"猫"的英文是？', json.dumps(['dog', 'cat', 'bird', 'fish']), 'cat'),
        ('english', 1, 'choice', '红色用英文怎么说？', json.dumps(['blue', 'green', 'red', 'yellow']), 'red'),
        ('english', 1, 'choice', '"Good morning"的意思是？', json.dumps(['早上好', '下午好', '晚上好', '再见']), '早上好'),
        ('english', 1, 'choice', '数字"3"的英文是？', json.dumps(['two', 'three', 'four', 'five']), 'three'),
        # 英语 - 二年级 (level 2)
        ('english', 2, 'choice', '"I ___ a student." 应该填？', json.dumps(['am', 'is', 'are', 'be']), 'am'),
        ('english', 2, 'choice', '"She ___ to school." 应该填？', json.dumps(['go', 'goes', 'going', 'went']), 'goes'),
        ('english', 2, 'choice', '"Thank you"的回答是？', json.dumps(["You're welcome", 'No', 'Yes', 'OK']), "You're welcome"),
        ('english', 2, 'choice', '"书"的英文是？', json.dumps(['pen', 'book', 'ruler', 'pencil']), 'book'),
        ('english', 2, 'choice', '复数形式：child → ？', json.dumps(['childs', 'children', 'childes', 'child']), 'children'),
        # 英语 - 三年级 (level 3)
        ('english', 3, 'choice', '"Yesterday I ___ to the park." 应该填？', json.dumps(['go', 'goes', 'went', 'going']), 'went'),
        ('english', 3, 'choice', '比较级：big → ？', json.dumps(['biger', 'bigger', 'biggest', 'more big']), 'bigger'),
        ('english', 3, 'choice', '"What time is it?" 是问？', json.dumps(['日期', '时间', '地点', '人物']), '时间'),
        ('english', 3, 'choice', '"Happy birthday!" 的回答是？', json.dumps(['Thank you!', 'You too!', 'OK!', 'No!']), 'Thank you!'),
        ('english', 3, 'choice', '"游泳"的英文是？', json.dumps(['run', 'swim', 'jump', 'walk']), 'swim'),
        
        # 科学 - 一年级 (level 1)
        ('science', 1, 'choice', '植物生长需要什么？', json.dumps(['阳光', '石头', '空气', '水']), '阳光'),
        ('science', 1, 'choice', '动物呼吸需要吸入什么气体？', json.dumps(['氧气', '二氧化碳', '氮气', '氢气']), '氧气'),
        ('science', 1, 'choice', '水的三态不包括以下哪种？', json.dumps(['固态', '液态', '气态', '火态']), '火态'),
        ('science', 1, 'choice', '下列哪个是哺乳动物？', json.dumps(['狗', '鱼', '鸟', '蝴蝶']), '狗'),
        ('science', 1, 'choice', '地球围绕什么转？', json.dumps(['太阳', '月亮', '火星', '金星']), '太阳'),
        # 科学 - 二年级 (level 2)
        ('science', 2, 'choice', '光合作用是植物利用什么制造养分？', json.dumps(['阳光', '月光', '星光', '灯光']), '阳光'),
        ('science', 2, 'choice', '下列哪个是导体？', json.dumps(['铜', '木头', '塑料', '橡胶']), '铜'),
        ('science', 2, 'choice', '声音在什么介质中传播最快？', json.dumps(['固体', '液体', '气体', '真空']), '固体'),
        ('science', 2, 'choice', '磁铁有几个磁极？', json.dumps(['2个', '1个', '3个', '4个']), '2个'),
        ('science', 2, 'choice', '彩虹有几种颜色？', json.dumps(['7种', '5种', '6种', '8种']), '7种'),
        # 科学 - 三年级 (level 3)
        ('science', 3, 'choice', '人体的骨骼有多少块？', json.dumps(['206块', '200块', '210块', '216块']), '206块'),
        ('science', 3, 'choice', '光年是测量什么的单位？', json.dumps(['距离', '时间', '速度', '重量']), '距离'),
        ('science', 3, 'choice', '下列哪个是可再生能源？', json.dumps(['太阳能', '煤炭', '石油', '天然气']), '太阳能'),
        ('science', 3, 'choice', '水的沸点是？', json.dumps(['100°C', '90°C', '110°C', '120°C']), '100°C'),
        ('science', 3, 'choice', '地球的卫星是？', json.dumps(['月球', '火星', '金星', '木星']), '月球'),
        
        # 历史 - 一年级 (level 1)
        ('history', 1, 'choice', '中国的国旗是什么颜色？', json.dumps(['红色', '蓝色', '绿色', '黄色']), '红色'),
        ('history', 1, 'choice', '中华人民共和国成立于哪一年？', json.dumps(['1949年', '1950年', '1948年', '1951年']), '1949年'),
        ('history', 1, 'choice', '中国古代四大发明不包括？', json.dumps(['火车', '造纸术', '指南针', '火药']), '火车'),
        ('history', 1, 'choice', '端午节是为了纪念谁？', json.dumps(['屈原', '李白', '杜甫', '孔子']), '屈原'),
        ('history', 1, 'choice', '春节是农历的哪一天？', json.dumps(['正月初一', '正月十五', '五月初五', '八月十五']), '正月初一'),
        # 历史 - 二年级 (level 2)
        ('history', 2, 'choice', '秦始皇统一了中国，他建立了哪个朝代？', json.dumps(['秦朝', '汉朝', '唐朝', '宋朝']), '秦朝'),
        ('history', 2, 'choice', '丝绸之路是从中国通向哪里？', json.dumps(['西方', '东方', '南方', '北方']), '西方'),
        ('history', 2, 'choice', '《史记》的作者是谁？', json.dumps(['司马迁', '班固', '陈寿', '范晔']), '司马迁'),
        ('history', 2, 'choice', '唐朝的首都是哪里？', json.dumps(['长安', '洛阳', '开封', '南京']), '长安'),
        ('history', 2, 'choice', '郑和下西洋是在哪个朝代？', json.dumps(['明朝', '唐朝', '宋朝', '元朝']), '明朝'),
        # 历史 - 三年级 (level 3)
        ('history', 3, 'choice', '鸦片战争发生在哪一年？', json.dumps(['1840年', '1850年', '1860年', '1870年']), '1840年'),
        ('history', 3, 'choice', '辛亥革命推翻了哪个朝代？', json.dumps(['清朝', '明朝', '元朝', '宋朝']), '清朝'),
        ('history', 3, 'choice', '五四运动发生在哪一年？', json.dumps(['1919年', '1920年', '1918年', '1921年']), '1919年'),
        ('history', 3, 'choice', '万里长城最早修建于哪个朝代？', json.dumps(['秦朝', '汉朝', '明朝', '唐朝']), '秦朝'),
        ('history', 3, 'choice', '孔子的思想核心是什么？', json.dumps(['仁', '义', '礼', '智']), '仁'),
    ]
    
    cursor.executemany('''
        INSERT INTO questions (subject, level, type, question, options, answer)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', questions)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============== 认证工具函数 ==============

def hash_password(password):
    """密码哈希（SHA-256 + salt）"""
    salt = "quiz_salt_2026"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def generate_token(user_id):
    """生成简单的 Token（用于身份验证）"""
    # 简单实现：user_id + 时间戳 + 密钥的哈希
    timestamp = int(datetime.now().timestamp())
    data = f"{user_id}:{timestamp}:{SECRET_KEY}"
    token = hashlib.sha256(data.encode()).hexdigest()
    return f"{user_id}:{timestamp}:{token}"


def verify_token(token):
    """验证 Token 并返回 user_id"""
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        user_id, timestamp, token_hash = parts
        
        # 验证时间戳（24 小时内有效）
        if datetime.now().timestamp() - int(timestamp) > 86400:
            return None
        
        # 重新计算哈希验证
        data = f"{user_id}:{timestamp}:{SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        
        if token_hash == expected_hash:
            return int(user_id)
        return None
    except:
        return None


def token_required(f):
    """Token 验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少认证 Token'}), 401
        
        # 移除 "Bearer " 前缀
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Token 无效或已过期'}), 401
        
        request.current_user_id = user_id
        return f(*args, **kwargs)
    return decorated


# ============== API 接口 ==============

# ============== 静态文件服务（前端页面） ==============

# 前端目录路径
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')

@app.route('/')
def serve_index():
    """提供前端首页"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供前端静态文件（CSS、JS 等）"""
    return send_from_directory(FRONTEND_DIR, filename)


# ============== API 接口 ==============

# ============== 认证接口 ==============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    student_name = data.get('student_name', '').strip()
    phone = data.get('phone', '').strip()
    
    # 验证输入
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3:
        return jsonify({'error': '用户名至少 3 个字符'}), 400
    
    if len(password) < 6:
        return jsonify({'error': '密码至少 6 个字符'}), 400
    
    if not phone:
        return jsonify({'error': '手机号不能为空（用于找回密码）'}), 400
    
    if len(phone) != 11 or not phone.isdigit():
        return jsonify({'error': '请输入有效的 11 位手机号码'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({'error': '用户名已存在'}), 400
        
        # 检查手机号是否已被注册
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            return jsonify({'error': '该手机号已被注册'}), 400
        
        # 创建用户
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, student_name, phone, last_login)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, student_name or username, phone, datetime.now().date().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # 生成 Token
        token = generate_token(user_id)
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user_id': user_id,
            'username': username,
            'token': token
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'注册失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 查找用户
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 验证密码
        password_hash = hash_password(password)
        if user['password_hash'] != password_hash:
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 更新最后登录时间
        cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now().date().isoformat(), user['id']))
        conn.commit()
        
        # 生成 Token
        token = generate_token(user['id'])
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user_id': user['id'],
            'username': user['username'],
            'student_name': user['student_name'],
            'token': token
        })
        
    except Exception as e:
        return jsonify({'error': f'登录失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出（客户端删除 Token 即可）"""
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/api/auth/check-username', methods=['POST'])
def check_username():
    """找回密码步骤一：验证用户名是否存在"""
    data = request.json
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'error': '用户名不能为空'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'exists': False, 'error': '该用户名不存在'}), 404

        return jsonify({'exists': True, 'message': '用户名验证通过'})

    except Exception as e:
        return jsonify({'error': f'验证失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/auth/verify-phone', methods=['POST'])
def verify_phone():
    """找回密码步骤二：验证手机号是否与用户名匹配"""
    data = request.json
    username = data.get('username', '').strip()
    phone = data.get('phone', '').strip()

    if not username or not phone:
        return jsonify({'error': '用户名和手机号不能为空'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT id, phone FROM users WHERE username = ?',
            (username,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': '该用户名不存在'}), 404

        if not user['phone'] or user['phone'] != phone:
            return jsonify({'error': '手机号与注册时不一致'}), 400

        return jsonify({'match': True, 'message': '手机号验证通过'})

    except Exception as e:
        return jsonify({'error': f'验证失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """找回密码步骤三：通过用户名重置密码"""
    data = request.json
    username = data.get('username', '').strip()
    new_password = data.get('new_password', '')

    if not username or not new_password:
        return jsonify({'error': '用户名和新密码不能为空'}), 400

    if len(new_password) < 6:
        return jsonify({'error': '新密码长度不能少于6位'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        # 通过用户名查找用户
        cursor.execute(
            'SELECT id, username FROM users WHERE username = ?',
            (username,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': '该用户名不存在'}), 404

        # 更新密码
        new_hash = hash_password(new_password)
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (new_hash, user['id'])
        )
        conn.commit()

        return jsonify({
            'success': True,
            'message': '密码重置成功，请使用新密码登录',
            'username': user['username']
        })

    except Exception as e:
        return jsonify({'error': f'重置失败：{str(e)}'}), 500
    finally:
        conn.close()


# ============== 公共服务 ==============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': '服务运行中'})


@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    """获取所有科目及其可用的年级"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有科目和年级的组合
    cursor.execute('''
        SELECT DISTINCT subject, level 
        FROM questions 
        ORDER BY subject, level
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    # 组织数据结构
    subjects = {}
    for row in rows:
        subject = row['subject']
        level = row['level']
        
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append(level)
    
    # 科目名称映射
    subject_names = {
        'math': '数学',
        'chinese': '语文',
        'english': '英语',
        'science': '科学',
        'history': '历史'
    }
    
    # 构建返回数据
    result = {}
    for subject, levels in subjects.items():
        # 统计每个年级的题目数量
        conn = get_db()
        cursor = conn.cursor()
        level_counts = {}
        for level in levels:
            cursor.execute('SELECT COUNT(*) as count FROM questions WHERE subject = ? AND level = ?', (subject, level))
            count = cursor.fetchone()['count']
            level_counts[level] = count
        conn.close()
        
        result[subject] = {
            'name': subject_names.get(subject, subject),
            'levels': sorted(levels),
            'level_counts': level_counts
        }
    
    return jsonify({'subjects': result})

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """获取题目列表
    参数：subject (数学/语文/英语), level (1-3), count (题目数量，默认10，最大50)
    """
    subject = request.args.get('subject', 'math')
    level = request.args.get('level', 1, type=int)
    count = request.args.get('count', 10, type=int)
    # 限制题目数量范围 1~50
    count = max(1, min(count, 50))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取指定科目和级别的题目，随机排序
    cursor.execute('''
        SELECT id, subject, level, type, question, options, answer
        FROM questions
        WHERE subject = ? AND level = ?
        ORDER BY RANDOM()
        LIMIT ?
    ''', (subject, level, count))
    
    rows = cursor.fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        questions.append({
            'id': row['id'],
            'subject': row['subject'],
            'level': row['level'],
            'type': row['type'],
            'question': row['question'],
            'options': json.loads(row['options']) if row['options'] else None,
            'answer': row['answer']
        })
    
    return jsonify({'questions': questions, 'count': len(questions)})


@app.route('/api/user/create', methods=['POST'])
def create_user():
    """创建新用户（快速注册，无需密码）"""
    data = request.json
    student_name = data.get('student_name', '未命名学生')
    
    # 生成随机用户名
    import random
    username = f"user_{random.randint(10000, 99999)}"
    password_hash = hash_password(secrets.token_hex(8))
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash, student_name, last_login)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, student_name, datetime.now().date().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # 生成 Token
        token = generate_token(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': username,
            'token': token,
            'message': '用户创建成功'
        })
    except Exception as e:
        return jsonify({'error': f'创建失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/user/<int:user_id>/change-password', methods=['POST'])
def change_password(user_id):
    """修改密码"""
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': '旧密码和新密码不能为空'}), 400
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度不能少于6位'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404

    # 验证旧密码
    expected_hash = hash_password(old_password)
    if row['password_hash'] != expected_hash:
        conn.close()
        return jsonify({'error': '旧密码不正确'}), 400

    # 更新新密码
    new_hash = hash_password(new_password)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                  (new_hash, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': '密码修改成功'})


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    user = {
        'id': row['id'],
        'username': row['username'],
        'student_name': row['student_name'],
        'avatar': row['avatar'],
        'level': row['level'],
        'total_study_time': row['total_study_time'],  # 总学习时长（秒）
        'created_at': row['created_at'],
        'stats': {
            'totalQuestions': row['total_questions'],
            'correctCount': row['correct_count'],
            'perfectScore': row['perfect_score'],
            'consecutiveDays': row['consecutive_days']
        },
        'last_login': row['last_login']
    }
    
    # 查询已练习过的科目（从答题记录中提取）
    cursor.execute('''
        SELECT DISTINCT subject FROM answer_records
        WHERE user_id = ?
    ''', (user_id,))
    practiced_subjects = [r['subject'] for r in cursor.fetchall() if r['subject']]
    user['practiced_subjects'] = practiced_subjects
    
    conn.close()
    
    return jsonify(user)


@app.route('/api/user/<int:user_id>/update', methods=['POST'])
def update_user(user_id):
    """更新用户统计数据"""
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 更新统计数据
    cursor.execute('''
        UPDATE users SET
            total_questions = ?,
            correct_count = ?,
            perfect_score = ?,
            consecutive_days = ?,
            last_login = ?
        WHERE id = ?
    ''', (
        data.get('total_questions', 0),
        data.get('correct_count', 0),
        data.get('perfect_score', 0),
        data.get('consecutive_days', 1),
        datetime.now().date().isoformat(),
        user_id
    ))
    
    # 计算等级
    total = data.get('total_questions', 0)
    if total < 10:
        level = 1
    elif total < 50:
        level = 2
    elif total < 100:
        level = 3
    elif total < 200:
        level = 4
    else:
        level = 5
    
    cursor.execute('UPDATE users SET level = ? WHERE id = ?', (level, user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'level': level})


@app.route('/api/user/<int:user_id>/avatar', methods=['POST'])
def save_avatar(user_id):
    """保存用户头像"""
    print(f'\n📥 收到头像保存请求: user_id={user_id}')
    
    data = request.json
    print(f'📦 请求数据: {data.keys() if data else None}')
    
    avatar_data = data.get('avatar')
    
    if not avatar_data:
        print('❌ 错误: 缺少头像数据')
        return jsonify({'error': '缺少头像数据'}), 400
    
    print(f'📸 头像数据长度: {len(avatar_data)} 字符')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET avatar = ? WHERE id = ?', (avatar_data, user_id))
        conn.commit()
        print(f'✓ 头像保存成功: user_id={user_id}')
        return jsonify({'success': True, 'message': '头像保存成功'})
    except Exception as e:
        print(f'❌ 保存失败: {str(e)}')
        return jsonify({'error': f'保存失败：{str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/user/<int:user_id>/avatar', methods=['GET'])
def get_avatar(user_id):
    """获取用户头像"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT avatar FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row['avatar']:
        return jsonify({'avatar': row['avatar']})
    else:
        return jsonify({'avatar': None})


@app.route('/api/answer/submit', methods=['POST'])
def submit_answer():
    """提交答题记录"""
    data = request.json
    user_id = data.get('user_id')
    question_id = data.get('question_id')
    subject = data.get('subject')
    user_answer = data.get('user_answer')
    is_correct = data.get('is_correct', False)
    time_spent = data.get('time_spent', 0)  # 答题用时（秒）
    
    if not user_id or not question_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 保存答题记录
    cursor.execute('''
        INSERT INTO answer_records (user_id, question_id, subject, user_answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, question_id, subject, user_answer, 1 if is_correct else 0))
    
    # 更新用户总学习时长
    if time_spent > 0:
        cursor.execute('''
            UPDATE users 
            SET total_study_time = total_study_time + ?
            WHERE id = ?
        ''', (time_spent, user_id))
    
    # 如果答错，加入错题本
    if not is_correct:
        # 检查是否已存在
        cursor.execute('''
            SELECT id, wrong_count FROM wrong_books
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id))
        existing = cursor.fetchone()
        
        if existing:
            # 已存在，增加错误次数
            cursor.execute('''
                UPDATE wrong_books SET
                    wrong_count = wrong_count + 1,
                    last_wrong_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (existing['id'],))
        else:
            # 不存在，新增记录
            cursor.execute('''
                INSERT INTO wrong_books (user_id, question_id, subject)
                VALUES (?, ?, ?)
            ''', (user_id, question_id, subject))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/api/answer/batch-submit', methods=['POST'])
def batch_submit_answers():
    """批量提交答题记录 - 完成全部题目后一次性提交"""
    data = request.json
    user_id = data.get('user_id')
    subject = data.get('subject')
    answers = data.get('answers', [])  # [{question_id, user_answer, is_correct}]
    total_time_spent = data.get('total_time_spent', 0)
    
    if not user_id or not answers:
        return jsonify({'error': '缺少必要参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    for ans in answers:
        question_id = ans.get('question_id')
        user_answer = ans.get('user_answer')
        is_correct = ans.get('is_correct', False)
        
        if not question_id:
            continue
        
        # 保存答题记录
        cursor.execute('''
            INSERT INTO answer_records (user_id, question_id, subject, user_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, question_id, subject, user_answer, 1 if is_correct else 0))
        
        # 如果答错，加入错题本
        if not is_correct:
            cursor.execute('''
                SELECT id, wrong_count FROM wrong_books
                WHERE user_id = ? AND question_id = ?
            ''', (user_id, question_id))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE wrong_books SET
                        wrong_count = wrong_count + 1,
                        last_wrong_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (existing['id'],))
            else:
                cursor.execute('''
                    INSERT INTO wrong_books (user_id, question_id, subject)
                    VALUES (?, ?, ?)
                ''', (user_id, question_id, subject))
    
    # 更新用户总学习时长
    if total_time_spent > 0:
        cursor.execute('''
            UPDATE users 
            SET total_study_time = total_study_time + ?
            WHERE id = ?
        ''', (total_time_spent, user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'count': len(answers)})


@app.route('/api/user/<int:user_id>/wrong-book', methods=['GET'])
def get_wrong_book(user_id):
    """获取用户错题本"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 从答题记录中获取最近的错误答案（使用子查询获取最近一次）
    cursor.execute('''
        SELECT w.id, w.subject, w.wrong_count, w.last_wrong_at,
               q.id as question_id, q.question, q.options, q.answer,
               (
                   SELECT ar.user_answer 
                   FROM answer_records ar 
                   WHERE ar.question_id = w.question_id 
                     AND ar.user_id = w.user_id 
                     AND ar.is_correct = 0
                   ORDER BY ar.answered_at DESC 
                   LIMIT 1
               ) as user_answer
        FROM wrong_books w
        JOIN questions q ON w.question_id = q.id
        WHERE w.user_id = ?
        ORDER BY w.last_wrong_at DESC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    wrong_items = []
    for row in rows:
        wrong_items.append({
            'id': row['id'],
            'subject': row['subject'],
            'question_id': row['question_id'],
            'question': row['question'],
            'options': json.loads(row['options']) if row['options'] else None,
            'correct_answer': row['answer'],
            'user_answer': row['user_answer'],
            'wrong_count': row['wrong_count'],
            'last_wrong_at': row['last_wrong_at']
        })
    
    return jsonify({'wrong_book': wrong_items, 'count': len(wrong_items)})


@app.route('/api/user/<int:user_id>/wrong-book/clear', methods=['POST'])
def clear_wrong_book(user_id):
    """清空用户错题本"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM wrong_books WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/api/user/<int:user_id>/wrong-book/practice', methods=['GET'])
def get_wrong_practice(user_id):
    """从错题本随机抽取题目用于再练习
    参数：count（默认5，最大20），subject（可选，指定学科）
    """
    count = request.args.get('count', 5, type=int)
    count = max(1, min(count, 20))
    subject = request.args.get('subject', None)
    
    conn = get_db()
    cursor = conn.cursor()
    
    if subject:
        cursor.execute('''
            SELECT w.id as wrong_book_id, w.question_id, w.subject,
                   q.question, q.options, q.answer, q.level, q.type
            FROM wrong_books w
            JOIN questions q ON w.question_id = q.id
            WHERE w.user_id = ? AND w.subject = ?
            ORDER BY RANDOM()
            LIMIT ?
        ''', (user_id, subject, count))
    else:
        cursor.execute('''
            SELECT w.id as wrong_book_id, w.question_id, w.subject,
                   q.question, q.options, q.answer, q.level, q.type
            FROM wrong_books w
            JOIN questions q ON w.question_id = q.id
            WHERE w.user_id = ?
            ORDER BY RANDOM()
            LIMIT ?
        ''', (user_id, count))
    
    rows = cursor.fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        questions.append({
            'wrong_book_id': row['wrong_book_id'],
            'question_id': row['question_id'],
            'subject': row['subject'],
            'question': row['question'],
            'options': json.loads(row['options']) if row['options'] else None,
            'answer': row['answer'],
            'level': row['level'],
            'type': row['type']
        })
    
    return jsonify({'questions': questions, 'count': len(questions)})


@app.route('/api/user/<int:user_id>/wrong-book/<int:wrong_id>', methods=['DELETE'])
def delete_wrong_item(user_id, wrong_id):
    """删除单条错题记录（做对后从错题本移除）"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 验证该记录属于该用户
    cursor.execute(
        'SELECT id, question_id FROM wrong_books WHERE id = ? AND user_id = ?',
        (wrong_id, user_id)
    )
    record = cursor.fetchone()
    
    if record:
        cursor.execute('DELETE FROM wrong_books WHERE id = ?', (wrong_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'removed_id': wrong_id})
    else:
        conn.close()
        return jsonify({'success': False, 'error': '记录不存在'}), 404


@app.route('/api/achievements', methods=['GET'])
def get_achievements():
    """获取成就列表"""
    achievements = [
        {'id': 1, 'name': '新手上路', 'desc': '完成第一次答题', 'icon': '🌟'},
        {'id': 2, 'name': '初露锋芒', 'desc': '答对 10 道题', 'icon': '🎯'},
        {'id': 3, 'name': '学习达人', 'desc': '累计答题 50 道', 'icon': '📚'},
        {'id': 4, 'name': '完美主义者', 'desc': '一次练习全对', 'icon': '💯'},
        {'id': 5, 'name': '坚持不懈', 'desc': '连续 7 天学习', 'icon': '🔥'},
        {'id': 6, 'name': '科目精通', 'desc': '三科都练习过', 'icon': '🎓'},
        {'id': 7, 'name': '错题克星', 'desc': '清空错题本', 'icon': '🏆'},
        {'id': 8, 'name': '百题大师', 'desc': '累计答题 100 道', 'icon': '👑'}
    ]
    return jsonify({'achievements': achievements})


@app.route('/api/user/<int:user_id>/achievements', methods=['GET'])
def get_user_achievements(user_id):
    """获取用户已解锁的成就"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT achievement_id, unlocked_at
        FROM user_achievements
        WHERE user_id = ?
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    unlocked = [row['achievement_id'] for row in rows]
    return jsonify({'unlocked_achievements': unlocked})


@app.route('/api/user/<int:user_id>/achievement/unlock', methods=['POST'])
def unlock_achievement(user_id):
    """解锁成就"""
    data = request.json
    achievement_id = data.get('achievement_id')
    
    if not achievement_id:
        return jsonify({'error': '缺少成就 ID'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查是否已解锁
    cursor.execute('''
        SELECT id FROM user_achievements
        WHERE user_id = ? AND achievement_id = ?
    ''', (user_id, achievement_id))
    
    newly_unlocked = False
    if not cursor.fetchone():
        # 未解锁，添加记录
        cursor.execute('''
            INSERT INTO user_achievements (user_id, achievement_id)
            VALUES (?, ?)
        ''', (user_id, achievement_id))
        conn.commit()
        newly_unlocked = True
    
    # 获取成就信息
    achievements = [
        {'id': 1, 'name': '新手上路', 'desc': '完成第一次答题', 'icon': '🌟'},
        {'id': 2, 'name': '初露锋芒', 'desc': '答对 10 道题', 'icon': '🎯'},
        {'id': 3, 'name': '学习达人', 'desc': '累计答题 50 道', 'icon': '📚'},
        {'id': 4, 'name': '完美主义者', 'desc': '一次练习全对', 'icon': '💯'},
        {'id': 5, 'name': '坚持不懈', 'desc': '连续 7 天学习', 'icon': '🔥'},
        {'id': 6, 'name': '科目精通', 'desc': '三科都练习过', 'icon': '🎓'},
        {'id': 7, 'name': '错题克星', 'desc': '清空错题本', 'icon': '🏆'},
        {'id': 8, 'name': '百题大师', 'desc': '累计答题 100 道', 'icon': '👑'}
    ]
    
    achievement = next((a for a in achievements if a['id'] == achievement_id), None)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'newly_unlocked': newly_unlocked,
        'achievement': achievement
    })


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """获取答题排行榜，按答对数量降序排列"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有用户，按答对数量降序排列
    cursor.execute('''
        SELECT 
            id, 
            username, 
            student_name,
            avatar,
            correct_count,
            total_questions,
            level,
            CASE 
                WHEN total_questions > 0 THEN 
                    ROUND(CAST(correct_count AS FLOAT) / total_questions * 100, 1)
                ELSE 0 
            END as accuracy
        FROM users
        WHERE total_questions > 0
        ORDER BY correct_count DESC, total_questions ASC
        LIMIT 50
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    for idx, row in enumerate(rows, 1):
        avatar_data = row['avatar']
        has_avatar = avatar_data is not None and len(avatar_data) > 0
        print(f'用户{idx}: id={row["id"]}, name={row["student_name"] or row["username"]}, 有头像={has_avatar}')
        
        leaderboard.append({
            'rank': idx,
            'id': row['id'],
            'username': row['username'],
            'student_name': row['student_name'],
            'avatar': row['avatar'],
            'correct_count': row['correct_count'],
            'total_questions': row['total_questions'],
            'level': row['level'],
            'accuracy': row['accuracy']
        })
    
    return jsonify({
        'leaderboard': leaderboard,
        'total_users': len(leaderboard)
    })


@app.route('/api/user/<int:user_id>/stats/detail', methods=['GET'])
def get_detailed_stats(user_id):
    """获取用户详细统计数据"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 最近7天每日答题数（补全无答题的日期为0）
    cursor.execute('''
        SELECT DATE(answered_at) as date, COUNT(*) as count
        FROM answer_records
        WHERE user_id = ? AND answered_at >= datetime('now', '-6 days')
        GROUP BY DATE(answered_at)
        ORDER BY date
    ''', (user_id,))
    daily_map = {row['date']: row['count'] for row in cursor.fetchall()}
    daily_stats = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_stats.append({'date': day, 'count': daily_map.get(day, 0)})
    
    # 各科答题数与正确率
    cursor.execute('''
        SELECT subject, 
               COUNT(*) as total,
               SUM(is_correct) as correct
        FROM answer_records
        WHERE user_id = ?
        GROUP BY subject
    ''', (user_id,))
    subject_rows = {row['subject']: dict(row) for row in cursor.fetchall()}
    
    all_subjects = ['math', 'chinese', 'english', 'science', 'history']
    subject_stats = []
    for subject in all_subjects:
        row = subject_rows.get(subject, {'subject': subject, 'total': 0, 'correct': 0})
        total = row.get('total') or 0
        correct = row.get('correct') or 0
        accuracy = round(correct / total * 100, 1) if total > 0 else 0
        subject_stats.append({
            'subject': subject,
            'total': total,
            'correct': correct,
            'accuracy': accuracy
        })
    
    # 汇总正确率
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(is_correct) as correct
        FROM answer_records
        WHERE user_id = ?
    ''', (user_id,))
    summary_row = cursor.fetchone()
    conn.close()
    
    total_all = summary_row['total'] or 0
    correct_all = summary_row['correct'] or 0
    overall_accuracy = round(correct_all / total_all * 100, 1) if total_all > 0 else 0
    
    return jsonify({
        'daily_stats': daily_stats,
        'subject_stats': subject_stats,
        'summary': {
            'total_questions': total_all,
            'correct_count': correct_all,
            'accuracy': overall_accuracy,
            'weekly_total': sum(d['count'] for d in daily_stats)
        }
    })


@app.route('/api/user/<int:user_id>/level-progress', methods=['GET'])
def get_level_progress(user_id):
    """获取用户各科各级别的星星进度"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT q.subject, q.level,
               COUNT(ar.id) as total,
               SUM(ar.is_correct) as correct
        FROM answer_records ar
        JOIN questions q ON ar.question_id = q.id
        WHERE ar.user_id = ?
        GROUP BY q.subject, q.level
        ORDER BY q.subject, q.level
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 构建 progress 结构：{ subject: { level: { stars } } }
    progress = {}
    for row in rows:
        subject = row['subject']
        level = row['level']
        total = row['total'] or 0
        correct = row['correct'] or 0
        
        if total == 0:
            stars = 0
        else:
            accuracy = correct / total
            if accuracy >= 0.8:
                stars = 3
            elif accuracy >= 0.5:
                stars = 2
            else:
                stars = 1
        
        if subject not in progress:
            progress[subject] = {}
        progress[subject][level] = {'stars': stars, 'total': total, 'correct': correct}
    
    return jsonify({'success': True, 'progress': progress})


@app.route('/api/user/<int:user_id>/daily-task', methods=['GET'])
def get_daily_task(user_id):
    """获取用户今日任务"""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 查询今日任务
    cursor.execute('''
        SELECT * FROM daily_tasks 
        WHERE user_id = ? AND task_date = ?
    ''', (user_id, today))
    
    task = cursor.fetchone()
    
    if not task:
        # 创建今日任务
        cursor.execute('''
            INSERT INTO daily_tasks (user_id, task_date, target_questions)
            VALUES (?, ?, 10)
        ''', (user_id, today))
        conn.commit()
        
        task = {
            'id': cursor.lastrowid,
            'target_questions': 10,
            'completed_questions': 0,
            'is_completed': 0
        }
    else:
        task = dict(task)
    
    conn.close()
    return jsonify({'task': task})


@app.route('/api/user/<int:user_id>/daily-task/update', methods=['POST'])
def update_daily_task(user_id):
    """更新每日任务进度"""
    data = request.json
    completed = data.get('completed_questions', 0)
    
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        UPDATE daily_tasks 
        SET completed_questions = ?,
            is_completed = CASE WHEN ? >= target_questions THEN 1 ELSE 0 END
        WHERE user_id = ? AND task_date = ?
    ''', (completed, completed, user_id, today))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/api/answer/today-count', methods=['GET'])
def get_today_answer_count():
    """获取用户今日答题数"""
    user_id = request.args.get('user_id')
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if not user_id:
        return jsonify({'error': '缺少user_id参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM answer_records
        WHERE user_id = ? AND DATE(answered_at) = ?
    ''', (user_id, date))
    
    result = cursor.fetchone()
    conn.close()
    
    return jsonify({'count': result['count']})


# ============== AI 功能 API ==============

@app.route('/api/ai/explain-question', methods=['POST'])
def ai_explain_question():
    """AI解析错题"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    question = data.get('question')
    user_answer = data.get('user_answer')
    correct_answer = data.get('correct_answer')
    subject = data.get('subject')
    
    if not all([user_id, question, user_answer, correct_answer, subject]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查用户是否有可用次数
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ai_usage_count, monthly_ai_quota 
        FROM users WHERE id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    # 检查会员状态
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    # 免费用户限制次数
    if not subscription and user['ai_usage_count'] >= user['monthly_ai_quota']:
        conn.close()
        return jsonify({
            'error': '本月AI解析次数已用完',
            'need_upgrade': True,
            'message': '升级VIP享受无限次AI解析'
        }), 403
    
    try:
        # 调用DeepSeek API
        ai_service = DeepSeekService()
        explanation = ai_service.explain_question(
            question, user_answer, correct_answer, subject
        )
        
        # 记录使用情况
        cursor.execute('''
            UPDATE users SET ai_usage_count = ai_usage_count + 1
            WHERE id = ?
        ''', (user_id,))
        
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'explanation', ?, ?)
        ''', (user_id, len(explanation), 0.01))  # 假设每次0.01元
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'explanation': explanation,
            'remaining_quota': user['monthly_ai_quota'] - user['ai_usage_count'] - 1
        })
        
    except Exception as e:
        conn.close()
        print(f"AI解析错误: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/subscription/check', methods=['GET'])
def check_subscription():
    """检查用户会员状态"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': '缺少user_id参数'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    conn.close()
    
    if subscription:
        return jsonify({
            'is_vip': True,
            'type': subscription['subscription_type'],
            'end_date': subscription['end_date']
        })
    else:
        return jsonify({'is_vip': False})


@app.route('/api/subscription/create', methods=['POST'])
def create_subscription():
    """创建会员订单（模拟支付）"""
    data = request.json
    user_id = data.get('user_id')
    subscription_type = data.get('type')  # 'monthly' or 'yearly'
    
    if not user_id or not subscription_type:
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 计算价格
    prices = {
        'monthly': 1.0,
        'yearly': 10.0
    }
    
    price = prices.get(subscription_type, 0)
    
    # 这里应该集成真实的支付接口（微信/支付宝）
    # 现在先模拟支付成功
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 计算到期时间
    if subscription_type == 'monthly':
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    else:
        end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 更新或插入会员信息
    cursor.execute('''
        INSERT OR REPLACE INTO user_subscriptions 
        (user_id, subscription_type, start_date, end_date, is_active)
        VALUES (?, ?, date('now'), ?, 1)
    ''', (user_id, f'vip_{subscription_type}', end_date))
    
    # 更新用户的AI配额
    cursor.execute('''
        UPDATE users SET monthly_ai_quota = 9999
        WHERE id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '开通成功',
        'end_date': end_date,
        'type': f'vip_{subscription_type}'
    })


@app.route('/api/ai/generate-study-plan', methods=['POST'])
def generate_study_plan():
    """生成今日学习计划"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': '缺少user_id参数'}), 400
    
    # 获取用户统计数据
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT total_questions, correct_count, consecutive_days 
        FROM users WHERE id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    # 获取薄弱知识点（从错题本统计）
    cursor.execute('''
        SELECT subject, COUNT(*) as count
        FROM wrong_books
        WHERE user_id = ?
        GROUP BY subject
        ORDER BY count DESC
        LIMIT 3
    ''', (user_id,))
    
    weak_points = [row['subject'] for row in cursor.fetchall()]
    
    # 获取近期表现
    cursor.execute('''
        SELECT subject, COUNT(*) as total, SUM(is_correct) as correct
        FROM answer_records
        WHERE user_id = ? AND answered_at >= datetime('now', '-7 days')
        GROUP BY subject
    ''', (user_id,))
    
    recent_performance = ""
    for row in cursor.fetchall():
        accuracy = (row['correct'] / row['total'] * 100) if row['total'] > 0 else 0
        recent_performance += f"- {row['subject']}: {row['total']}题，正确率{accuracy:.1f}%\n"
    
    if not recent_performance:
        recent_performance = "最近7天暂无答题记录"
    
    conn.close()
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    conn.close()
    
    if not subscription:
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        # 调用AI生成计划
        ai_service = DeepSeekService()
        plan = ai_service.generate_study_plan(
            {
                'total_questions': user['total_questions'],
                'accuracy': (user['correct_count'] / user['total_questions'] * 100) 
                           if user['total_questions'] > 0 else 0,
                'consecutive_days': user['consecutive_days']
            },
            weak_points,
            recent_performance
        )
        
        # 保存计划到数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO study_plans (user_id, plan_date, plan_content)
            VALUES (?, date('now'), ?)
        ''', (user_id, plan))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'plan': plan})
        
    except Exception as e:
        conn.close()
        print(f"生成学习计划失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/generate-learning-report', methods=['POST'])
def generate_learning_report():
    """生成周度学习报告"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': '缺少user_id参数'}), 400
    
    # 获取本周数据
    conn = get_db()
    cursor = conn.cursor()
    
    # 本周答题总数和正确率
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(is_correct) as correct
        FROM answer_records
        WHERE user_id = ? AND answered_at >= datetime('now', '-7 days')
    ''', (user_id,))
    
    result = cursor.fetchone()
    total_questions = result['total'] if result else 0
    correct_count = result['correct'] if result else 0
    accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # 学习时长
    cursor.execute('SELECT total_study_time FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    study_time = user['total_study_time'] // 60 if user and user['total_study_time'] else 0  # 转换为分钟
    
    # 活跃天数
    cursor.execute('''
        SELECT COUNT(DISTINCT DATE(answered_at)) as days
        FROM answer_records
        WHERE user_id = ? AND answered_at >= datetime('now', '-7 days')
    ''', (user_id,))
    
    active_days = cursor.fetchone()['days']
    
    # 各科表现
    cursor.execute('''
        SELECT subject, COUNT(*) as total, SUM(is_correct) as correct
        FROM answer_records
        WHERE user_id = ? AND answered_at >= datetime('now', '-7 days')
        GROUP BY subject
    ''', (user_id,))
    
    subject_performance = ""
    for row in cursor.fetchall():
        acc = (row['correct'] / row['total'] * 100) if row['total'] > 0 else 0
        subject_performance += f"- {row['subject']}: {row['total']}题，正确率{acc:.1f}%\n"
    
    if not subject_performance:
        subject_performance = "本周暂无答题记录"
    
    conn.close()
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    conn.close()
    
    if not subscription:
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        # 调用AI生成报告
        ai_service = DeepSeekService()
        report = ai_service.generate_learning_report({
            'total_questions': total_questions,
            'accuracy': accuracy,
            'study_time': study_time,
            'active_days': active_days,
            'subject_performance': subject_performance,
            'improvement': '数据收集中...'
        })
        
        return jsonify({'success': True, 'report': report})
        
    except Exception as e:
        print(f"生成学习报告失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/correct-essay', methods=['POST'])
def ai_correct_essay():
    """AI作文批改"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    essay_text = data.get('essay_text')
    grade_level = data.get('grade_level', 3)
    essay_type = data.get('essay_type', 'narrative')
    
    if not all([user_id, essay_text]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    if not subscription:
        conn.close()
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        ai_service = DeepSeekService()
        correction = ai_service.correct_essay(essay_text, grade_level, essay_type)
        
        # 记录使用情况
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'essay_correction', ?, ?)
        ''', (user_id, len(correction), 0.02))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'correction': correction})
        
    except Exception as e:
        conn.close()
        print(f"作文批改失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/practice-speaking', methods=['POST'])
def ai_practice_speaking():
    """AI口语练习"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    topic = data.get('topic')
    difficulty = data.get('difficulty', 'medium')
    language = data.get('language', 'english')
    
    if not all([user_id, topic]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    if not subscription:
        conn.close()
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        ai_service = DeepSeekService()
        practice = ai_service.practice_speaking(topic, difficulty, language)
        
        # 记录使用情况
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'speaking_practice', ?, ?)
        ''', (user_id, len(practice), 0.02))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'practice': practice})
        
    except Exception as e:
        conn.close()
        print(f"口语练习生成失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/recommend-questions', methods=['POST'])
def ai_recommend_questions():
    """AI智能推荐题目"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    weak_points = data.get('weak_points', [])
    preferred_subjects = data.get('preferred_subjects', [])
    
    if not user_id:
        return jsonify({'error': '缺少user_id参数'}), 400
    
    # 获取用户统计数据
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_questions, correct_count, level FROM users WHERE id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    try:
        ai_service = DeepSeekService()
        recommendations = ai_service.recommend_questions(
            {
                'total_questions': user['total_questions'],
                'accuracy': (user['correct_count'] / user['total_questions'] * 100) 
                           if user['total_questions'] > 0 else 0,
                'level': user['level']
            },
            weak_points,
            preferred_subjects
        )
        
        conn.close()
        
        return jsonify({'success': True, 'recommendations': recommendations})
        
    except Exception as e:
        conn.close()
        print(f"题目推荐失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/knowledge-graph', methods=['POST'])
def ai_knowledge_graph():
    """AI生成知识点图谱"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    subject = data.get('subject')
    topics = data.get('topics', [])
    
    if not all([user_id, subject, topics]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    if not subscription:
        conn.close()
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        ai_service = DeepSeekService()
        graph = ai_service.generate_knowledge_graph(subject, topics)
        
        # 记录使用情况
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'knowledge_graph', ?, ?)
        ''', (user_id, len(graph), 0.02))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'knowledge_graph': graph})
        
    except Exception as e:
        conn.close()
        print(f"知识图谱生成失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI学习伙伴（智能问答）"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    conversation_history = data.get('history', [])
    context = data.get('context', 'learning')
    
    if not all([user_id, message]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 免费用户限制次数
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ai_usage_count, monthly_ai_quota FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    # 检查会员状态
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    # 免费用户限制次数
    if not subscription and user['ai_usage_count'] >= user['monthly_ai_quota']:
        conn.close()
        return jsonify({
            'error': '本月AI使用次数已用完',
            'need_upgrade': True
        }), 403
    
    try:
        ai_service = DeepSeekService()
        reply = ai_service.chat_with_ai(message, conversation_history, context)
        
        # 记录使用情况
        cursor.execute('''
            UPDATE users SET ai_usage_count = ai_usage_count + 1 WHERE id = ?
        ''', (user_id,))
        
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'chat', ?, ?)
        ''', (user_id, len(reply), 0.01))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'reply': reply})
        
    except Exception as e:
        conn.close()
        print(f"AI对话失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


@app.route('/api/ai/generate-questions', methods=['POST'])
def ai_generate_questions():
    """AI自动生成练习题"""
    from ai_service import DeepSeekService
    
    data = request.json
    user_id = data.get('user_id')
    subject = data.get('subject')
    topic = data.get('topic')
    difficulty = data.get('difficulty', 2)
    count = data.get('count', 5)
    
    if not all([user_id, subject, topic]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查会员状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date >= date('now')
    ''', (user_id,))
    
    subscription = cursor.fetchone()
    
    if not subscription:
        conn.close()
        return jsonify({
            'error': '此功能仅限VIP会员使用',
            'need_upgrade': True
        }), 403
    
    try:
        ai_service = DeepSeekService()
        questions = ai_service.generate_practice_questions(subject, topic, difficulty, count)
        
        # 记录使用情况
        cursor.execute('''
            INSERT INTO ai_usage_records (user_id, usage_type, tokens_used, cost)
            VALUES (?, 'generate_questions', ?, ?)
        ''', (user_id, len(questions), 0.02))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'questions': questions})
        
    except Exception as e:
        conn.close()
        print(f"题目生成失败: {str(e)}")
        return jsonify({'error': f'AI服务异常: {str(e)}'}), 500


# ============== 启动服务 ==============

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动 Flask 服务
    print("\n🚀 小学刷题乐园后端服务启动中...")
    print("📡 API 地址：http://localhost:5000")
    print("📚 接口文档：http://localhost:5000/api/health\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
