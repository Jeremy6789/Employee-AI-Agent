import os
import asyncio
import json
import time
from dotenv import load_dotenv, find_dotenv
from flask_socketio import SocketIO
from google import genai
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage

# ✅ 載入 .env 並啟用 Gemini 原生用法
dotenv_path = find_dotenv()
print(f"✅ 目前使用的 .env 路徑: {dotenv_path}")
load_dotenv(dotenv_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(GEMINI_API_KEY)

# ✅ 使用 Gemini 原生 client
client = genai.Client(api_key=GEMINI_API_KEY)

# ✅ 封裝成符合 autogen agentchat 的結構
class GeminiChatCompletionClient:
    def __init__(self, model="gemini-1.5-flash-8b"):
        self.model = model
        self.model_info = {"vision": False}  # ✅ 避免 autogen 出錯

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
        #print("📨 Gemini 回應內容：", response)
        return type("Response", (), {
            "text": response.text,
            "content": response.text,
            "usage": {
                "prompt_tokens": {"value": 0},
                "completion_tokens": {"value": 0}
            }
        })

# ✅ 初始化封裝後的 Gemini client
model_client = GeminiChatCompletionClient()

# ✅ 實現兩個 AI Agent 互動分析，使用模擬流式輸出的方式
async def interactive_two_agent_analysis(socketio: SocketIO, dept_id, employee_data):
    # 基本統計數據
    avg_satisfaction = employee_data["員工滿意度評分"].mean()
    min_satisfaction = employee_data["員工滿意度評分"].min()
    max_satisfaction = employee_data["員工滿意度評分"].max()
    
    # 低滿意度員工比例
    low_satisfaction_count = len(employee_data[employee_data["員工滿意度評分"] <= 2])
    low_satisfaction_percentage = (low_satisfaction_count / len(employee_data)) * 100
    
    # 隨機選擇代表性反饋作為樣本
    if len(employee_data) > 5:
        sample = employee_data.sample(5)
    else:
        sample = employee_data
    
    sample_feedback = []
    for _, row in sample.iterrows():
        sample_feedback.append(f"員工 {row['員工ID']} (評分 {row['員工滿意度評分']}): {row['近期反饋內容']}")
    
    # 第一個 Agent（HR 分析專家）的提示
    analyst_prompt = f"""
    作為人力資源分析專家，請根據以下員工滿意度數據進行詳細分析：
    
    部門: {dept_id}
    整體滿意度分析:
    - 平均滿意度評分: {avg_satisfaction:.2f}/5
    - 最低評分: {min_satisfaction}/5
    - 最高評分: {max_satisfaction}/5
    - 低滿意度員工比例: {low_satisfaction_percentage:.1f}%
    
    員工反饋樣本:
    {json.dumps(sample_feedback, ensure_ascii=False, indent=2)}
    
    請提供詳細的分析，包括:
    1. 關鍵問題識別
    2. 滿意度分佈模式分析
    3. 員工反饋的主要主題和趨勢
    
    請保持專業分析的語氣，並註明數據支持的觀點。
    """
    
    socketio.emit('update', {
        'message': '🤖 [HR分析專家] 正在分析員工滿意度數據...',
        'source': 'hr_analyst',
        'tag': 'analysis'
    })
    
    # 模擬延遲，讓用戶感知到實時分析過程
    await asyncio.sleep(1.5)
    
    # 第一個 Agent（HR 分析專家）生成分析
    try:
        response1 = client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=analyst_prompt
        )
        
        analysis = response1.text.strip()
        
        # 緩慢地發送分析結果，模擬實時生成效果
        segments = analysis.split('\n\n')
        for i, segment in enumerate(segments):
            if segment.strip():
                socketio.emit('update', {
                    'message': f"🤖 [HR分析專家]：{segment}",
                    'source': "hr_analyst",
                    'tag': 'analysis'
                })
                # 短暫延遲，模擬流式輸出
                await asyncio.sleep(0.8)
        
        # 第二個 Agent（HR 顧問）的提示，包含第一個 Agent 的分析
        consultant_prompt = f"""
        作為人力資源顧問，請基於分析專家的以下分析結果，提供具體的改善建議：
        
        部門: {dept_id}
        分析專家的發現:
        {analysis}
        
        請針對上述分析提供:
        1. 優先級最高的三個問題
        2. 每個問題的具體解決方案
        3. 短期和長期的改善計劃
        4. HR 部門應該採取的行動步驟
        
        請保持建設性和可行性，並在回答最後以「最終建議：」開頭總結你的核心建議。
        """
        
        socketio.emit('update', {
            'message': '🤖 [HR顧問] 正在根據分析結果生成改善建議...',
            'source': 'hr_consultant',
            'tag': 'analysis'
        })
        
        # 短暫延遲，增強互動感
        await asyncio.sleep(1.5)
        
        # 第二個 Agent（HR 顧問）生成建議
        response2 = client.models.generate_content(
            model="gemini-1.5-flash-8b", 
            contents=consultant_prompt
        )
        
        recommendations = response2.text.strip()
        
        # 緩慢地發送建議結果，模擬實時生成效果
        segments = recommendations.split('\n\n')
        for i, segment in enumerate(segments):
            if segment.strip():
                socketio.emit('update', {
                    'message': f"🤖 [HR顧問]：{segment}",
                    'source': "hr_consultant",
                    'tag': 'analysis'
                })
                # 短暫延遲，模擬流式輸出
                await asyncio.sleep(0.8)
        
        # 提取最終建議
        if "最終建議：" in recommendations:
            final_recommendation = recommendations.split("最終建議：")[-1].strip()
            socketio.emit('suggestions', {'suggestions': final_recommendation})
        else:
            # 如果沒有找到最終建議標記，生成一個簡短總結
            summary_prompt = f"""
            請總結以下分析和建議的核心要點，並提出最重要的3點行動建議：
            
            分析：{analysis}
            
            建議：{recommendations}
            """
            
            summary_response = client.models.generate_content(
                model="gemini-1.5-flash-8b",
                contents=summary_prompt
            )
            
            summary = summary_response.text.strip()
            socketio.emit('suggestions', {'suggestions': summary})
            
    except Exception as e:
        socketio.emit('update', {
            'message': f'❌ 分析過程出錯: {str(e)}',
            'tag': 'error'
        })

# ✅ 主要分析入口點函數
async def run_multiagent_analysis(socketio: SocketIO, dept_id, employee_data):
    socketio.emit('update', {
        'message': '🤖 系統：正在啟動HR分析專家與HR顧問的協作...',
        'tag': 'analysis'
    })
    try:
        # 使用兩個互動式 Agent 進行分析
        await interactive_two_agent_analysis(socketio, dept_id, employee_data)
    except Exception as e:
        socketio.emit('update', {
            'message': f'❌ 分析過程出現未預期錯誤: {str(e)}',
            'tag': 'error'
        })