import streamlit as st
import random
import time
import sqlite3
import os
import datetime

# ===================== 数据库初始化 =====================
DB_FILE = "game_scores.db"

def init_database():
    """初始化数据库，创建成绩表、背包表和用户表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建用户表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建成绩表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            time_seconds REAL NOT NULL,
            difficulty TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查是否存在gave_up字段，如果不存在则添加
    cursor.execute("PRAGMA table_info(scores)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'gave_up' not in columns:
        cursor.execute(
            "ALTER TABLE scores ADD COLUMN gave_up INTEGER DEFAULT 0"
        )
    
    # 创建背包表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backpack (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nickname, item_type, item_name)
        )
    ''')
    
    # 创建邮件表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            coins INTEGER NOT NULL DEFAULT 0,
            is_read INTEGER NOT NULL DEFAULT 0,
            is_claimed INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建奖池表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prize_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            is_settled INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_score(nickname, time_seconds, difficulty, attempts, gave_up=0):
    """保存玩家成绩到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scores (nickname, time_seconds, difficulty, attempts, gave_up) VALUES (?, ?, ?, ?, ?)",
        (nickname, time_seconds, difficulty, attempts, gave_up)
    )
    conn.commit()
    conn.close()

def get_leaderboard(difficulty=None, limit=10, today_only=True):
    """获取排行榜数据，先按猜测次数由低到高，再按花费时间由低到高"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 获取今天的日期（YYYY-MM-DD格式）
    import datetime
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    if difficulty:
        if today_only:
            # 只显示今天的数据，且没有弃权
            cursor.execute(
                "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE difficulty = ? AND date(timestamp) = ? AND gave_up = 0 ORDER BY attempts ASC, time_seconds ASC LIMIT ?",
                (difficulty, today, limit)
            )
        else:
            # 显示所有数据，且没有弃权
            cursor.execute(
                "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE difficulty = ? AND gave_up = 0 ORDER BY attempts ASC, time_seconds ASC LIMIT ?",
                (difficulty, limit)
            )
    else:
        if today_only:
            # 只显示今天的数据，且没有弃权
            cursor.execute(
                "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE date(timestamp) = ? AND gave_up = 0 ORDER BY attempts ASC, time_seconds ASC LIMIT ?",
                (today, limit)
            )
        else:
            # 显示所有数据，且没有弃权
            cursor.execute(
                "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE gave_up = 0 ORDER BY attempts ASC, time_seconds ASC LIMIT ?",
                (limit,)
            )
    results = cursor.fetchall()
    conn.close()
    return results

def update_digital_coins(username, amount, reason="游戏奖励"):
    """更新玩家的数字币数量"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 检查玩家是否已有数字币记录
    cursor.execute(
        "SELECT quantity FROM backpack WHERE nickname = ? AND item_type = 'currency' AND item_name = '数字币'",
        (username,)
    )
    result = cursor.fetchone()
    
    if result:
        # 更新现有记录
        new_quantity = max(0, result[0] + amount)  # 确保数量不为负数
        cursor.execute(
            "UPDATE backpack SET quantity = ?, last_updated = CURRENT_TIMESTAMP WHERE nickname = ? AND item_type = 'currency' AND item_name = '数字币'",
            (new_quantity, username)
        )
    else:
        # 创建新记录
        new_quantity = max(0, amount)  # 确保数量不为负数
        cursor.execute(
            "INSERT INTO backpack (nickname, item_type, item_name, quantity) VALUES (?, ?, ?, ?)",
            (username, 'currency', '数字币', new_quantity)
        )
    
    # 记录数字币变动
    cursor.execute(
        "INSERT INTO coin_history (username, amount, reason) VALUES (?, ?, ?)",
        (username, amount, reason)
    )
    
    conn.commit()
    conn.close()

def get_digital_coins(nickname):
    """获取玩家的数字币数量"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT quantity FROM backpack WHERE nickname = ? AND item_type = 'currency' AND item_name = '数字币'",
        (nickname,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

def register_user(username, password):
    """注册新用户"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 用户名已存在
        return False
    finally:
        conn.close()

def verify_user(username, password):
    """验证用户登录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT password FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0] == password
    return False

def user_exists(username):
    """检查用户是否存在"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def get_game_history():
    """获取所有游戏历史记录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT nickname, time_seconds, difficulty, attempts, gave_up, timestamp FROM scores ORDER BY timestamp DESC"
    )
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_all_users():
    """获取所有用户信息"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT username, password, created_at FROM users"
    )
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_coin_history():
    """获取数字币变动记录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 这里需要创建一个数字币变动记录表
    # 先检查表是否存在
    cursor.execute("PRAGMA table_info(coin_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'id' not in columns:
        # 创建数字币变动记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    
    # 获取数字币变动记录
    cursor.execute(
        "SELECT username, amount, reason, timestamp FROM coin_history ORDER BY timestamp DESC"
    )
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_daily_leaderboard(date):
    """获取指定日期的排行榜记录"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE date(timestamp) = ? AND gave_up = 0 ORDER BY attempts ASC, time_seconds ASC",
        (date,)
    )
    results = cursor.fetchall()
    conn.close()
    
    return results

def send_email(recipient, title, content, coins=0):
    """发送邮件"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO emails (recipient, title, content, coins) VALUES (?, ?, ?, ?)",
        (recipient, title, content, coins)
    )
    
    conn.commit()
    conn.close()

def get_user_emails(username):
    """获取用户的邮件"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, title, content, coins, is_read, is_claimed, sent_at FROM emails WHERE recipient = ? AND is_deleted = 0 ORDER BY sent_at DESC",
        (username,)
    )
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_unread_email_count(username):
    """获取用户未读邮件数量"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM emails WHERE recipient = ? AND is_read = 0 AND is_deleted = 0",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

def mark_email_as_read(email_id):
    """标记邮件为已读"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE emails SET is_read = 1 WHERE id = ?",
        (email_id,)
    )
    
    conn.commit()
    conn.close()

def claim_email_coins(email_id, username):
    """领取邮件中的数字币"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 获取邮件信息
    cursor.execute(
        "SELECT coins FROM emails WHERE id = ? AND recipient = ? AND is_claimed = 0 AND is_deleted = 0",
        (email_id, username)
    )
    result = cursor.fetchone()
    
    if result:
        coins = result[0]
        if coins > 0:
            # 发放数字币
            update_digital_coins(username, coins, "邮件领取")
            # 标记为已领取
            cursor.execute(
                "UPDATE emails SET is_claimed = 1 WHERE id = ?",
                (email_id,)
            )
            conn.commit()
            conn.close()
            return True
    
    conn.close()
    return False

def delete_email(email_id, username):
    """删除邮件"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE emails SET is_deleted = 1 WHERE id = ? AND recipient = ?",
        (email_id, username)
    )
    
    conn.commit()
    conn.close()

