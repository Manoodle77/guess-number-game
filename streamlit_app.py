import streamlit as st
import random
import time
import sqlite3
import os

# ===================== 数据库初始化 =====================
DB_FILE = "game_scores.db"

def init_database():
    """初始化数据库，创建成绩表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

def save_score(nickname, time_seconds, difficulty, attempts):
    """保存玩家成绩到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scores (nickname, time_seconds, difficulty, attempts) VALUES (?, ?, ?, ?)",
        (nickname, time_seconds, difficulty, attempts)
    )
    conn.commit()
    conn.close()

def get_leaderboard(difficulty=None, limit=10):
    """获取排行榜数据，按用时排序（时间越短越靠前）"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if difficulty:
        cursor.execute(
            "SELECT nickname, time_seconds, difficulty, attempts FROM scores WHERE difficulty = ? ORDER BY time_seconds ASC LIMIT ?",
            (difficulty, limit)
        )
    else:
        cursor.execute(
            "SELECT nickname, time_seconds, difficulty, attempts FROM scores ORDER BY time_seconds ASC LIMIT ?",
            (limit,)
        )
    results = cursor.fetchall()
    conn.close()
    return results

# 初始化数据库
init_database()

# ===================== 初始化会话状态 - 增强版 =====================
# 新增：确保所有状态都初始化，避免首次运行报错
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
# 新增：用于锁定按钮状态，避免重复触发
if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False

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

# ===================== 辅助函数：重置游戏状态 =====================
def reset_game_state(reset_nickname=True):
    """重置游戏状态（可选择是否重置昵称）"""
    st.session_state.difficulty = None
    st.session_state.secret = None
    st.session_state.attempts = 0
    st.session_state.history = []
    st.session_state.game_over = False
    st.session_state.guess_input = ""
    st.session_state.create_guess_input = ""
    if reset_nickname:
        st.session_state.nickname = ""
        st.session_state.start_time = None

# ===================== 主应用 =====================
def main():
    # 自定义CSS（保留原有样式）
    st.markdown('''
    <style>
    /* 背景图片 */
    .stApp {
        background-image: url('https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=minimalist%20black%20and%20white%20background%2C%20gradient%20chessboard%20pattern%2C%20number%20grid%2C%20solid%20lines%20in%20top%20right%20corner%2C%20fading%20lines%20towards%20bottom%20left%2C%20pure%20white%20at%20bottom%20left%2C%20clean%20design&image_size=landscape_16_9');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }

    /* 标题样式 */
    .stTitle {
        color: #FFFFFF !important;
        font-family: 'Comic Sans MS', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        font-size: 36px !important;
        font-weight: bold;
    }

    /* 副标题样式 */
    .stHeading {
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }

    .stHeading h2 {
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }

    /* 主按钮样式 - 核心修改：强化文字颜色优先级 */
    .stButton > button {
        background: white !important;
        color: #000000 !important; /* 纯黑色，比black更明确 */
        border: 3px solid #9E9E9E;
        border-radius: 25px !important;
        padding: 12px 24px;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 20px;
        font-weight: bold;
        font-stretch: expanded;
        text-shadow: none !important;
        box-shadow: 4px 4px 0px #9E9E9E, 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        cursor: pointer;
        /* 新增：强制继承文字颜色 */
        --text-color: #000000 !important;
    }

    /* 按钮hover/active状态：确保文字还是黑色 */
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
        color: #000000 !important; /* 再次强调黑色 */
    }

    /* 返回按钮样式 - 同样强化文字颜色 */
    .back-button {
        background: white !important;
        color: #000000 !important; /* 纯黑色 */
        border: 2px solid #BDBDBD !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        font-weight: normal !important;
        box-shadow: 2px 2px 0px #BDBDBD !important;
        margin-top: 20px !important;
        --text-color: #000000 !important;
    }

    /* 关键修复：强制按钮内所有文字为黑色（覆盖全局p标签） */
    .stButton > button * {
        color: #000000 !important; /* 覆盖按钮内所有子元素的文字颜色 */
        text-shadow: none !important;
        background-color: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 0 !important;
    }

    /* 文本输入框样式 */
    .stTextInput > div > div > input {
        border: 2px solid #9E9E9E;
        border-radius: 15px;
        padding: 10px;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 16px;
        background-color: rgba(255, 255, 255, 0.9);
    }

    /* 文本内容样式 */
    .stWrite {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 5px 10px;
        border-radius: 10px;
        display: inline-block;
        margin: 2px 0;
    }

    /* 段落样式（保留全局白色，仅按钮内例外） */
    p {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 5px 10px;
        border-radius: 10px;
        display: inline-block;
        margin: 2px 0;
    }

    /* 列表项样式 */
    ul {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 16px;
    }

    li {
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 16px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 5px 10px;
        border-radius: 10px;
        margin: 5px 0;
        display: inline-block;
    }

    /* 成功/错误消息样式 */
    .stSuccess, .stError {
        border-radius: 15px;
        padding: 10px;
        border: 2px solid;
    }
    .stSuccess {
        background-color: rgba(6, 214, 160, 0.2);
        border-color: #06D6A0;
    }
    .stError {
        background-color: rgba(255, 87, 34, 0.2);
        border-color: #FF5722;
    }

    /* 烟花动画 */
    @keyframes fireworks {
        0% { transform: scale(0); opacity: 1; }
        100% { transform: scale(1); opacity: 0; }
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
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        animation: pulse 1s ease-in-out infinite alternate;
        text-align: center;
        margin: 20px 0;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        100% { transform: scale(1.1); }
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
                setTimeout(() => firework.remove(), 1000);
            }, i * 100);
        }
    }
    </script>
    ''', unsafe_allow_html=True)

    st.title("数字密码")
    
    # ===================== 排行榜显示 =====================
    if st.session_state.show_leaderboard:
        with st.container():
            st.header("🏆 排行榜")
            difficulty_option = st.selectbox(
                "选择难度查看排行榜：",
                ["全部", "简单 (3位数)", "中等 (4位数)", "困难 (5位数)"],
                key="leaderboard_difficulty"
            )
            difficulty_map = {"全部": None, "简单 (3位数)": "easy", "中等 (4位数)": "medium", "困难 (5位数)": "hard"}
            selected_difficulty = difficulty_map[difficulty_option]
            
            leaderboard_data = get_leaderboard(selected_difficulty, 10)
            if leaderboard_data:
                for i, (nickname, time_seconds, difficulty, attempts) in enumerate(leaderboard_data, 1):
                    time_str = f"{time_seconds:.1f}秒" if time_seconds < 60 else f"{int(time_seconds//60)}分{time_seconds%60:.1f}秒"
                    difficulty_display = {"easy": "简单 (3位数)", "medium": "中等 (4位数)", "hard": "困难 (5位数)"}.get(difficulty, difficulty)
                    medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
                    st.write(f"{medal} **{nickname}** - {time_str} | 难度: {difficulty_display} | 尝试次数: {attempts}")
            else:
                st.write("暂无排行榜数据，快来挑战吧！")
            
            # 优化：返回主菜单按钮（一次点击生效）
            if st.button("🏠 返回主菜单"):
                st.session_state.show_leaderboard = False
                st.rerun()  # 关键：强制重新运行，立即渲染主菜单
    
    # ===================== 主菜单（模式选择） =====================
    elif st.session_state.game_mode is None:
        with st.container():
            st.markdown(
                '<div style="text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 15px;">欢迎来到头脑风暴的世界！</div>',
                unsafe_allow_html=True
            )
            st.header("选择游戏模式")
            col1, col2 = st.columns(2)
            
            # 优化1：答题模式按钮（一次点击生效）
            with col1:
                if st.button("答题模式"):
                    st.session_state.game_mode = "answer"
                    st.rerun()  # 强制重新运行，立即渲染答题模式界面
            
            # 优化2：出题模式按钮（一次点击生效）
            with col2:
                if st.button("出题模式"):
                    st.session_state.game_mode = "create"
                    st.rerun()  # 强制重新运行，立即渲染出题模式界面
            
            # 排行榜按钮（一次点击生效）
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏆 排行榜"):
                st.session_state.show_leaderboard = True
                st.rerun()  # 强制重新运行，立即渲染排行榜
    
    # ===================== 答题模式 =====================
    elif st.session_state.game_mode == "answer":
        # 昵称输入
        if st.session_state.nickname == "":
            with st.container():
                st.header("请输入你的昵称")
                nickname_input = st.text_input("昵称：", key="nickname_input")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("开始游戏"):
                        if nickname_input.strip():
                            st.session_state.nickname = nickname_input.strip()
                            st.session_state.start_time = time.time()
                            st.rerun()  # 强制刷新，进入难度选择
                        else:
                            st.error("请输入昵称！")
                
                with col2:
                    if st.button("🏠 返回主菜单"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
        
        # 难度选择
        elif st.session_state.difficulty is None:
            with st.container():
                st.header("选择难度级别")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("简单 (3位数)"):
                        st.session_state.difficulty = "easy"
                        st.session_state.length = 3
                        st.session_state.secret = generate_secret(3)
                        reset_game_state(reset_nickname=False)
                        st.rerun()
                
                with col2:
                    if st.button("中等 (4位数)"):
                        st.session_state.difficulty = "medium"
                        st.session_state.length = 4
                        st.session_state.secret = generate_secret(4)
                        reset_game_state(reset_nickname=False)
                        st.rerun()
                
                with col3:
                    if st.button("困难 (5位数)"):
                        st.session_state.difficulty = "hard"
                        st.session_state.length = 5
                        st.session_state.secret = generate_secret(5)
                        reset_game_state(reset_nickname=False)
                        st.rerun()
                
                # 返回主菜单
                if st.button("🏠 返回主菜单", key="back_to_menu"):
                    reset_game_state()
                    st.session_state.game_mode = None
                    st.rerun()
        
        # 游戏进行中
        else:
            with st.container():
                st.header("答题模式")
                st.write(f"难度：{st.session_state.difficulty} ({st.session_state.length}位数)")
                st.write("游戏规则：")
                st.write(f"1. 系统会生成一个{st.session_state.length}位数，每个数字都不重复")
                st.write(f"2. 你需要输入一个{st.session_state.length}位数进行猜测")
                st.write("3. 系统会反馈：")
                st.write("   - A：表示数字和位置都正确的个数")
                st.write("   - B：表示数字正确但位置错误的个数")
                st.write(f"4. 当你猜中所有数字时（{st.session_state.length}A0B），游戏胜利")
                
                # 猜测输入
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
                            
                            if a == st.session_state.length:
                                # 计算用时并保存成绩
                                time_used = time.time() - st.session_state.start_time
                                save_score(st.session_state.nickname, time_used, st.session_state.difficulty, st.session_state.attempts)
                                
                                # 格式化用时
                                time_str = f"{time_used:.1f}秒" if time_used < 60 else f"{int(time_used//60)}分{time_used%60:.1f}秒"
                                st.markdown('<div class="congratulation">猜对了！</div>', unsafe_allow_html=True)
                                st.success(f"恭喜你猜对了！用了{st.session_state.attempts}次尝试，用时{time_str}。")
                                
                                # 排行榜提示
                                leaderboard = get_leaderboard(st.session_state.difficulty, 3)
                                player_rank = next((i for i, (n, _, _, _) in enumerate(leaderboard, 1) if n == st.session_state.nickname), None)
                                if player_rank:
                                    difficulty_display = {"easy": "简单 (3位数)", "medium": "中等 (4位数)", "hard": "困难 (5位数)"}.get(st.session_state.difficulty, st.session_state.difficulty)
                                    medal = "🥇" if player_rank==1 else "🥈" if player_rank==2 else "🥉"
                                    st.info(f"{medal} 恭喜，您目前在{difficulty_display}模式中，排名第{player_rank}名！")
                                
                                st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                                st.session_state.game_over = True
                            
                            st.session_state.guess_input = ""
                            st.rerun()  # 强制刷新，清空输入框
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # 游戏结束操作
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("重新开始"):
                        reset_game_state(reset_nickname=False)
                        st.rerun()
                
                with col2:
                    if st.button("🏆 查看排行榜"):
                        st.session_state.show_leaderboard = True
                        st.rerun()
                
                with col3:
                    if st.button("🏠 返回主菜单", key="back_to_menu_game"):
                        reset_game_state()
                        st.session_state.game_mode = None
                        st.rerun()
    
    # ===================== 出题模式 =====================
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
                            
                            if a == 4:
                                st.markdown('<div class="congratulation">猜对了！</div>', unsafe_allow_html=True)
                                st.success(f"游戏结束！共猜测{st.session_state.attempts}轮")
                                st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                                st.session_state.game_over = True
                            
                            st.session_state.create_guess_input = ""
                            st.rerun()
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # 游戏结束操作
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("重新出题"):
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n游戏被用户中断，再见！")
    except Exception as e:
        print(f"发生错误：{e}")
        print("游戏异常退出")
