import streamlit as st
import random

# ===================== 初始化会话状态 - 放在脚本最前面 =====================
if 'game_mode' not in st.session_state:
    st.session_state.game_mode = None
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
if 'submit_clicked' not in st.session_state:
    st.session_state.submit_clicked = False
if 'create_submit_clicked' not in st.session_state:
    st.session_state.create_submit_clicked = False
if 'mode_submit_clicked' not in st.session_state:
    st.session_state.mode_submit_clicked = False
if 'difficulty_submit_clicked' not in st.session_state:
    st.session_state.difficulty_submit_clicked = False

# ===================== 核心函数 =====================
# 生成随机的不重复数字
def generate_secret(length=4):
    digits = list('0123456789')
    random.shuffle(digits)
    return ''.join(digits[:length])

# 计算A和B的数量
def calculate_AB(secret, guess):
    a_count = sum(1 for s, g in zip(secret, guess) if s == g)
    # 计算B的数量：总共有多少个共同数字，减去位置正确的A的数量
    common = set(secret) & set(guess)
    b_count = sum(min(secret.count(c), guess.count(c)) for c in common) - a_count
    return a_count, b_count

# ===================== 主应用 =====================
def main():
    # 自定义CSS（保留原有样式，无修改）
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

    /* 主按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%);
        color: white;
        border: 3px solid #9E9E9E;
        border-radius: 25px !important;
        padding: 12px 24px;
        font-family: 'Comic Sans MS', 'Microsoft YaHei', 'SimHei', 'PingFang SC', cursive, sans-serif;
        font-size: 18px;
        font-weight: bold;
        font-stretch: expanded;
        text-shadow: 1px 1px 0px rgba(0, 0, 0, 0.5);
        box-shadow: 4px 4px 0px #9E9E9E, 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #BDBDBD 0%, #9E9E9E 100%);
        color: white;
        border: 3px solid #E0E0E0;
        box-shadow: 4px 4px 0px #E0E0E0, 0 6px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-3px) scale(1.05);
        text-shadow: 1px 1px 0px rgba(0, 0, 0, 0.2);
    }

    .stButton > button:active {
        transform: translateY(1px);
        box-shadow: 2px 2px 0px #E0E0E0;
    }

    /* 返回按钮样式 */
    .back-button {
        background: linear-gradient(135deg, #F5F5F5 0%, #E0E0E0 100%) !important;
        color: #666666 !important;
        border: 2px solid #BDBDBD !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        font-weight: normal !important;
        box-shadow: 2px 2px 0px #BDBDBD !important;
        margin-top: 20px !important;
    }

    .back-button:hover {
        background: linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%) !important;
        color: #555555 !important;
        border: 2px solid #9E9E9E !important;
        box-shadow: 2px 2px 0px #9E9E9E !important;
        transform: translateY(-2px) scale(1.03) !important;
    }

    .back-button:active {
        transform: translateY(1px) !important;
        box-shadow: 1px 1px 0px #9E9E9E !important;
    }

    /* 文本输入框样式 */
    .stTextInput > div > div > input {
        border: 2px solid #9E9E9E;
        border-radius: 15px;
        padding: 10px;
        font-family: 'Comic Sans MS', cursive, sans-serif;
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

    /* 段落样式 */
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

    /* 按钮内文字样式 */
    .stButton p {
        background-color: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 0 !important;
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

    /* 成功消息样式 */
    .stSuccess {
        background-color: rgba(6, 214, 160, 0.2);
        border-radius: 15px;
        border: 2px solid #06D6A0;
        padding: 10px;
    }

    /* 错误消息样式 */
    .stError {
        background-color: rgba(255, 87, 34, 0.2);
        border-radius: 15px;
        border: 2px solid #FF5722;
        padding: 10px;
    }

    /* 烟花动画 */
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

    st.title("数字密码")
    
    # ===================== 游戏模式选择 =====================
    if st.session_state.game_mode is None:
        with st.container():
            st.markdown('<div style="text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background-color: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 15px;">欢迎来到头脑风暴的世界！</div>', unsafe_allow_html=True)
            st.header("选择游戏模式")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("答题模式"):
                    st.session_state.game_mode = "answer"
            
            with col2:
                if st.button("出题模式"):
                    st.session_state.game_mode = "create"
    
    # ===================== 答题模式 =====================
    elif st.session_state.game_mode == "answer":
        # 难度选择
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
                        st.session_state.guess_input = ""  # 重置输入框
                
                with col2:
                    if st.button("中等 (4位数)"):
                        st.session_state.difficulty = "medium"
                        st.session_state.length = 4
                        st.session_state.secret = generate_secret(4)
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""  # 重置输入框
                
                with col3:
                    if st.button("困难 (5位数)"):
                        st.session_state.difficulty = "hard"
                        st.session_state.length = 5
                        st.session_state.secret = generate_secret(5)
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""  # 重置输入框
                
                # 返回主菜单（修复：移除无效的difficulty_submit_clicked设置）
                if st.button("🏠 返回主菜单", key="back_to_menu"):
                    st.session_state.game_mode = None
                    st.session_state.difficulty = None
                    st.session_state.secret = None
                    st.session_state.attempts = 0
                    st.session_state.history = []
                    st.session_state.game_over = False
                    st.session_state.guess_input = ""
                    st.session_state.create_guess_input = ""
        
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
                
                # 调试信息（可选保留）
                # st.write(f"调试信息：生成的数字是 {st.session_state.secret}")
                
                # 猜测输入（游戏未结束时）
                if not st.session_state.game_over:
                    # 输入框（修复：简化value绑定，确保清空生效）
                    guess = st.text_input(
                        f"请输入你的猜测（{st.session_state.length}位数）：",
                        value=st.session_state.guess_input,
                        key="guess_input_field"
                    )
                    
                    # 提交猜测按钮（核心修复：调整submit_clicked逻辑）
                    if st.button("提交猜测"):
                        # 先验证输入，再处理逻辑（无需依赖submit_clicked标记）
                        if not guess.isdigit() or len(guess) != st.session_state.length:
                            st.error(f"请输入有效的{st.session_state.length}位数！")
                        elif len(set(guess)) != st.session_state.length:
                            st.error("输入的数字不能重复！")
                        else:
                            # 验证通过，处理游戏逻辑
                            st.session_state.attempts += 1
                            a, b = calculate_AB(st.session_state.secret, guess)
                            st.session_state.history.append((guess, a, b))
                            
                            # 清空输入框（立即生效）
                            st.session_state.guess_input = ""
                            
                            # 显示反馈（能正常渲染）
                            st.info(f"已提交猜测：{guess} → {a}A{b}B")
                            
                            # 猜对逻辑
                            if a == st.session_state.length:
                                st.markdown('<div class="congratulation">猜对了！</div>', unsafe_allow_html=True)
                                st.success(f"恭喜你猜对了！用了{st.session_state.attempts}次尝试。")
                                st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                                st.session_state.game_over = True
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # 游戏结束或重新开始
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("重新开始"):
                        st.session_state.difficulty = None
                        st.session_state.secret = None
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                
                with col2:
                    if st.button("🏠 返回主菜单", key="back_to_menu_game"):
                        st.session_state.game_mode = None
                        st.session_state.difficulty = None
                        st.session_state.secret = None
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                        st.session_state.create_guess_input = ""
    
    # ===================== 出题模式 =====================
    elif st.session_state.game_mode == "create":
        with st.container():
            st.header("出题模式")
            st.write("请输入一个四位数，每个数字不重复")
            
            # 输入目标数字
            if st.session_state.secret is None:
                secret_input = st.text_input("请输入你要出的题目（四位数）：")
                
                if st.button("设置题目"):
                    if not secret_input.isdigit() or len(secret_input) != 4:
                        st.error("请输入有效的四位数！")
                    elif len(set(secret_input)) != 4:
                        st.error("输入的数字不能重复！")
                    else:
                        st.session_state.secret = secret_input
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.create_guess_input = ""
            
            # 游戏进行中
            else:
                st.write(f"题目已设置：{st.session_state.secret}")
                st.write("现在你可以输入猜测的数字，系统会告诉你几A几B")
                
                # 猜测输入
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
                            
                            # 清空输入框
                            st.session_state.create_guess_input = ""
                            
                            # 显示即时反馈
                            st.info(f"已提交猜测：{guess} → {a}A{b}B")
                            
                            if a == 4:
                                st.markdown('<div class="congratulation">猜对了！</div>', unsafe_allow_html=True)
                                st.success(f"游戏结束！共猜测{st.session_state.attempts}轮")
                                st.markdown('<script>createFireworks();</script>', unsafe_allow_html=True)
                                st.session_state.game_over = True
                
                # 显示历史记录
                if st.session_state.history:
                    st.subheader("猜测历史")
                    for i, (guess, a, b) in enumerate(st.session_state.history, 1):
                        st.write(f"第{i}次：{guess} → {a}A{b}B")
                
                # 游戏结束或重新开始
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("重新出题"):
                        st.session_state.secret = None
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.create_guess_input = ""
                
                with col2:
                    if st.button("重新开始"):
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.create_guess_input = ""
                
                with col3:
                    if st.button("🏠 返回主菜单", key="back_to_menu_create"):
                        st.session_state.game_mode = None
                        st.session_state.secret = None
                        st.session_state.attempts = 0
                        st.session_state.history = []
                        st.session_state.game_over = False
                        st.session_state.guess_input = ""
                        st.session_state.create_guess_input = ""

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n游戏被用户中断，再见！")
    except Exception as e:
        print(f"发生错误：{e}")
        print("游戏异常退出")
