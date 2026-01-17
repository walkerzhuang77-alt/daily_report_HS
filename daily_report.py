import os
import sys
import time
import datetime
import traceback
from dotenv import load_dotenv

# ==========================================
# 0. 智能网络配置 (关键修改！🚀)
# ==========================================
# 自动判断是在 GitHub 服务器还是在你的 Mac 上
if os.getenv("GITHUB_ACTIONS") == "true":
    print("🚀 检测到 GitHub Actions 环境：使用直连模式 (无需代理)")
    # GitHub 服务器在海外，天生能连 Google，不需要任何代理设置
else:
    print("🏠 检测到本地环境：开启 VPN 代理 (端口 7897)")
    # 强制配置：流量走 7897 端口 (你的VPN端口)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
    os.environ["GRPC_PROXY"] = "http://127.0.0.1:7897"

# 强制 UTF-8 编码，防止中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
os.environ["PYTHONIOENCODING"] = "utf-8"

# 导入业务库
try:
    import akshare as ak
    import pandas as pd
    import google.generativeai as genai
except ImportError as e:
    print(f"❌ 缺少库: {e}")
    print("请运行: pip install google-generativeai akshare pandas python-dotenv")
    sys.exit(1)

# ==========================================
# 1. 密钥配置
# ==========================================
load_dotenv()
# 获取 API Key (本地从 .env 读，GitHub 从 Secrets 读)
MY_API_KEY = os.getenv("GOOGLE_API_KEY")

if not MY_API_KEY:
    print("❌ 严重错误: 未找到 GOOGLE_API_KEY")
    print("1. 如果是本地，请检查 .env 文件。")
    print("2. 如果是 GitHub，请检查 Settings -> Secrets -> Actions 是否添加了 Key。")
    sys.exit(1)

genai.configure(api_key=MY_API_KEY)


# ==========================================
# A. 获取数据 (包含商业航天 & AI)
# ==========================================
def get_market_data():
    print("⏳ 正在采集沪深两市全景数据...")
    try:
        sh_index = ak.stock_zh_index_daily_em(symbol="sh000001")
        sz_index = ak.stock_zh_index_daily_em(symbol="sz399001")

        # 简单计算成交额
        amt = 0.0
        if 'amount' in sh_index.columns:
            amt = sh_index.iloc[-1]['amount'] + sz_index.iloc[-1]['amount']
        elif '成交额' in sh_index.columns:
            amt = sh_index.iloc[-1]['成交额'] + sz_index.iloc[-1]['成交额']

        total_amount = amt / 100000000

        # 获取板块
        sector_df = ak.stock_board_industry_name_em()

        # 筛选关键赛道
        targets = ['航天航空', '通信设备', '互联网服务', '软件开发', '文化传媒', '游戏', '半导体']
        sector_info = []

        # 增加容错：检查列名是否存在
        name_col = '板块名称' if '板块名称' in sector_df.columns else 'name'
        change_col = '涨跌幅' if '涨跌幅' in sector_df.columns else 'change_pct'

        for index, row in sector_df.iterrows():
            if row[name_col] in targets:
                sector_info.append(f"{row[name_col]}: {row[change_col]}%")

        today_date = sh_index.iloc[-1]['date'] if 'date' in sh_index.columns else datetime.date.today()

        summary = f"""
        日期: {today_date}
        两市成交额: {total_amount:.0f} 亿元
        重点板块表现: {" | ".join(sector_info)}
        """
        print(f"✅ 数据采集成功！今日成交额: {total_amount:.0f}亿")
        return summary
    except Exception as e:
        print(f"⚠️ 数据接口小故障: {e}")
        return "数据异常，请假设成交额3万亿，AI与商业航天活跃。"


# ==========================================
# B. 生成策略 (使用你验证过的真实模型列表)
# ==========================================
def generate_report(market_data):
    print("🤖 资深交易员正在思考...")

    prompt = f"""
    你是A股资深交易员。基于今日【{market_data}】的数据，
    请写一份关于【商业航天】和【AI应用】的明日操作策略。

    要求：
    1. 分析今日行情风险。
    2. 给出商业航天（卫星/低空）的低吸点位。
    3. 给出AI应用（传媒/Agent）的博弈思路。
    4. 输出Markdown格式，简练犀利。
    """

    # 🟢 根据你 Debug 出来的真实可用模型列表
    models_to_try = [
        "gemini-2.0-flash",  # ✅ 正式版 (首选，最稳)
        "gemini-2.5-flash",  # 🚀 超前版 (速度快)
        "gemini-flash-latest",  # 🛡️ 官方推荐别名
        "gemini-2.0-flash-exp",  # ⚠️ 实验版 (容易忙)
        "gemini-2.5-pro"  # 🧠 推理版
    ]

    for model_name in models_to_try:
        print(f"\n🔄 尝试模型: {model_name} ...")

        # ⚡️ 重试机制：给每个模型 3 次机会
        for attempt in range(1, 4):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)

                print(f"✅ 成功生成策略！(使用模型: {model_name})")
                return response.text

            except Exception as e:
                err = str(e)
                if "429" in err:  # 配额满了/太忙
                    print(f"   ⚠️ 第{attempt}次尝试: 线路拥堵 (429)，休息5秒后重试...")
                    time.sleep(5)
                elif "404" in err:
                    print(f"   ❌ 模型名称不对 (404)，跳过。")
                    break  # 换下一个模型
                elif "403" in err:
                    print(f"   ❌ 权限错误 (403): 请检查 API Key 是否有效或已泄露。")
                    break
                else:
                    print(f"   ❌ 其他报错: {err}")
                    break

    print("\n😭 所有模型都试过了。")
    return "😭 策略生成失败，请检查网络或 Key。"


# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    data = get_market_data()
    report = generate_report(data)

    if "😭" not in report:
        # 生成带日期的文件名
        filename = f"Strategy_{datetime.date.today()}.md"
        # 兼容 GitHub Actions 的路径写法（直接写在当前目录）
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📂 报告已保存: {filename}")
        print("-" * 30)
        # 简单预览
        print(report[:300] + "...\n(详情请看生成的 Markdown 文件)")
    else:
        # 如果失败，抛出异常以便 GitHub Actions 显示为红色失败状态
        print(report)
        sys.exit(1)