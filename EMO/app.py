import os
import asyncio
import json
import threading
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from google import genai
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from EMPwithSnow import generate_satisfaction_trend_plot

# ✅ 初始化 Flask 與 SocketIO
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, async_mode='threading')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ✅ 載入 .env 並初始化 Gemini
dotenv_path = find_dotenv()
#print(f"✅ 目前使用的 .env 路徑: {dotenv_path}")
load_dotenv(dotenv_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#print(GEMINI_API_KEY)

# ✅ 建立 Gemini 客戶端與模型
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# ✅ 封裝 autogen client
class GeminiChatCompletionClient:
    def __init__(self, model="gemini-1.5-flash-8b"):
        self.model = model
        self.model_info = {"vision": False}

    async def create(self, messages, **kwargs):
        parts = []
        for m in messages:
            if hasattr(m, 'content'):
                parts.append(str(m.content))
            elif isinstance(m, dict) and 'content' in m:
                parts.append(str(m['content']))
        content = "\n".join(parts)
        response = client.models.generate_content(
            model=self.model,
            contents=content
        )
        return type("Response", (), {
            "text": response.text,
            "content": response.text,
            "usage": {
                "prompt_tokens": {"value": 0},
                "completion_tokens": {"value": 0}
            }
        })

model_client = GeminiChatCompletionClient()

# ✅ 多 Agent 分析（保留原來程式碼）
from multiagent import run_multiagent_analysis

# ✅ Flask 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        socketio.emit('update', {'message': '🟢 檔案上傳成功，開始分析中...'})
        threading.Thread(target=background_task, args=(file_path,)).start()
        return 'File uploaded and processing started.', 200

def background_task(file_path):
    try:
        # 確保CSV檔案結構正確
        df = pd.read_csv(file_path)
        
        # 檢查必要欄位是否存在
        required_columns = ["員工ID", "員工滿意度評分", "近期反饋內容"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要欄位: {col}")
        
        # 處理數據，確保格式正確
        df["員工ID"] = df["員工ID"].astype(str)
        df["員工滿意度評分"] = pd.to_numeric(df["員工滿意度評分"], errors="coerce")
        
        # 處理可能的缺失值
        if df["員工滿意度評分"].isna().any():
            df = df.dropna(subset=["員工滿意度評分"])
            socketio.emit('update', {'message': "⚠️ 警告: 有些記錄的滿意度評分無效，已自動過濾"})
        
        if len(df) == 0:
            raise ValueError("處理後沒有有效數據可分析")
            
        dept_id = os.path.splitext(os.path.basename(file_path))[0]
        
        # 生成圖表
        try:
            plot_path = generate_satisfaction_trend_plot(dept_id, df)
            socketio.emit('plot_generated', {'plot_url': '/' + plot_path})
        except Exception as plot_error:
            socketio.emit('update', {'message': f"⚠️ 生成圖表時出錯: {str(plot_error)}，但分析將繼續"})
        
        # 執行多Agent分析
        asyncio.run(run_multiagent_analysis(socketio, dept_id, df))
        
    except ValueError as ve:
        socketio.emit('update', {'message': f"❌ 數據驗證錯誤: {str(ve)}"})
    except pd.errors.ParserError:
        socketio.emit('update', {'message': "❌ CSV檔案格式錯誤，請確認檔案格式正確"})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        socketio.emit('update', {'message': f"❌ 分析過程出現錯誤: {str(e)}"})
        print(f"詳細錯誤: {error_details}")

# 已移除 Gemini 聊天區支援即時回應功能

if __name__ == '__main__':
    socketio.run(app, debug=True)