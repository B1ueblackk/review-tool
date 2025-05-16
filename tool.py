"""
backend.py
运行:  python backend.py
然后在 iPad 浏览器打开  http://<LAN_IP>:8000/
"""
import os, asyncio, socket, threading, time
import pyautogui, pytesseract
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from openai import OpenAI
from pynput import keyboard

# ----------------- 配置 -----------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()
latest_msg = "服务器已启动，等待截图…"
latest_analysis = ""  # 存储最近的分析结果
subscribers: set[asyncio.Queue] = set()

# -------- 公用函数：获取局域网 IP --------
def get_local_ip() -> str:
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))      # 不会真的发包
        ip = s.getsockname()[0]
    except Exception:
        pass
    finally:
        s.close()
    return ip

# --------- 把消息推给所有订阅者 ----------
def _notify_all(msg: str):
    for q in list(subscribers):
        try:
            q.put_nowait(msg)
        except (asyncio.QueueFull, RuntimeError):
            subscribers.discard(q)

# -------- 截图→OCR→GPT 处理函数 ----------
def process_screenshot():
    global latest_msg, latest_analysis
    img = pyautogui.screenshot()
    text = pytesseract.image_to_string(img, lang="chi_sim").strip()
    if not text:
        latest_msg = "截图中没有识别到文字或内容为空。"
        _notify_all(latest_msg)
        return

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一位java面试专家，精通各种面试问题"},
            {"role": "user",
             "content": f"以下是我在截图中识别的问题，：\n{text}\n请帮我分析一下。截图比较杂乱，可能包含其他信息，请你提取其中代码相关的问题，给出思路和答案代码，代码可以是比较容易想到的思路，比如暴力，给后续留出改进空间。请你直接提供给我思路，代码和关键解析，不需其他信息。"}
        ],
        temperature=0.5,
    )
    latest_analysis = completion.choices[0].message.content
    latest_msg = latest_analysis
    _notify_all(latest_msg)

# -------- 优化分析处理函数 ----------
def process_optimization():
    global latest_msg
    if not latest_analysis:
        latest_msg = "请先使用 Ctrl+Shift+A 进行问题分析。"
        _notify_all(latest_msg)
        return

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一位java面试专家，精通各种面试问题"},
            {"role": "user",
             "content": f"针对以下解决方案，请提供更好的优化方案，包括代码和思路：\n{latest_analysis}"}
        ],
        temperature=0.5,
    )
    latest_msg = completion.choices[0].message.content
    _notify_all(latest_msg)

# -------- 热键触发处理函数 ----------
def on_hotkey_triggered():
    def worker():
        print("检测到热键，开始截取屏幕...")
        process_screenshot()

    threading.Thread(target=worker, daemon=True).start()

def on_optimization_triggered():
    def worker():
        print("检测到优化热键，开始分析优化方案...")
        process_optimization()

    threading.Thread(target=worker, daemon=True).start()

def start_hotkey_listener():
    with keyboard.GlobalHotKeys({
        '<ctrl>+<shift>+a': on_hotkey_triggered,  # 使用 Ctrl+Shift+A 作为触发键
        '<ctrl>+<shift>+b': on_optimization_triggered  # 使用 Ctrl+Shift+B 作为优化触发键
    }) as h:
        h.join()

# ------------- SSE 端点 -----------------
@app.get("/stream")
async def stream(request: Request):
    q: asyncio.Queue = asyncio.Queue(maxsize=5)
    await q.put(latest_msg)          # 先推一次
    subscribers.add(q)

    async def events():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=30)
                    yield {"event": "message", "data": data}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "keep-alive"}
        finally:
            subscribers.discard(q)

    return EventSourceResponse(events())

# ------------- 静态首页 -----------------
HTML = """
<!DOCTYPE html><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
body {
    font-family: Consolas, "Courier New", monospace;
    white-space: pre-wrap;
    padding: 1em;
    margin: 0;
    background-color: #1a1a1a;
    color: #ffffff;
    font-size: 16px;
    line-height: 1.6;
    min-height: 100vh;
    box-sizing: border-box;
    overflow-x: hidden;
}
pre {
    font-family: Consolas, "Courier New", monospace;
    font-size: 16px;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-width: 100%;
}
@media (max-width: 768px) {
    body {
        font-size: 14px;
        padding: 0.8em;
    }
    pre {
        font-size: 14px;
    }
}
</style>
<pre id=log>等待服务器推送…</pre>
<script>
const log=document.getElementById('log');
const es=new EventSource('/stream');
es.onmessage=e=>{
    log.textContent=e.data;
    // 自动调整字体大小以适应屏幕
    const adjustFontSize = () => {
        const container = document.body;
        const content = log;
        const containerHeight = window.innerHeight;
        const contentHeight = content.scrollHeight;
        
        if (contentHeight > containerHeight) {
            const currentSize = parseInt(window.getComputedStyle(content).fontSize);
            const newSize = Math.floor(currentSize * (containerHeight / contentHeight));
            content.style.fontSize = Math.max(12, newSize) + 'px';
        }
    };
    
    // 初始调整
    adjustFontSize();
    // 监听窗口大小变化
    window.addEventListener('resize', adjustFontSize);
};
es.onerror=e=>console.error(e);
</script>
"""
@app.get("/", response_class=HTMLResponse)
def index(): return HTML

# ------------- 启动 -----------------
def main():
    ip = get_local_ip()
    print("-----------------------------------------------------------")
    print(f"✔ 在局域网设备访问  →  http://{ip}:8000/")
    print("✔ 按 Ctrl+Shift+A 触发截图分析")
    print("✔ 按 Ctrl+Shift+B 获取优化方案")
    print("-----------------------------------------------------------")

    # 启动热键监听
    threading.Thread(target=start_hotkey_listener, daemon=True).start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()