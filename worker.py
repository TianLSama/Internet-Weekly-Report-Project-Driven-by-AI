"""
Cloudflare Workers — 互联网安全周报自动生成与服务
- scheduled: 每周五 UTC 2:00 (北京时间 10:00) 自动生成
- fetch: 提供 HTTP 访问，返回最新报告 HTML
"""
import json
from datetime import datetime, timedelta

# ============================================================
# 提示词 — 部署时从 prompt.txt 自动读取，此处为运行时回退
# ============================================================
_SYSTEM_PROMPT = None

def _get_prompt():
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is not None:
        return _SYSTEM_PROMPT
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            _SYSTEM_PROMPT = f.read()
    except Exception:
        _SYSTEM_PROMPT = ""
    return _SYSTEM_PROMPT


# ============================================================
# DeepSeek API 调用
# ============================================================
API_BASE = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"


def _date_range():
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    return f"{week_ago.strftime('%Y年%m月%d日')} -- {today.strftime('%Y年%m月%d日')}"


def _clean_html(raw):
    content = raw.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


async def _call_deepseek(api_key, system_prompt, date_range):
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请生成本周（{date_range}）的网络安全周报 HTML 页面。直接输出完整 HTML，不要用 markdown 代码块包裹。",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 16384,
    })

    resp = await fetch(API_BASE, {
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        "body": body,
    })

    if resp.status != 200:
        error_text = await resp.text()
        raise Exception(f"DeepSeek API error {resp.status}: {error_text}")

    data = await resp.json()
    raw = data["choices"][0]["message"]["content"]
    return _clean_html(raw)


# ============================================================
# Cloudflare Workers 入口
# ============================================================

async def fetch(request, env, ctx):
    """HTTP 请求处理 — 返回最新周报 HTML"""
    try:
        html = await env.REPORT_KV.get("latest")
    except Exception:
        html = None

    if html:
        return Response(html, headers={
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
        })

    return Response(
        "<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'><title>周报</title></head>"
        "<body style='font-family:sans-serif;padding:40px;text-align:center'>"
        "<h1>📋 报告尚未生成</h1><p>请等待周五上午 10:00 自动生成，或联系管理员手动触发。</p>"
        "</body></html>",
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )


async def scheduled(event, env, ctx):
    """定时触发 — 每周五 UTC 2:00 (北京时间 10:00)"""
    api_key = env.DEEPSEEK_API_KEY
    system_prompt = _get_prompt()
    date_range = _date_range()

    try:
        html = await _call_deepseek(api_key, system_prompt, date_range)
        await env.REPORT_KV.put("latest", html)
        print(f"[OK] Report generated for {date_range}")
    except Exception as e:
        print(f"[ERR] {e}")
