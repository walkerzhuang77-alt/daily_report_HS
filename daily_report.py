import os
import sys
import time
import datetime
import traceback
from dotenv import load_dotenv

# ==========================================
# 0. 智能网络配置
# ==========================================
if os.getenv("GITHUB_ACTIONS") == "true":
    print("🚀 检测到 GitHub Actions 环境：使用直连模式")
else:
    print("🏠 检测到本地环境：开启 VPN 代理 (端口 7897)")
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
    os.environ["GRPC_PROXY"] = "http://127.0.0.1:7897"

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    import akshare as ak
    import pandas as pd
    import google.generativeai as genai
except ImportError as e:
    print(f"❌ 缺少库: {e}")
    sys.exit(1)

# ==========================================
# 1. 配置加载
# ==========================================
load_dotenv()
MY_API_KEY = os.getenv("GOOGLE_API_KEY")

if not MY_API_KEY:
    print("❌ 严重错误: 未找到 GOOGLE_API_KEY")
    sys.exit(1)

genai.configure(api_key=MY_API_KEY)

# ==========================================
# 2. 核心赛道配置 (用户指定)
# ==========================================
SECTOR_MAPPING = {
    '商业航天': '航天航空',
    '工业金属': '工业金属',
    '消费电子': '消费电子',
    '通信设备': '通信设备',
    '通用设备': '通用设备',
    '半导体': '半导体',
    '专用设备': '专用设备',
    '化学制品': '化学制品',
    '电池': '电池',
    '电力': '电力行业',
    '汽车零部件': '汽车零部件',
    '小金属': '小金属'
}


# ==========================================
# A. 获取精准数据
# ==========================================
def get_market_data():
    print("⏳ 正在采集全景数据...")
    try:
        sh_index = ak.stock_zh_index_daily_em(symbol="sh000001")
        sz_index = ak.stock_zh_index_daily_em(symbol="sz399001")

        last_sh = sh_index.iloc[-1]
        last_sz = sz_index.iloc[-1]

        # 计算成交额 (亿)
        try:
            amt = last_sh['amount'] + last_sz['amount']
        except:
            amt = last_sh['成交额'] + last_sz['成交额']

        total_amount = amt / 100000000

        # 获取所有板块数据
        sector_df = ak.stock_board_industry_name_em()

        # 字段兼容处理
        name_col = '板块名称' if '板块名称' in sector_df.columns else 'name'
        change_col = '涨跌幅' if '涨跌幅' in sector_df.columns else 'change_pct'

        # 筛选目标赛道
        target_data = []
        real_names = list(SECTOR_MAPPING.values())

        for index, row in sector_df.iterrows():
            if row[name_col] in real_names:
                user_name = [k for k, v in SECTOR_MAPPING.items() if v == row[name_col]][0]
                target_data.append(f"{user_name}({row[name_col]}): {row[change_col]}%")

        # 判断当前时间段
        current_hour = datetime.datetime.now().hour + 8  # GitHub是UTC时间
        if os.getenv("GITHUB_ACTIONS") != "true":
            current_hour = datetime.datetime.now().hour

        report_type = "午盘复盘" if current_hour < 14 else "收盘复盘"

        summary = {
            "type": report_type,
            "date": str(last_sh['date']),
            "amount": f"{total_amount:.0f} 亿元",
            "index_change": f"上证 {last_sh.get('change_pct', 0) if 'change_pct' in last_sh else 'N/A'}%",
            "sectors": " | ".join(target_data)
        }

        print(f"✅ 数据采集成功！[{report_type}] 成交额: {total_amount:.0f}亿")
        return summary

    except Exception as e:
        print(f"⚠️ 数据接口异常: {e}")
        return {
            "type": "数据异常模式",
            "date": str(datetime.date.today()),
            "amount": "接口获取失败",
            "index_change": "未知",
            "sectors": "需人工核对"
        }


