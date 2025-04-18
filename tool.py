import os
import subprocess
import pyautogui
import pytesseract
import openai
from openai import OpenAI
from pynput import keyboard
from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext
import threading

load_dotenv()

# 设置你的 OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# 全局维护一个 Tkinter 窗口和标签，用于显示结果
root = tk.Tk()
root.title("分析结果展示")
root.geometry("400x1000")

# 让窗口尽量置顶
root.attributes("-topmost", True)

# 创建一个带滚动条的 ScrolledText
output_text = scrolledtext.ScrolledText(root, wrap='word')
output_text.pack(padx=10, pady=10, fill='both', expand=True)

# 在初始时插入提示文字
output_text.insert('1.0', "等待结果...")

def update_output(text):
    """
    更新窗口中的文字
    """
    # 清空并插入新的文本
    output_text.delete('1.0', 'end')
    output_text.insert('1.0', text)
    # 让窗口重新置顶
    root.attributes("-topmost", True)
    root.update()

def get_front_window_bounds_mac():
    """
    通过 AppleScript 获取当前激活窗口的坐标 (x1, y1, x2, y2).
    返回一个 (x, y, width, height) 元组.
    如果获取失败，则返回 None.
    """
    script = r'''
    tell application "System Events"
        set frontAppName to name of first process whose frontmost is true
    end tell

    tell application frontAppName
        if (count of windows) > 0 then
            set theBounds to bounds of window 1
            return theBounds
        else
            return "NO_WINDOW"
        end if
    end tell
    '''

    result = subprocess.run(["osascript", "-e", script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True)
    output = result.stdout.strip()

    if output == "NO_WINDOW":
        return None

    try:
        coords = list(map(int, output.split(",")))
        if len(coords) == 4:
            x1, y1, x2, y2 = coords
            width = x2 - x1
            height = y2 - y1
            return (x1, y1, width, height)
    except:
        pass

    return None


def screenshot_active_window_mac():
    """
    截取整个屏幕, 返回一个 PIL.Image.Image 对象.
    """
    screenshot = pyautogui.screenshot()
    return screenshot


def analyze_screenshot_via_chatgpt(img):
    """
    对截图进行OCR，然后将识别到的文本发送给ChatGPT进行分析，并打印回复.
    """
    text = pytesseract.image_to_string(img, lang='chi_sim')
    text = text.strip()

    if not text:
        root.after(0, update_output, "截图中没有识别到文字或内容为空。")
        return

    print("OCR 识别到的文字：")
    print(text)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "你是一位java面试专家，精通各种面试问题"},
            {"role": "user", "content": f"以下是我在截图中识别的问题，：\n{text}\n请帮我分析一下。截图比较杂乱，可能包含其他信息，请你提取其中代码相关的问题，给出思路和答案代码"}
        ],
        temperature=0.5
    )

    reply = completion.choices[0].message.content
    root.after(0, update_output, f"ChatGPT 回复：\n{reply}")


def on_hotkey_triggered():
    def worker():
        print("检测到热键，开始截取活动窗口...")
        img = screenshot_active_window_mac()
        if img:
            analyze_screenshot_via_chatgpt(img)
        else:
            root.after(0, update_output, "未能获取到前台窗口，或没有可截取的窗口。")

    threading.Thread(target=worker, daemon=True).start()


def start_hotkey_listener():
    with keyboard.GlobalHotKeys({
        '<ctrl>': on_hotkey_triggered
    }) as h:
        h.join()


def main():
    print("已启动截图分析工具 (macOS)。按 Ctrl+Shift+A 截图并分析。")
    print("请确保已在系统偏好设置里给了屏幕录制 & 辅助功能权限。")

    t = threading.Thread(target=start_hotkey_listener, daemon=True)
    t.start()

    root.mainloop()

if __name__ == "__main__":
    main()