def get_today_prize_pool():
    """获取今日奖池金额"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 检查今日奖池是否存在
    cursor.execute(
        "SELECT amount FROM prize_pool WHERE date = ? AND is_settled = 0",
        (today,)
    )
    result = cursor.fetchone()
    
    if result:
        amount = result[0]
    else:
        # 创建今日奖池
        cursor.execute(
            "INSERT INTO prize_pool (date, amount) VALUES (?, ?)",
            (today, 0)
        )
        conn.commit()
        amount = 0
    
    conn.close()
    return amount

def update_prize_pool(amount):
    """更新奖池金额"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 检查今日奖池是否存在
    cursor.execute(
        "SELECT id FROM prize_pool WHERE date = ? AND is_settled = 0",
        (today,)
    )
    result = cursor.fetchone()
    
    if result:
        # 更新现有奖池
        cursor.execute(
            "UPDATE prize_pool SET amount = amount + ? WHERE id = ?",
            (amount, result[0])
        )
    else:
        # 创建今日奖池
        cursor.execute(
            "INSERT INTO prize_pool (date, amount) VALUES (?, ?)",
            (today, amount)
        )
    
    conn.commit()
    conn.close()

def settle_daily_prize_pool():
    """每日结算奖池"""
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 检查昨日奖池是否存在且未结算
    cursor.execute(
        "SELECT id, amount FROM prize_pool WHERE date = ? AND is_settled = 0",
        (yesterday,)
    )
    result = cursor.fetchone()
    
    if result:
        pool_id, pool_amount = result
        
        # 获取昨日各个模式的排行榜冠军
        champions = []
        difficulties = ['easy', 'medium', 'hard']
        
        for difficulty in difficulties:
            # 获取该模式的最佳成绩
            cursor.execute(
                "SELECT nickname, MIN(attempts), MIN(time_seconds) FROM scores WHERE date(sent_at) = ? AND difficulty = ? AND gave_up = 0 GROUP BY nickname ORDER BY attempts ASC, time_seconds ASC LIMIT 1",
                (yesterday, difficulty)
            )
            champion = cursor.fetchone()
            if champion:
                champions.append(champion[0])
        
        # 去重，同一个账户可能获得多个模式的冠军
        unique_champions = list(set(champions))
        champion_count = len(unique_champions)
        
        if champion_count > 0:
            # 计算每个冠军的奖励
            reward_per_champion = pool_amount // champion_count
            remaining = pool_amount % champion_count
            
            # 给每个冠军发送邮件
            for champion in unique_champions:
                send_email(
                    champion,
                    "排行榜奖励",
                    f"恭喜您昨日获得排行榜第一名！请查收昨日奖池奖励",
                    reward_per_champion
                )
            
            # 标记昨日奖池为已结算
            cursor.execute(
                "UPDATE prize_pool SET is_settled = 1 WHERE id = ?",
                (pool_id,)
            )
            
            # 如果有剩余，添加到今日奖池
            if remaining > 0:
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                # 检查今日奖池是否存在
                cursor.execute(
                    "SELECT id FROM prize_pool WHERE date = ? AND is_settled = 0",
                    (today,)
                )
                today_pool = cursor.fetchone()
                if today_pool:
                    cursor.execute(
                        "UPDATE prize_pool SET amount = amount + ? WHERE id = ?",
                        (remaining, today_pool[0])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO prize_pool (date, amount) VALUES (?, ?)",
                        (today, remaining)
                    )
        
        conn.commit()
    
    conn.close()

# 初始化数据库
init_database()

# 检查是否需要执行每日结算
# 这里简化处理，每次应用启动时检查
settle_daily_prize_pool()

# ===================== 初始化会话状态 - 增强版 =====================
if 'game_mode' not in st.session_state:
    st.session_state.game_mode = None
if 'show_leaderboard' not in st.session_state:
    st.session_state.show_leaderboard = False
if 'nickname' not in st.session_state:
    st.session_state.nickname = ""
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'difficulty' not in st.session_state:
    st.session_state.difficulty = None
if 'length' not in st.session_state:
    st.session_state.length = 4
if 'secret' not in st.session_state:
    st.session_state.secret = None
if 'attempts' not in st.session_state:
    st.session_state.attempts = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'game_over' not in st.session_state:
    st.session_state.game_over = False
if 'guess_input' not in st.session_state:
    st.session_state.guess_input = ""
if 'create_guess_input' not in st.session_state:
    st.session_state.create_guess_input = ""
# 比大小游戏状态变量
if 'dice_values' not in st.session_state:
    st.session_state.dice_values = []
if 'player_choice' not in st.session_state:
    st.session_state.player_choice = None
if 'show_dice' not in st.session_state:
    st.session_state.show_dice = False
if 'dice_animation' not in st.session_state:
    st.session_state.dice_animation = False
# 弃权确认状态
if 'abandon_confirm' not in st.session_state:
    st.session_state.abandon_confirm = False
# 登录状态
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'show_abandon_confirm' not in st.session_state:
    st.session_state.show_abandon_confirm = False
if 'abandon_result' not in st.session_state:
    st.session_state.abandon_result = None
# 新增：猜中刷新专用状态
if 'win_refresh' not in st.session_state:
    st.session_state.win_refresh = False
if 'win_info' not in st.session_state:
    st.session_state.win_info = None
if 'page' not in st.session_state:
    st.session_state.page = None

# ===================== 核心函数 =====================
def generate_secret(length=4):
    """生成随机的不重复数字"""
    digits = list('0123456789')
    random.shuffle(digits)
    return ''.join(digits[:length])

def calculate_AB(secret, guess):
    """计算A和B的数量"""
    a_count = sum(1 for s, g in zip(secret, guess) if s == g)
    common = set(secret) & set(guess)
    b_count = sum(min(secret.count(c), guess.count(c)) for c in common) - a_count
    return a_count, b_count

# ===================== 辅助函数：重置游戏状态（核心修复） =====================
def reset_game_state(reset_nickname=True):
    """重置游戏过程状态（不重置难度/长度/秘钥，避免清空已选难度）"""
    st.session_state.attempts = 0
    st.session_state.history = []
    st.session_state.game_over = False
    st.session_state.guess_input = ""
    st.session_state.create_guess_input = ""
    st.session_state.abandon_confirm = False
    # 重置比大小游戏状态
    st.session_state.dice_values = []
    st.session_state.player_choice = None
    st.session_state.show_dice = False
    st.session_state.dice_animation = False
    st.session_state.show_abandon_confirm = False
    st.session_state.abandon_result = None  # 重置弃权结果
    if reset_nickname:
        st.session_state.nickname = ""
        st.session_state.start_time = None
        st.session_state.difficulty = None
        st.session_state.secret = None
        st.session_state.length = 4

