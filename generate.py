"""
互联网安全周报 — 本地测试脚本
用法:
    python generate.py          # 单次执行（测试模式）
    python generate.py --now    # 同上
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from openai import OpenAI

# === 配置 ===
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(PROJECT_DIR, "prompt.txt")
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports")
API_BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"


def load_prompt() -> str:
    """读取提示词文件"""
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"提示词文件不存在: {PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def get_date_range() -> str:
    """获取本周日期范围字符串"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    return f"{week_ago.strftime('%Y年%m月%d日')} -- {today.strftime('%Y年%m月%d日')}"


def clean_html(raw: str) -> str:
    """清理 AI 返回的 HTML（去掉可能的 markdown 代码块包裹）"""
    content = raw.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def generate_report(api_key: str) -> str:
    """调用 DeepSeek API 生成周报 HTML"""
    system_prompt = load_prompt()
    date_range = get_date_range()

    client = OpenAI(api_key=api_key, base_url=API_BASE_URL)

    print(f"[*] 正在调用 DeepSeek API ({MODEL})...")
    print(f"[*] 日期范围: {date_range}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请生成本周（{date_range}）的网络安全周报 HTML 页面。直接输出完整 HTML，不要用 markdown 代码块包裹。",
            },
        ],
        temperature=0.3,
        max_tokens=16384,
    )

    raw = response.choices[0].message.content
    return clean_html(raw)


def save_report(html: str) -> str:
    """保存 HTML 到 reports/ 目录"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"weekly_report_{today}.html"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def main():
    parser = argparse.ArgumentParser(description="互联网安全周报生成器（本地测试）")
    parser.add_argument("--now", action="store_true", help="立即生成一份周报（默认行为）")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置环境变量 DEEPSEEK_API_KEY")
        print("  请先执行: set DEEPSEEK_API_KEY=your-key  (Windows)")
        print("  或:      export DEEPSEEK_API_KEY=your-key  (Linux/Mac)")
        sys.exit(1)

    try:
        html = generate_report(api_key)
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        sys.exit(1)

    filepath = save_report(html)
    print(f"✅ 报告已生成: {filepath}")
    print(f"   文件大小: {len(html)} 字符")


if __name__ == "__main__":
    main()
