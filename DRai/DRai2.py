import os
import json
import time
import pandas as pd
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import BlockedPromptException

# 載入 API 金鑰
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

#HW2
def summarize_feedback_batch(feedbacks, scores):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = "請根據以下每筆員工回饋與滿意度，用一句話總結並判斷是正面還是負面，輸出格式為：\n\n" \
                 "員工ID：XXX\n反饋總結：XXX\n正負面評分：正面/負面\n\n"

        for i in range(len(feedbacks)):
            prompt += f"員工ID：{feedbacks[i]['id']}\n近期反饋：「{feedbacks[i]['text']}」，滿意度為 {feedbacks[i]['score']} 分。\n\n"

        response = model.generate_content(prompt)

        result_blocks = response.text.strip().split("\n\n")
        parsed_results = []
#HW2
        for block in result_blocks:
            emp_id, summary, sentiment = "", "", ""
            for line in block.strip().splitlines():
                if line.startswith("員工ID："):
                    emp_id = line.replace("員工ID：", "").strip()
                elif line.startswith("反饋總結："):
                    summary = line.replace("反饋總結：", "").strip()
                elif line.startswith("正負面評分："):
                    sentiment = line.replace("正負面評分：", "").strip()
#HW2
            parsed_results.append({
                "員工ID": emp_id,
                "正負面評分": sentiment,
                "反饋總結": summary
            })

        return parsed_results

    except Exception as e:
        print("⚠️ API 呼叫失敗：", e)
        # 若整批失敗，可為每筆生成失敗紀錄
        return [{"員工ID": fb["id"], "正負面評分": "", "反饋總結": "分析失敗"} for fb in feedbacks]



def main():
    if len(sys.argv) < 2:
        print("用法：python employee_summary_bot.py <CSV路徑>")
        return

    input_csv = sys.argv[1]
    output_csv = "employee_feedback_summary.csv"

    df = pd.read_csv(input_csv)
    results = []

    batch_size = 25
    results = []

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        print(f"\n🔄 處理第 {i+1} 到 {i+len(batch)} 筆...")
#HW2
        batch_input = []
        for _, row in batch.iterrows():
            batch_input.append({
                "id": row["員工ID"],
                "text": row["近期反饋內容"],
                "score": row["員工滿意度評分"]
            })

        batch_result = summarize_feedback_batch(batch_input, None)
        results.extend(batch_result)

        time.sleep(2)



    output_df = pd.DataFrame(results)
    output_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"分析完成！結果已寫入 {output_csv}")

if __name__ == "__main__":
    main()