# ===================== 主应用 =====================
def main():
    # 自定义CSS：100%还原原字体+按钮黑色文字+烟花动画完整
    st.markdown('''
    <style>
    /* 背景图片 - 原版不变 */
    .stApp {
        background-image: url('https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=minimalist%20black%20and%20white%20background%2C%20gradient%20chessboard%20pattern%2C%20number%20grid%2C%20solid%20lines%20in%20top%20right%20corner%2C%20fading%20lines%20towards%20bottom%20left%2C%20pure%20white%20at%20bottom%20left%2C%20clean%20design&image_size=landscape_16_9');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }

    /* 标题样式 - 还原原版字体+样式 */
    .stTitle {
        color: #FFFFFF !important;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        font-size: 36px !important;
        font-weight: bold;
    }

    /* 副标题样式 - 还原原版字体+样式 */
    .stHeading {
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }
    .stHeading h2 {
        color: #FFFFFF !important;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }

    /* 主按钮样式 - 黑色文字+还原原版字体+原版样式 */
    .stButton > button {
        background: white !important;
        color: #000000 !important; /* 纯黑色文字 */
        border: 3px solid #9E9E9E;
        border-radius: 25px !important;
        padding: 12px 24px;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 20px;
        font-weight: bold;
        font-stretch: expanded;
        text-shadow: none !important;
        box-shadow: 4px 4px 0px #9E9E9E, 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        cursor: pointer;
        --text-color: #000000 !important; /* 强制继承黑色 */
    }
    .stButton > button:hover {
        background: #f0f0f0 !important;
        color: #000000 !important;
        border: 3px solid #E0E0E0;
        box-shadow: 4px 4px 0px #E0E0E0, 0 6px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-3px) scale(1.05);
        text-shadow: none !important;
    }
    .stButton > button:active {
        transform: translateY(1px);
        box-shadow: 2px 2px 0px #E0E0E0;
        color: #000000 !important;
    }
    /* 强制按钮内所有文字黑色（覆盖全局p标签）- 核心修复 */
    .stButton > button * {
        color: #000000 !important;
        text-shadow: none !important;
        background-color: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 0 !important;
    }



    /* 登出按钮样式 - 与用户名一致大小和灰色 */
    .logout-button-container .stButton {
        width: auto !important;
        min-width: 0 !important;
        display: inline-block !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .logout-button-container .stButton > button {
        background: transparent !important;
        color: #CCCCCC !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 2px 6px !important;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 14px !important;
        font-weight: normal !important;
        box-shadow: none !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5) !important;
        text-decoration: underline !important;
        cursor: pointer !important;
        margin: 0 !important;
        min-height: 20px !important;
        height: 20px !important;
        line-height: 1 !important;
        width: auto !important;
        display: inline-block !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }
    .logout-button-container .stButton > button:hover {
        color: #FFFFFF !important;
        text-decoration: none !important;
        background: rgba(255, 255, 255, 0.1) !important;
    }
    /* 确保按钮内部元素也正确显示 */
    .logout-button-container .stButton > button * {
        color: #CCCCCC !important;
        font-size: 14px !important;
        font-weight: normal !important;
        text-decoration: underline !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        box-shadow: none !important;
    }
    .logout-button-container .stButton > button:hover * {
        color: #FFFFFF !important;
        text-decoration: none !important;
    }

    /* 文本输入框样式 - 还原原版字体+样式 */
    .stTextInput > div > div > input {
        border: 2px solid #9E9E9E;
        border-radius: 15px;
        padding: 10px;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 16px;
        background-color: rgba(255, 255, 255, 0.9);
    }

    /* 文本内容样式 - 还原原版字体+样式 */
    .stWrite {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 5px 10px;
        border-radius: 10px;
        display: inline-block;
        margin: 2px 0;
    }
    
    /* 所有div元素的通用样式，确保字体清晰可见 */
    div {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8) !important;
    }

    /* 段落样式 - 还原原版字体+样式 */
    p {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 5px 10px;
        border-radius: 10px;
        display: inline-block;
        margin: 2px 0;
    }

    /* 列表项样式 - 还原原版字体+样式 */
    ul {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 16px;
    }
    li {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif; /* 还原原版字体 */
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 5px 10px;
        border-radius: 10px;
        margin: 5px 0;
        display: inline-block;
    }

    /* 成功/错误消息样式 - 原版不变 */
    .stSuccess {
        background-color: rgba(6, 214, 160, 0.2);
        border-radius: 15px;
        border: 2px solid #06D6A0;
        padding: 10px;
    }
    .stError {
        background-color: rgba(255, 87, 34, 0.2);
        border-radius: 15px;
        border: 2px solid #FF5722;
        padding: 10px;
    }

    /* 烟花动画+恭喜文字 - 完整保留，确保生效 */
    @keyframes fireworks {
        0% {
            transform: scale(0);
            opacity: 1;
        }
        100% {
            transform: scale(1);
            opacity: 0;
        }
    }
    .firework {
        position: absolute;
        width: 10px;
        height: 10px;
        background: radial-gradient(circle, #ff0 0%, #ff8c00 25%, #ff0000 50%, #8b00ff 75%, #00f 100%);
        border-radius: 50%;
        animation: fireworks 1s ease-out forwards;
        z-index: 1000;
    }
    .congratulation {
        font-size: 36px;
        font-weight: bold;
        color: #ffffff;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        animation: pulse 1s ease-in-out infinite alternate;
        text-align: center;
        margin: 20px 0;
    }
    @keyframes pulse {
        0% {
            transform: scale(1);
        }
        100% {
            transform: scale(1.1);
        }
    }
    
    /* 数字币样式和动画 */
    .digital-coin {
        display: inline-block;
        width: 30px;
        height: 30px;
        background: radial-gradient(circle, #ffd700 0%, #ffed4e 50%, #ffd700 100%);
        border-radius: 50%;
        text-align: center;
        line-height: 30px;
        font-weight: bold;
        color: #333;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        margin: 0 5px;
    }
    
    /* 数字币飞入口袋动画 */
    @keyframes coin-fly {
        0% {
            transform: scale(1) translate(0, 0);
            opacity: 1;
        }
        100% {
            transform: scale(0.5) translate(100px, -100px);
            opacity: 0;
        }
    }
    
    .coin-animation {
        animation: coin-fly 1s ease-out forwards;
    }
    </style>
    
    <script>
    function createFireworks() {
        const container = document.querySelector('.stApp');
        for (let i = 0; i < 50; i++) {
            setTimeout(() => {
                const firework = document.createElement('div');
                firework.className = 'firework';
                firework.style.left = Math.random() * 100 + '%';
                firework.style.top = Math.random() * 100 + '%';
                firework.style.animationDelay = Math.random() * 0.5 + 's';
                container.appendChild(firework);
                
                setTimeout(() => {
                    firework.remove();
                }, 1000);
            }, i * 100);
        }
    }


    </script>
    ''', unsafe_allow_html=True)

    # 登录界面
    if not st.session_state.logged_in:
        with st.container():
            st.title("用户登录")
            st.write("请输入账号和密码进行登录或注册")
            
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("登录"):
                    if user_exists(username):
                        if verify_user(username, password):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("密码错误，请重新输入")
                    else:
                        st.error("账号不存在")
            with col2:
                if st.button("注册"):
                    if username and password:
                        if register_user(username, password):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("账号已存在，请选择其他账号")
                    else:
                        st.error("请输入账号和密码")
        return
    
    # 顶部布局：标题、用户信息、数字币和邮件
    col_title, col_user = st.columns([3, 1])
    with col_title:
        st.title("数字迷宫")
    with col_user:
        # 显示用户信息和邮件按钮
        unread_count = get_unread_email_count(st.session_state.username)
        # 使用更简单的HTML结构，确保没有多余的标签
        # 构建邮件按钮HTML
        # 构建邮件按钮HTML
        unread_html = ''
        if unread_count > 0:
            unread_html = f'<span style="position: absolute; top: -8px; right: -8px; background-color: red; color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 12px; display: flex; align-items: center; justify-content: center;">{unread_count}</span>'
        
        # 构建完整的HTML，使用单行字符串避免渲染问题
        email_button_html = '<div style="width: 100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">' \
                          '<span style="color: #FFFFFF; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); font-weight: bold; font-size: 16px;">👤 ' + st.session_state.username + '</span>' \
                          '<div id="email_button" style="color: #FFFFFF; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); text-decoration: none; cursor: pointer; position: relative; display: inline-block;">' \
                          '<span style="font-size: 20px;">Mail</span>' + unread_html + '</div>' \
                          '</div>'
        st.markdown(email_button_html, unsafe_allow_html=True)
        
        # 数字币显示
        coins = get_digital_coins(st.session_state.username)
        st.markdown(f'<div style="text-align: right; clear: both; margin-top: 5px;"><span style="color: #FFFFFF; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); font-weight: bold;">💰 {coins}</span></div>', unsafe_allow_html=True)
    
    # 邮件界面
    if 'email_box_visible' not in st.session_state:
        st.session_state.email_box_visible = False
    
    # 邮件按钮点击事件
    if st.session_state.email_box_visible:
        with st.container():
            st.header("📧 邮件箱")
            
            # 获取用户邮件
            emails = get_user_emails(st.session_state.username)
            
            if emails:
                for email in emails:
                    email_id, title, content, coins, is_read, is_claimed, sent_at = email
                    
                    # 邮件卡片
                    with st.expander(f"{'📩 ' if not is_read else '📨 '}{title} - {sent_at}"):
                        # 标记为已读
                        if not is_read:
                            mark_email_as_read(email_id)
                        
                        # 显示邮件内容
                        st.write(content)
                        
                        # 显示数字币
                        if coins > 0:
                            if not is_claimed:
                                if st.button(f"领取 {coins} 数字币", key=f"claim_{email_id}"):
                                    if claim_email_coins(email_id, st.session_state.username):
                                        st.success(f"成功领取 {coins} 数字币")
                                        st.rerun()
                                    else:
                                        st.error("领取失败，请稍后重试")
                            else:
                                st.info(f"已领取 {coins} 数字币")
                        
                        # 删除邮件
                        if st.button("删除邮件", key=f"delete_{email_id}"):
                            delete_email(email_id, st.session_state.username)
                            st.success("邮件已删除")
                            st.rerun()
            else:
                st.write("暂无邮件")
            
            # 返回主菜单
            if st.button("返回主菜单"):
                st.session_state.email_box_visible = False
                st.rerun()
        return
    
    # 添加邮件按钮点击事件的JavaScript
    st.markdown('''
    <script>
    document.getElementById('email_button').addEventListener('click', function(e) {
        // 找到并点击隐藏的邮件按钮
        const emailButton = document.querySelector('button[data-testid="stButton-email_button_trigger"]');
        if (emailButton) {
            emailButton.click();
        }
    });
    </script>
    ''', unsafe_allow_html=True)
    
    # 邮件按钮（使用普通按钮，通过CSS隐藏）
    if st.button("显示邮件", key="email_button_trigger"):
        st.session_state.email_box_visible = True
        st.rerun()
    
    # 隐藏邮件按钮的CSS
    st.markdown('''
    <style>
    button[data-testid="stButton-email_button_trigger"] {
        display: none !important;
    }
    </style>
    ''', unsafe_allow_html=True)
    
    # ===================== 后台管理页面 =====================
    if st.session_state.page == "admin":
        # 权限检查
        if st.session_state.username != "admin":
            st.error("您没有权限访问后台管理页面")
            if st.button("🏠 返回主菜单"):
                st.session_state.page = None
                st.rerun()
            return
        
        with st.container():
            st.header("🔧 后台管理")
            
            # 后台导航
            admin_tabs = st.tabs(["游戏历史", "账号信息", "数字币记录", "邮件发送", "每日排行榜"])
            
            # 1. 游戏历史记录
            with admin_tabs[0]:
                st.subheader("游戏历史记录")
                
                # 获取游戏历史记录
                game_history = get_game_history()
                
                if game_history:
                    # 显示游戏历史记录
                    for record in game_history:
                        nickname, time_seconds, difficulty, attempts, gave_up, timestamp = record
                        
                        # 格式化时间
                        if time_seconds < 60:
                            time_str = f"{time_seconds:.1f}秒"
                        else:
                            minutes = int(time_seconds // 60)
                            seconds = time_seconds % 60
                            time_str = f"{minutes}分{seconds:.1f}秒"
                        
                        # 格式化难度
                        difficulty_display = {
                            "easy": "简单 (3位数)",
                            "medium": "中等 (4位数)",
                            "hard": "困难 (5位数)"
                        }.get(difficulty, difficulty)
                        
                        # 格式化结果
                        result = "已完成" if gave_up == 0 else "已弃权"
                        
                        # 显示记录
                        st.write(f"**时间**: {timestamp} | **玩家**: {nickname} | **游戏模式**: 逻辑大师 | **难度**: {difficulty_display} | **尝试次数**: {attempts} | **用时**: {time_str} | **结果**: {result}")
                else:
                    st.write("暂无游戏历史记录")
            
            # 2. 账号信息
            with admin_tabs[1]:
                st.subheader("账号信息")
                
                # 获取所有用户信息
                users = get_all_users()
                
                if users:
                    # 显示账号信息
                    for user in users:
                        username, password, created_at = user
                        
                        # 获取用户数字币余额
                        coins = get_digital_coins(username)
                        
                        # 显示用户信息
                        st.write(f"**账号**: {username} | **密码**: {password} | **创建时间**: {created_at} | **数字币**: {coins}")
                else:
                    st.write("暂无账号信息")
            
            # 3. 数字币记录
            with admin_tabs[2]:
                st.subheader("数字币变动记录")
                
                # 获取数字币变动记录
                coin_history = get_coin_history()
                
                if coin_history:
                    # 显示数字币变动记录
                    for record in coin_history:
                        username, amount, reason, timestamp = record
                        
                        # 格式化金额和变动类型
                        amount_str = f"+{amount}" if amount > 0 else str(amount)
                        change_type = "增加" if amount > 0 else "减少"
                        
                        # 显示记录
                        st.write(f"**时间**: {timestamp} | **账户**: {username} | **变动数量**: {amount_str} | **类型**: {change_type} | **变动原因**: {reason}")
                else:
                    st.write("暂无数字币变动记录")
            
            # 4. 邮件发送
            with admin_tabs[3]:
                st.subheader("邮件发送")
                
                # 获取所有用户
                users = get_all_users()
                user_list = [user[0] for user in users]
                user_list.insert(0, "所有玩家")
                
                # 邮件发送表单
                recipient = st.selectbox("选择收件人", user_list)
                email_title = st.text_input("邮件标题")
                email_content = st.text_area("邮件内容")
                
                # 道具发放
                st.subheader("发放道具")
                coin_amount = st.number_input("数字币数量", min_value=0, step=1)
                
                if st.button("发送邮件并发放道具"):
                    if not email_title or not email_content:
                        st.error("请填写邮件标题和内容")
                    else:
                        # 处理收件人
                        if recipient == "所有玩家":
                            # 发送给所有玩家
                            for user in user_list[1:]:  # 排除"所有玩家"选项
                                # 发送邮件
                                send_email(user, email_title, email_content, coin_amount)
                            st.success(f"邮件已发送给所有玩家，包含{coin_amount}数字币")
                        else:
                            # 发送给特定玩家
                            # 发送邮件
                            send_email(recipient, email_title, email_content, coin_amount)
                            st.success(f"邮件已发送给{recipient}，包含{coin_amount}数字币")
            
            # 5. 每日排行榜
            with admin_tabs[4]:
                st.subheader("每日排行榜")
                
                # 日期选择器
                selected_date = st.date_input("选择日期")
                date_str = selected_date.strftime('%Y-%m-%d')
                
                # 获取指定日期的排行榜
                leaderboard = get_daily_leaderboard(date_str)
                
                if leaderboard:
                    # 显示排行榜
                    st.write(f"**{date_str} 排行榜**")
                    for i, record in enumerate(leaderboard, 1):
                        nickname, time_seconds, difficulty, attempts = record
                        
                        # 格式化时间
                        if time_seconds < 60:
                            time_str = f"{time_seconds:.1f}秒"
                        else:
                            minutes = int(time_seconds // 60)
                            seconds = time_seconds % 60
                            time_str = f"{minutes}分{seconds:.1f}秒"
                        
                        # 格式化难度
                        difficulty_display = {
                            "easy": "简单 (3位数)",
                            "medium": "中等 (4位数)",
                            "hard": "困难 (5位数)"
                        }.get(difficulty, difficulty)
                        
                        # 显示排名
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                        st.write(f"{medal} **{nickname}** - 难度: {difficulty_display} | 尝试次数: {attempts} | 用时: {time_str}")
                else:
                    st.write(f"{date_str} 暂无排行榜数据")
            
            # 返回主菜单
            if st.button("🏠 返回主菜单"):
                st.session_state.page = None
                st.rerun()
        return
    
    # ===================== 排行榜显示 =====================
    if st.session_state.show_leaderboard:
        with st.container():
            st.header("🏆 排行榜")
            
            difficulty_option = st.selectbox(
                "选择难度查看排行榜：",
                ["全部", "简单 (3位数)", "中等 (4位数)", "困难 (5位数)"],
                key="leaderboard_difficulty"
            )
            
            difficulty_map = {
                "全部": None,
                "简单 (3位数)": "easy",
                "中等 (4位数)": "medium",
                "困难 (5位数)": "hard"
            }
            selected_difficulty = difficulty_map[difficulty_option]
            
            leaderboard_data = get_leaderboard(selected_difficulty, 10)
            
            if leaderboard_data:
                for i, (nickname, time_seconds, difficulty, attempts) in enumerate(leaderboard_data, 1):
                    if time_seconds < 60:
                        time_str = f"{time_seconds:.1f}秒"
                    else:
                        minutes = int(time_seconds // 60)
                        seconds = time_seconds % 60
                        time_str = f"{minutes}分{seconds:.1f}秒"
                    
                    difficulty_display = {
                        "easy": "简单 (3位数)",
                        "medium": "中等 (4位数)",
                        "hard": "困难 (5位数)"
                    }.get(difficulty, difficulty)
                    
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                    st.write(f"{medal} **{nickname}** - 尝试次数: {attempts} | 难度: {difficulty_display} | {time_str}")
            else:
                st.write("暂无排行榜数据，快来挑战吧！")
            
            if st.button("🏠 返回主菜单"):
                st.session_state.show_leaderboard = False
                st.rerun()
    
    # ===================== 主菜单（模式选择） =====================
    elif st.session_state.game_mode is None:
        with st.container():
            st.markdown('<div style="text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 15px;">在数字的迷雾中，唯有智者能找到通往胜利的钥匙！</div>', unsafe_allow_html=True)
            st.header("选择游戏模式")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("逻辑大师"):
                    st.session_state.game_mode = "answer"
                    st.rerun()
            
            with col2:
                if st.button("赌狗天堂"):
                    st.session_state.game_mode = "dice"
                    st.rerun()
            
            with col3:
                if st.button("线下辅助"):
                    st.session_state.game_mode = "create"
                    st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏆 排行榜"):
                st.session_state.show_leaderboard = True
                st.rerun()
            
            # 后台管理入口（仅管理员可见）
            if st.session_state.username == "admin":
                if st.button("🔧 后台管理"):
                    st.session_state.page = "admin"
                    st.rerun()
    
    # ===================== 答题模式（3/4/5位数都修复） =====================
    elif st.session_state.game_mode == "answer":
        # 难度选择（核心修复：点击可正常跳转）
        if st.session_state.difficulty is None:
            with st.container():
                st.header("选择难度级别")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("简单 (3位数)"):
                        st.session_state.difficulty = "easy"
                        st.session_state.length = 3
                        st.session_state.secret = generate_secret(3)
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                        st.session_state.start_time = time.time()
                        st.rerun()
                
                with col2:
                    if st.button("中等 (4位数)"):
                        st.session_state.difficulty = "medium"
                        st.session_state.length = 4
                        st.session_state.secret = generate_secret(4)
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                        st.session_state.start_time = time.time()
                        st.rerun()
                
                with col3:
                    if st.button("困难 (5位数)"):
                        st.session_state.difficulty = "hard"
                        st.session_state.length = 5
                        st.session_state.secret = generate_secret(5)
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                        st.session_state.start_time = time.time()
                        st.rerun()
                
                if st.button("🏠 返回主菜单", key="back_to_menu"):
                    reset_game_state()
                    st.session_state.game_mode = None
                    st.rerun()
        
        # 游戏进行中
        else:
            with st.container():
                # 新增：渲染胜利信息（刷新后保留）
                if st.session_state.win_refresh and st.session_state.win_info:
                    win = st.session_state.win_info
                    # 显示恭喜文字+获得数字币
                    st.markdown(f'<div class="congratulation">猜对了！您获得了{win["coins"]}数字币</div>', unsafe_allow_html=True)
                    # 数字币飞入口袋动画
                    for i in range(win["coins"]):
                        st.markdown(f'<div class="digital-coin coin-animation">{i+1}</div>', unsafe_allow_html=True)
                    # 胜利提示（显示最新余额）
                    st.success(f"恭喜你猜对了！用了{win['attempts']}次尝试，用时{win['time_str']}。当前余额：{win['new_balance']} 数字币")
                    
                    # 获取本局游戏的排名（只显示今天的数据，包含时间戳）
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    today = datetime.date.today().strftime('%Y-%m-%d')
                    
                    # 获取包含时间戳的排行榜数据，按尝试次数和时间排序
                    cursor.execute(
                        "SELECT nickname, time_seconds, difficulty, attempts, timestamp FROM scores WHERE difficulty = ? AND date(timestamp) = ? ORDER BY attempts ASC, time_seconds ASC",
                        (win["difficulty"], today)
                    )
                    leaderboard_with_time = cursor.fetchall()
                    conn.close()
                    
                    # 查找玩家在排行榜中的位置
                    player_rank = None
                    if leaderboard_with_time:
                        # 找到本局游戏的记录（相同昵称、尝试次数，且时间最接近当前时间）
                        current_time = time.time()
                        closest_record = None
                        closest_time_diff = float('inf')
                        
                        for i, (nickname, _, _, attempts, timestamp) in enumerate(leaderboard_with_time, 1):
                            if nickname == st.session_state.nickname and attempts == win["attempts"]:
                                # 计算时间差，找到最接近当前时间的记录（即本局游戏）
                                record_time = time.mktime(datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').timetuple())
                                time_diff = abs(record_time - current_time)
                                if time_diff < closest_time_diff:
                                    closest_time_diff = time_diff
                                    closest_record = i
                        
                        # 如果找到了本局游戏的记录
                        if closest_record:
                            player_rank = closest_record
                        # 如果没有找到，找该昵称的最佳排名
                        else:
                            for i, (nickname, _, _, _, _) in enumerate(leaderboard_with_time, 1):
                                if nickname == st.session_state.username:
                                    player_rank = i
                                    break
                    
                    if player_rank:
                        difficulty_display = {
                            "easy": "简单 (3位数)",
                            "medium": "中等 (4位数)",
                            "hard": "困难 (5位数)"
                        }.get(win["difficulty"])
                        medal = "🥇" if player_rank == 1 else "🥈" if player_rank == 2 else "🥉" if player_rank == 3 else f"#{player_rank}"
                        st.info(f"{medal} 恭喜，您本局游戏的分数排名第{player_rank}名！")
                    # 烟花动画
                    st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                    # 标记游戏结束
                    st.session_state.game_over = True
                    # 重置刷新状态（避免重复显示）
                    st.session_state.win_refresh = False
                
                st.header("答题模式")
                st.write(f"难度：{st.session_state.difficulty} ({st.session_state.length}位数)")
                st.write("游戏规则：")
                st.write(f"1. 系统会生成一个{st.session_state.length}位数，每个数字都不重复")
                st.write(f"2. 你需要输入一个{st.session_state.length}位数进行猜测")
                st.write("3. 系统会反馈：")
                st.write("   - A：表示数字和位置都正确的个数")
                st.write("   - B：表示数字正确但位置错误的个数")
                st.write(f"4. 当你猜中所有数字时（{st.session_state.length}A0B），游戏胜利")
                
                # 猜测输入（游戏未结束时显示）
                if not st.session_state.game_over:
                    guess = st.text_input(
                        f"请输入你的猜测（{st.session_state.length}位数）：",
                        value=st.session_state.guess_input,
                        key="guess_input_field"
                    )
                    
                    if st.button("提交猜测"):
                        if not guess.isdigit() or len(guess) != st.session_state.length:
                            st.error(f"请输入有效的{st.session_state.length}位数！")
                        elif len(set(guess)) != st.session_state.length:
                            st.error("输入的数字不能重复！")
                        else:
                            st.session_state.attempts += 1
                            a, b = calculate_AB(st.session_state.secret, guess)
                            st.session_state.history.append((guess, a, b))
                            st.info(f"已提交猜测：{guess} → {a}A{b}B")
                            
                            # 猜中逻辑（终极修复：强制刷新+状态保留）
                            if a == st.session_state.length:
                                # 计算用时并保存
                                time_used = time.time() - st.session_state.start_time
                                save_score(st.session_state.username, time_used, st.session_state.difficulty, st.session_state.attempts)
                                
                                # 发放数字币
                                if st.session_state.difficulty == "easy":
                                    coins = 2
                                elif st.session_state.difficulty == "medium":
                                    coins = 5
                                else:  # hard
                                    coins = 10
                                update_digital_coins(st.session_state.username, coins, f"逻辑大师游戏奖励 - {st.session_state.difficulty}难度")
                                
                                # 格式化用时
                                if time_used < 60:
                                    time_str = f"{time_used:.1f}秒"
                                else:
                                    minutes = int(time_used // 60)
                                    seconds = time_used % 60
                                    time_str = f"{minutes}分{seconds:.1f}秒"
                                
                                # 获取最新余额（强制从数据库读取）
                                new_balance = get_digital_coins(st.session_state.username)
                                
                                # 保存胜利信息到会话状态（刷新后保留）
                                st.session_state.win_info = {
                                    "coins": coins,
                                    "attempts": st.session_state.attempts,
                                    "time_str": time_str,
                                    "new_balance": new_balance,
                                    "difficulty": st.session_state.difficulty,
                                    "length": st.session_state.length
                                }
                                # 标记需要刷新
                                st.session_state.win_refresh = True
                                # 强制刷新页面（关键：刷新后余额自动更新）
                                st.rerun()
                            # 未猜中（才执行清空+刷新，保证输入框正常）
                            else:
                                st.session_state.guess_input = ""
                                st.rerun()
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # ========== 核心修复：弃权结果展示 ==========
                if st.session_state.abandon_result is not None:
                    res = st.session_state.abandon_result
                    # 显示失败动画
                    st.markdown('<div style="font-size: 36px; font-weight: bold; color: #ff6b6b; font-family: \'Comic Sans MS\', \'Microsoft YaHei\', cursive, sans-serif; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); animation: pulse 1s ease-in-out infinite alternate; text-align: center; margin: 20px 0;">失败了！</div>', unsafe_allow_html=True)
                    # 显示弃权提示和代币扣除
                    st.error(f"你选择了弃权！用了{res['attempts']}次尝试，用时{res['time_str']}。扣除了5个数字币。")
                    # 显示正确答案
                    st.error(f"正确答案是：{res['secret']}")
                    # 更新数字币显示
                    new_balance = get_digital_coins(st.session_state.username)
                    script_html = f'''<script>
                        const coinElements = document.querySelectorAll(".digital-coin");
                        if (coinElements.length > 0) {{
                            const coinElement = coinElements[0];
                            const balanceElement = coinElement.nextElementSibling;
                            if (balanceElement) {{
                                balanceElement.textContent = "{new_balance}";
                            }}
                        }}
                    </script>'''
                    st.markdown(script_html, unsafe_allow_html=True)
                
                # 游戏操作按钮
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("重新开始"):
                        # 重置游戏状态，重新生成题目，重置时间
                        reset_game_state(reset_nickname=False)
                        st.session_state.secret = generate_secret(st.session_state.length)
                        st.session_state.start_time = time.time()
                        st.session_state.win_info = None  # 新增：重置胜利信息
                        st.rerun()
                
                with col2:
                    # 1. 显示弃权按钮（游戏未结束时）
                    if not st.session_state.game_over and not st.session_state.show_abandon_confirm:
                        if st.button("弃权"):
                            current_coins = get_digital_coins(st.session_state.username)
                            if current_coins >= 5:
                                st.session_state.show_abandon_confirm = True
                                st.rerun()
                            else:
                                st.warning("弃权需要消耗5数字币，您的余额不足，请继续挑战，胜利就在前方。")

                    # 2. 显示确认弃权弹窗
                    if st.session_state.show_abandon_confirm and not st.session_state.game_over:
                        st.warning("挑战者，是否确定弃权？弃权需要消耗5数字币。")
                        confirm_col1, confirm_col2 = st.columns(2)
                        with confirm_col1:
                            if st.button("确认弃权"):
                                # 计算用时
                                time_used = time.time() - st.session_state.start_time
                                # 保存弃权记录
                                save_score(st.session_state.username, time_used, st.session_state.difficulty, st.session_state.attempts, gave_up=1)
                                # 扣除5个数字币
                                update_digital_coins(st.session_state.username, -5, "逻辑大师游戏弃权扣除")
                                
                                # 格式化用时
                                if time_used < 60:
                                    time_str = f"{time_used:.1f}秒"
                                else:
                                    minutes = int(time_used // 60)
                                    seconds = time_used % 60
                                    time_str = f"{minutes}分{seconds:.1f}秒"
                                
                                # 保存弃权结果到session_state
                                st.session_state.abandon_result = {
                                    "time_str": time_str,
                                    "secret": st.session_state.secret,
                                    "attempts": st.session_state.attempts
                                }
                                # 标记游戏结束
                                st.session_state.game_over = True
                                # 关闭确认弹窗
                                st.session_state.show_abandon_confirm = False
                                st.rerun()
                        with confirm_col2:
                            if st.button("继续挑战"):
                                st.session_state.show_abandon_confirm = False
                                st.rerun()
                
                with col3:
                    if st.button("🏆 查看排行榜"):
                        st.session_state.show_leaderboard = True
                        st.rerun()
                
                with col4:
                    if st.button("🏠 返回主菜单", key="back_to_menu_game"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
    
    # ===================== 出题模式（同步修复特效） =====================
    elif st.session_state.game_mode == "create":
        with st.container():
            st.header("出题模式")
            st.write("请输入一个四位数，每个数字不重复")
            
            # 输入目标数字
            if st.session_state.secret is None:
                secret_input = st.text_input("请输入你要出的题目（四位数）：")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("设置题目"):
                        if not secret_input.isdigit() or len(secret_input) != 4:
                            st.error("请输入有效的四位数！")
                        elif len(set(secret_input)) != 4:
                            st.error("输入的数字不能重复！")
                        else:
                            st.session_state.secret = secret_input
                            reset_game_state(reset_nickname=False)
                            st.rerun()
                
                with col2:
                    if st.button("🏠 返回主菜单"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
            
            # 游戏进行中
            else:
                st.write(f"题目已设置：{st.session_state.secret}")
                st.write("现在你可以输入猜测的数字，系统会告诉你几A几B")
                
                if not st.session_state.game_over:
                    guess = st.text_input(
                        "请输入猜测的数字（四位数）：",
                        value=st.session_state.create_guess_input,
                        key="create_guess_input_field"
                    )
                    
                    if st.button("提交猜测"):
                        if not guess.isdigit() or len(guess) != 4:
                            st.error("请输入有效的四位数！")
                        elif len(set(guess)) != 4:
                            st.error("输入的数字不能重复！")
                        else:
                            st.session_state.attempts += 1
                            a, b = calculate_AB(st.session_state.secret, guess)
                            st.session_state.history.append((guess, a, b))
                            st.info(f"已提交猜测：{guess} → {a}A{b}B")
                            
                            # 猜中逻辑（无st.rerun，不刷新）
                            if a == 4:
                                st.markdown('<div class="congratulation">猜对了！</div>', unsafe_allow_html=True)
                                st.success(f"游戏结束！共猜测{st.session_state.attempts}轮")
                                st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                                st.session_state.game_over = True
                            # 未猜中（才执行清空+刷新）
                            else:
                                st.session_state.create_guess_input = ""
                                st.rerun()
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # 游戏操作按钮
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("重新出题"):
                        st.session_state.secret = None
                        reset_game_state(reset_nickname=False)
                        st.rerun()
                
                with col2:
                    if st.button("重新开始"):
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.create_guess_input = ""
                        st.rerun()
                
                with col3:
                    if st.button("🏠 返回主菜单", key="back_to_menu_create"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()

    # ===================== 赌狗天堂游戏模式 =====================
    elif st.session_state.game_mode == "dice":
        with st.container():
            st.header("赌狗天堂")
            
            st.write("游戏规则：")
            st.write("1. 系统会随机投掷3个骰子")
            st.write("2. 你需要猜测结果是'大'、'小'还是'围'")
            st.write('3. 点数总和在4到10之间（包含4和10）表示"小"；11到17之间（包含11和17）表示"大"；三个骰子数字一致表示"围"')
            st.write("4. 猜对获胜，猜错失败")
            st.write("5. 特别说明：如果结果是'围'，即使点数总和符合'大'或'小'的范围，也只有猜'围'才算成功")
            st.write("6. 若猜中大小，可以获得2倍奖励；猜中围，可以获得3倍奖励；猜错时，赌注将累计到今日奖池中")
            
            # 重置游戏状态
            if not st.session_state.dice_values:
                st.session_state.dice_values = []
                st.session_state.player_choice = None
                st.session_state.show_dice = False
                st.session_state.dice_animation = False
                st.session_state.bet_amount = 0
                st.session_state.bet_deducted = False
            
            # 投骰子按钮
            if not st.session_state.dice_values:
                if st.button("开始游戏 - 投骰子"):
                    st.session_state.dice_animation = True
                    # 生成随机骰子值
                    st.session_state.dice_values = [random.randint(1, 6) for _ in range(3)]
                    st.rerun()
                
                # 返回主菜单按钮（在投骰子按钮下面）
                if st.button("🏠 返回主菜单", key="back_to_menu_dice_before"):
                    reset_game_state()
                    st.session_state.game_mode = None
                    st.rerun()
            
            # 显示骰子和遮罩
            if st.session_state.dice_values:
                # 显示今日奖池
                today_pool = get_today_prize_pool()
                st.subheader(f"今日奖池: {today_pool} 数字币")
                st.write("挑战逻辑大师，追逐排行榜，瓜分赌狗的果实！")
                st.subheader("骰子结果")
                col1, col2, col3 = st.columns(3)
                
                # 骰子动画和遮罩效果
                for i, (col, value) in enumerate(zip([col1, col2, col3], st.session_state.dice_values), 1):
                    with col:
                        if st.session_state.show_dice:
                            # 显示骰子点数
                            st.markdown(f"<div style='text-align: center; font-size: 48px; font-weight: bold; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.5); padding: 20px; border-radius: 15px;'>{value}</div>", unsafe_allow_html=True)
                        else:
                            # 显示遮罩
                            st.markdown(f"<div style='text-align: center; font-size: 48px; font-weight: bold; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.8); padding: 20px; border-radius: 15px; animation: pulse 1s ease-in-out infinite alternate;'>?</div>", unsafe_allow_html=True)
                
                # 投骰子动画
                if st.session_state.dice_animation:
                    st.markdown("<div style='text-align: center; font-size: 24px; font-weight: bold; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 10px; margin: 10px 0;'>骰子滚动中...</div>", unsafe_allow_html=True)
                    # 模拟动画延迟
                    time.sleep(1)
                    st.session_state.dice_animation = False
                    st.rerun()
                
                # 玩家选择界面
                if not st.session_state.player_choice:
                    # 先输入赌注金额
                    st.subheader("请输入赌注金额")
                    # 获取玩家当前数字币余额
                    current_coins = get_digital_coins(st.session_state.username)
                    st.write(f"当前数字币余额：{current_coins}")
                    
                    # 检查数字币是否足够
                    if current_coins < 1:
                        st.error("数字币不足，请前往'逻辑大师'赢取数字币")
                    else:
                        # 输入赌注金额
                        bet_amount = st.number_input("赌注金额", min_value=1, max_value=current_coins, step=1, key="bet_amount_input")
                        
                        st.subheader("请选择")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("大"):
                                st.session_state.player_choice = "大"
                                st.session_state.bet_amount = bet_amount
                                st.rerun()
                        with col2:
                            if st.button("小"):
                                st.session_state.player_choice = "小"
                                st.session_state.bet_amount = bet_amount
                                st.rerun()
                        with col3:
                            if st.button("围"):
                                st.session_state.player_choice = "围"
                                st.session_state.bet_amount = bet_amount
                                st.rerun()
                    
                    # 返回主菜单按钮（在小按钮下面）
                    if st.button("🏠 返回主菜单", key="back_to_menu_dice_choice"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
                
                # 显示玩家选择并等待确认
                elif not st.session_state.show_dice:
                    st.subheader(f"你的选择：{st.session_state.player_choice}")
                    st.subheader(f"赌注金额：{st.session_state.bet_amount}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("确认，揭晓结果"):
                            st.session_state.show_dice = True
                            st.rerun()
                    with col2:
                        if st.button("我再想想"):
                            st.session_state.player_choice = None
                            st.rerun()
                    
                    # 返回主菜单按钮
                    if st.button("🏠 返回主菜单", key="back_to_menu_dice_confirm"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
                
                # 显示结果
                elif st.session_state.show_dice:
                    total = sum(st.session_state.dice_values)
                    st.subheader(f"点数总和：{total}")
                    
                    # 判定结果
                    # 首先检查是否为围（三个骰子数字一致）
                    if st.session_state.dice_values[0] == st.session_state.dice_values[1] == st.session_state.dice_values[2]:
                        result = "围"
                    elif 4 <= total <= 10:
                        result = "小"
                    elif 11 <= total <= 17:
                        result = "大"
                    else:
                        result = "未知"
                    
                    # 显示结果
                    if result == st.session_state.player_choice:
                        st.markdown('<div class="congratulation">恭喜中奖！</div>', unsafe_allow_html=True)
                        st.success(f"恭喜你猜对了！结果是{result}，点数总和为{total}")
                        st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                        
                        # 给玩家奖励，不扣除赌注
                        bet_amount = st.session_state.bet_amount
                        if not st.session_state.bet_deducted:
                            if result == "围":
                                # 猜中围，获得三倍赌注
                                reward = bet_amount * 3
                                update_digital_coins(st.session_state.username, reward, f"赌狗天堂 - 猜中围")
                                st.success(f"恭喜你获得 {reward} 数字币")
                            else:
                                # 猜中大或小，获得双倍赌注
                                reward = bet_amount * 2
                                update_digital_coins(st.session_state.username, reward, f"赌狗天堂 - 猜中{result}")
                                st.success(f"恭喜你获得 {reward} 数字币")
                            st.session_state.bet_deducted = True
                    else:
                        # 猜错，扣除赌注并添加到奖池
                        bet_amount = st.session_state.bet_amount
                        if not st.session_state.bet_deducted:
                            update_digital_coins(st.session_state.username, -bet_amount, f"赌狗天堂 - 猜错")
                            # 将赌注添加到奖池
                            update_prize_pool(bet_amount)
                            st.session_state.bet_deducted = True
                        st.markdown('<div style="font-size: 36px; font-weight: bold; color: #ff6b6b; font-family: \'Comic Sans MS\', \'Microsoft YaHei\', cursive, sans-serif; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); animation: pulse 1s ease-in-out infinite alternate; text-align: center; margin: 20px 0;">失败了！</div>', unsafe_allow_html=True)
                        st.error(f"猜错了！结果是{result}，点数总和为{total}")
                    
                    # 重新开始按钮
                    if st.button("再玩一次"):
                        # 重新投掷骰子，相当于点击了"开始游戏-投骰子"
                        st.session_state.dice_animation = True
                        # 生成新的随机骰子值
                        st.session_state.dice_values = [random.randint(1, 6) for _ in range(3)]
                        # 重置其他状态
                        st.session_state.player_choice = None
                        st.session_state.show_dice = False
                        st.session_state.bet_amount = 0
                        st.session_state.bet_deducted = False
                        st.rerun()
                    
                    # 返回主菜单按钮
                    if st.button("🏠 返回主菜单", key="back_to_menu_dice"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()

    # 右下角登出按钮
    st.markdown('<div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">', unsafe_allow_html=True)
    if st.button("登出", key="logout_button"):
        # 彻底清空所有状态
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.nickname = ""
        st.session_state.game_mode = None
        st.session_state.show_leaderboard = False
        st.session_state.win_refresh = False
        st.session_state.win_info = None
        st.session_state.abandon_result = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n游戏被用户中断，再见！")
    else:
        print("游戏正常运行")
