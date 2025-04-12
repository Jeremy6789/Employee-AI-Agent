import os
from datetime import datetime
import pandas as pd
import gradio as gr
from dotenv import load_dotenv
from fpdf import FPDF
import re
import google.generativeai as genai

# 載入 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro")  # 或 "gemini-1.0-pro"


# 嘗試取得中文字型（Windows）
def get_chinese_font_file() -> str:
    fonts_path = r"C:\Windows\Fonts"
    candidates = ["kaiu.ttf"]  # 你也可以用其他中文字型
    for font in candidates:
        font_path = os.path.join(fonts_path, font)
        if os.path.exists(font_path):
            print("找到中文字型：", font_path)
            return os.path.abspath(font_path)
    print("⚠ 未找到中文字型")
    return None

# 將 DataFrame 輸出成 PDF 表格
def create_table(pdf: FPDF, df: pd.DataFrame):
    available_width = pdf.w - 2 * pdf.l_margin
    num_columns = len(df.columns)
    col_width = available_width / num_columns
    line_height = 6  # 單行高度

    pdf.set_font("ChineseFont", "", 12)

    # 表頭
    pdf.set_fill_color(200, 200, 200)
    for col in df.columns:
        pdf.cell(col_width, line_height * 2, str(col), border=1, align="C", fill=True)
    pdf.ln(line_height * 2)

    fill = False
    for _, row in df.iterrows():
        cell_texts = [str(item) for item in row]

        # 計算每格所需的行數與最大行數
        line_counts = []
        for text in cell_texts:
            lines = pdf.multi_cell(col_width, line_height, text, split_only=True)
            line_counts.append(len(lines))
        max_lines = max(line_counts)
        row_height = max_lines * line_height

        # 換頁檢查
        if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_fill_color(200, 200, 200)
            for col in df.columns:
                pdf.cell(col_width, line_height * 2, str(col), border=1, align="C", fill=True)
            pdf.ln(line_height * 2)

        y_start = pdf.get_y()
        x_start = pdf.get_x()
        pdf.set_fill_color(230, 240, 255) if fill else pdf.set_fill_color(255, 255, 255)

        # 畫格子框線並置中顯示文字
        for i, text in enumerate(cell_texts):
            x = x_start + i * col_width
            pdf.rect(x, y_start, col_width, row_height)  # 畫出格子

            # 計算要顯示的行數
            lines = pdf.multi_cell(col_width, line_height, text, split_only=True)
            total_text_height = len(lines) * line_height
            y_text = y_start + (row_height - total_text_height) / 2  # 垂直置中

            for line in lines:
                pdf.set_xy(x, y_text)
                pdf.cell(col_width, line_height, line, align="C")
                y_text += line_height

        pdf.set_y(y_start + row_height)
        fill = not fill

def generate_pdf(text: str = None, df: pd.DataFrame = None) -> str:
    print("開始生成 PDF")
    pdf = FPDF(format="A4")
    pdf.add_page()
    
    chinese_font_path = get_chinese_font_file()
    if not chinese_font_path:
        return "⚠ 錯誤：無法找到中文字型，請確認系統已安裝。"
    
    pdf.add_font("ChineseFont", "", chinese_font_path, uni=True)
    pdf.set_font("ChineseFont", "", 12)

    if df is not None:
        create_table(pdf, df)
    elif text is not None:
        pdf.multi_cell(0, 10, text)
    else:
        pdf.cell(0, 10, "⚠ 沒有可呈現的內容")

    filename = f"employee_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    print("PDF 生成完成：", filename)
    return filename

# 使用 Gemini API 對每筆員工資料進行分析
def analyze_employee_feedback(df: pd.DataFrame, user_prompt: str, max_batch_size: int = 25, max_rows: int = 50) -> pd.DataFrame:
    # 獲取 CSV 總筆數
    total_rows = len(df)
    
    # 如果筆數小於或等於 max_rows，則不分批，直接處理所有資料
    if total_rows <= max_rows:
        batch_size = total_rows  # 不分批，直接處理所有資料
    else:
        batch_size = max_batch_size  # 超過 max_rows，分批處理
    
    results = []
    
    # 根據批次大小進行資料分批處理
    for start in range(0, min(total_rows, max_rows), batch_size):
        batch = df.iloc[start:start + batch_size]
        combined_prompt = "請針對以下每筆資料進行分析，回傳格式請嚴格遵守：\n員工ID: XXX\n情緒分數: 整數分數\n改善建議: 建議內容\n\n"
        
        for _, row in batch.iterrows():
            combined_prompt += (
                f"員工ID: {row['員工ID']}\n"
                f"滿意度評分: {row['員工滿意度評分']}\n"
                f"反饋內容: {row['近期反饋內容']}\n\n"
            )
        
        try:
            response = model.generate_content(combined_prompt)
            lines = response.text.strip().split("\n")
            
            temp_result = {}
            for line in lines:
                if line.startswith("員工ID"):
                    if temp_result:
                        results.append(temp_result)
                        temp_result = {}
                    temp_result["員工ID"] = line.split(":", 1)[1].strip()
                elif line.startswith("情緒分數"):
                    temp_result["情緒分數"] = int(re.search(r"\d+", line).group())
                elif line.startswith("改善建議"):
                    temp_result["改善建議"] = line.split(":", 1)[1].strip()
            
            if temp_result:
                results.append(temp_result)

        except Exception as e:
            print(f"分析失敗：{e}")
            for _, row in batch.iterrows():
                results.append({
                    "員工ID": row["員工ID"],
                    "情緒分數": "分析失敗",
                    "改善建議": "API 發生錯誤或額度不足"
                })

    # 合併原始資料
    result_df = pd.DataFrame(results)
    merged_df = pd.merge(df, result_df, on="員工ID", how="left")
    return merged_df

# Gradio 處理函式
def gradio_handler(csv_file, user_prompt):
    if csv_file is not None:
        df = pd.read_csv(csv_file.name)
        result_df = analyze_employee_feedback(df, user_prompt)
        pdf_path = generate_pdf(df=result_df)
        summary_text = result_df[["員工ID", "情緒分數", "改善建議"]].to_string(index=False)
        return summary_text, pdf_path
    else:
        return "⚠ 請上傳包含 員工ID、滿意度、反饋內容 的 CSV。", None

# 預設分析提示
default_prompt = """根據以下每筆員工的滿意度評分與反饋內容，請回傳每筆資料的情緒分數（0~100）以及一句具體的改善建議。請遵守以下格式來回答每筆員工的資料：
                    員工ID: [員工ID]
                    情緒分數: [情緒分數]
                    改善建議: [改善建議]"""

# Gradio 介面
with gr.Blocks() as demo:
    gr.Markdown("# 🧠 員工滿意度分析報表生成器")
    with gr.Row():
        csv_input = gr.File(label="📂 上傳員工 CSV 檔案")
        user_input = gr.Textbox(label="📝 自訂分析提示", lines=6, value=default_prompt)
    output_text = gr.Textbox(label="📊 分析摘要", interactive=False, lines=15)
    output_pdf = gr.File(label="📄 下載 PDF 報表")
    submit_button = gr.Button("🚀 開始分析")
    submit_button.click(fn=gradio_handler, inputs=[csv_input, user_input],
                        outputs=[output_text, output_pdf])

demo.launch()