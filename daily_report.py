# ==========================================
# 0. 强制解决 Mac/Linux 编码错误的魔法代码 (必须放在最前面)
# ==========================================
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # 兼容旧版 Python
os.environ["PYTHONIOENCODING"] = "utf-8"

# ==========================================
# 正式代码开始
# ==========================================
import akshare as ak
from google import genai
import datetime
import time
import pandas as pd

# 🔴 配置区域
MY_API_KEY = "AIzaSyBBFCB27qbU8vKSQuwJl7UpD4DPvizell0"


# ==========================================
# 1. 获取深度市场数据 (修复数据源)
# ==========================================
def get_market_data():
    print("⏳ 正在采集沪深两市全景数据...")
    try:
        # --- A. 获取大盘指数 (切换到东方财富源 _em) ---
        # 上证指数 (sh000001)
        sh_index = ak.stock_zh_index_daily_em(symbol="sh000001")
        sh_latest = sh_index.iloc[-1]

        # 深证成指 (sz399001)
        sz_index = ak.stock_zh_index_daily_em(symbol="sz399001")
        sz_latest = sz_index.iloc[-1]

        # 东方财富的 amount 单位通常已经是“元”
        # 我们把它们加起来，除以 1亿 得到“亿元”
        # 注意：有时候接口返回字段名可能是 "amount" 或 "成交额"
        # 这里做一个简单的容错处理
        if 'amount' in sh_latest:
            sh_amount = sh_latest['amount']
            sz_amount = sz_latest['amount']
        else:
            # 尝试中文列名 (AkShare有时候会返回中文列名)
            sh_amount = sh_latest.get('成交额', 0)
            sz_amount = sz_latest.get('成交额', 0)

        total_amount = (float(sh_amount) + float(sz_amount)) / 100000000

        # --- B. 获取重点板块资金流向 ---
        sector_df = ak.stock_board_industry_name_em()

        # 1. 领涨板块
        top_gainers = sector_df.sort_values(by="涨跌幅", ascending=False).head(3)
        top_gainers_str = ", ".join([f"{row['板块名称']}(+{row['涨跌幅']}%)" for _, row in top_gainers.iterrows()])

        # 2. 科技赛道监控
        tech_keywords = ['半导体', '软件开发', '消费电子', '计算机设备']
        tech_data_list = []
        for index, row in sector_df.iterrows():
            if row['板块名称'] in tech_keywords:
                tech_data_list.append(f"{row['板块名称']}: 涨幅{row['涨跌幅']}%, 换手{row['换手率']}%")

        tech_status_str = " | ".join(tech_data_list)

        data_summary = f"""
        【A股收盘数据】
        日期: {sh_latest['date']}
        上证指数: {sh_latest['close']}
        两市总成交额: {total_amount:.2f} 亿元 (8000亿是枯荣线，1.5万亿是过热线)

        【今日领涨】
        {top_gainers_str}

        【科技板块监控】
        {tech_status_str}
        """
        print(f"✅ 数据采集成功！今日成交额: {total_amount:.2f}亿")
        return data_summary

    except Exception as e:
        print(f"⚠️ 数据接口异常: {e}")
        # 打印一下列名，方便调试
        try:
            print(f"当前获取到的列名: {sh_index.columns}")
        except:
            pass
        return f"数据获取遇到阻碍 ({e})，请AI基于模糊逻辑分析风险。"


# ==========================================
# 2. 智能 AI 策略生成
# ==========================================
def generate_report(market_data):
    print("🤖 资深交易员正在制定交易计划...")
    client = genai.Client(api_key=MY_API_KEY)

    prompt = f"""
    你是一位华尔街出身的量化对冲基金经理，现在专注于A股市场。
    请根据今天的收盘数据，写一份【深度复盘与交易指令】。

    输入数据：
    {market_data}

    ---

    请严格按照以下 Markdown 格式输出：

    # 📊 A股资金复盘 (Emoji标题)
    * **市场定性**：用一句话判断今日市场情绪（例如：缩量诱多、放量突破、情绪退潮）。
    * **成交额分析**：重点点评今日“两市总成交额”。如果低于8000亿，强调流动性枯竭风险；如果高于1.5万亿，强调过热风险。
    * **主力动向**：结合【领涨板块】和【科技赛道监控】数据，分析主力资金是在“高切低”还是“抱团主线”。

    # 🚀 科技股实战交易计划 (重点)
    *基于今日盘面，假设我依然看好泛科技（半导体/AI）方向，请制定明日计划：*

    ### 1. 买入信号确认 (Buy Triggers)
    *(请列出3个具体的右侧买入条件，例如：量能放大及均线形态)*
    * ✅ 信号一：
    * ✅ 信号二：
    * ✅ 信号三：

    ### 2. 风控设定位 (Risk Management)
    * **动态止损 (Stop Loss)**：(请基于ATR或关键均线，给出一个具体的止损逻辑，例如：跌破5日线或回撤超过X%)
    * **分批止盈 (Take Profit)**：(给出止盈策略，例如：乖离率过大时减仓一半)

    ### 3. 极端行情预案 (Emergency Plan)
    * **Scenario**：如果买入后，明日遭遇主力“假突破真砸盘”，跌破关键支撑位（如20日线）且成交量异常放大。
    * **Action**：(请用祈使句给出明确的应对指令，如“无条件清仓”或“锁仓做T”)

    ---
    *Disclaimer: 本报告由AI辅助生成，不构成投资建议。*
    """

    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
    ]

    for model_name in candidate_models:
        print(f"🔄 正在尝试模型: {model_name} ...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            print(f"✅ 成功！使用模型 [{model_name}] 生成了策略。")
            return response.text

        except Exception as e:
            # 打印简化的错误信息，避免满屏乱码
            error_msg = str(e)
            if "ascii" in error_msg:
                print(f"   ⚠️ {model_name}: 编码错误 (已尝试自动修复，如仍报错请检查终端设置)")
            elif "429" in error_msg:
                print(f"   ⚠️ {model_name}: 配额耗尽")
            else:
                print(f"   ⚠️ {model_name}: 其他错误")
            time.sleep(1)
            continue

    return "😭 策略生成失败。"


# ==========================================
# 主程序
# ==========================================
if __name__ == "__main__":
    if "AIza" not in MY_API_KEY:
        print("❌ 错误：请先填入 API Key！")
    else:
        data = get_market_data()
        report = generate_report(data)

        print("\n" + "=" * 40)
        print(report)
        print("=" * 40)

        # 存文件
        filename = f"Strategy_{datetime.date.today()}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📂 交易计划已保存为: {filename}")