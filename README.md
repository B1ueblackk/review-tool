# review-tool
## 🛠 使用说明

1. 克隆本项目到本地：

   ```bash
   git clone https://github.com/B1ueblackk/review-tool.git
   
2. 安装依赖
   ```bash
   pip install -r requirements.txt
3. 安装 Tesseract OCR
* macOS: ```brew install tesseract```
* Ubuntu: ```sudo apt install tesseract-ocr ```
* windows: 下载 https://github.com/tesseract-ocr/tesseract 并配置环境变量
4. 创建 .env 文件，加入你的 OpenAI API 密钥
OPENAI_API_KEY=你的OpenAI密钥
5.	运行后端
python backend.py
6.	在 iPad 或任意浏览器中打开
http://<你的局域网IP>:8000/
7. 功能热键
   * Ctrl + Shift + A：截图并分析面试题 
   * Ctrl + Shift + B：对上一题的方案进行优化分析

本项目仅供学习与个人研究使用，不适用于真实面试或招聘场景。作者不对内容的准确性或适用性承担任何责任，请自行判断是否使用。   
This project is for learning purposes only and should not be used in real interview or hiring situations.