# ==========================================
# B. 生成深度策略
# ==========================================
def generate_report(data):
    print("🤖 资深交易员正在深度复盘...")

    # 根据时间段定制 Prompt
    if "午盘" in data['type']:
        time_logic = "重点分析上午的承接力度，量能是否足以支撑午后反攻？如有跳水，是机会还是风险？"
        action_guide = "给出【午后】的具体操作：是开新仓、做T还是减仓防守？"
    else:
        time_logic = "重点分析全天资金流向，尾盘是否有抢筹或砸盘迹象？隔日溢价预期如何？"
        action_guide = "给出【明日】的竞价关注点和核心操作策略。"

    # 🟢 关键Prompt保持不变
    prompt = f"""
    【角色设定】
    你是一位拥有20年A股经验的资深游资操盤手，擅长情绪周期判断、题材轮动和龙头战法。你的风格是：语言犀利、逻辑严密、不说废话、只讲干货。

    【今日盘面数据】
    - 复盘类型：{data['type']}
    - 两市成交：{data['amount']} (量能是关键，判断是缩量还是放量)
    - 核心赛道表现：
    {data['sectors']}

    【任务要求】
    请基于上述数据，写一份深度的操盘内参。请严格按照以下 Markdown 格式输出：

    # 🚀 {data['type']}：市场情绪与核心策略

    ## I. 盘面核心逻辑拆解
    * **量能定性**：当前成交额意味着什么？（主力出逃 vs 增量进场 vs 缩量洗盘）。
    * **情绪风向**：赛道分化情况，资金是在进攻还是防守？{data['index_change']}。

    ## II. 核心赛道深度扫描 (重点分析以下板块)
    *请结合数据，挑选 2-3 个表现最亮眼或最异常的板块进行点评*
    * **商业航天/卫星/低空**：(逻辑演绎及持续性判断)
    * **科技主线 (半导体/消费电子/通信)**：(机构资金态度，是出货还是调仓？)
    * **周期/新能源 (金属/电池/电力)**：(是否有轮动补涨机会？)

    ## III. 交易员实战策略 ({action_guide})
    * **仓位建议**：(例如：5成仓滚动 / 空仓观望 / 满仓博弈)
    * **操作方向**：
        * **进攻端**：如果看好，具体的低吸点位或打板逻辑是什么？
        * **防守端**：什么信号出现必须止损或止盈？
    * **核心博弈思路**：针对当前赛道列表，哪一个是明天的胜负手？

    **注意：拒绝模棱两可的废话。像交易员一样思考，直接给出判断。**
    """

    # 🟢 修改部分：更新为您账号实测可用的最强模型列表
    models_to_try = [
        "gemini-2.5-flash",  # 🚀 速度最快且新
        "gemini-2.5-pro",  # 🧠 逻辑推理最强
        "gemini-2.0-flash",  # ✅ 稳定版
        "gemini-2.0-flash-exp"  # ⚠️ 备用
    ]

    for model_name in models_to_try:
        print(f"\n🔄 尝试模型: {model_name} ...")
        # 增加重试次数
        for attempt in range(1, 4):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                print(f"✅ 策略生成完毕！(使用模型: {model_name})")
                return response.text
            except Exception as e:
                err = str(e)
                # 优化报错显示，不再静默失败
                if "429" in err:
                    print(f"   ⚠️ (尝试{attempt}) 太忙了(429)，休息5秒...")
                    time.sleep(5)
                elif "404" in err:
                    print(f"   ❌ 模型名 {model_name} 不对，跳过。")
                    break
                elif "403" in err:
                    print(f"   ❌ 权限错误 (403): API Key 可能无效。")
                    break
                else:
                    print(f"   ❌ (尝试{attempt}) 报错: {err}")
                    time.sleep(2)

    return "😭 所有模型都失败了，请检查网络或 Key。"


# ==========================================
# 主程序
# ==========================================
if __name__ == "__main__":
    data = get_market_data()
    report = generate_report(data)

    if "😭" not in report:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H")
        filename = f"Strategy_{timestamp}.md"

        # 兼容 GitHub Actions，同时保存为 report.md 方便邮件发送
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(report)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📂 报告已保存: {filename}")
        print("-" * 30)
        print(report[:200] + "...")
    else:
        print(report)
        sys.exit(1)
