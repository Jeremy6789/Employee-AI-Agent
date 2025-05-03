import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from snownlp import SnowNLP
matplotlib.use('Agg')
matplotlib.rc('font', family='Microsoft JhengHei')

def generate_satisfaction_trend_plot(dept_id, employee_data):
    output_dir = "static/satisfactiontrend"
    os.makedirs(output_dir, exist_ok=True)
    
    # 確保員工ID是字串型態
    employee_data["員工ID"] = employee_data["員工ID"].astype(str)
    
    # 轉換滿意度評分為數字
    employee_data["員工滿意度評分"] = pd.to_numeric(employee_data["員工滿意度評分"], errors="coerce")
    
    # 用 snownlp 對反饋內容進行情緒分析，映射至 1~5（與滿意度評分同尺度）
    employee_data["反饋情緒分析"] = employee_data["近期反饋內容"].apply(lambda text: SnowNLP(text).sentiments * 4 + 1)
    
    # 計算兩者平均
    avg_satisfaction = employee_data["員工滿意度評分"].mean()
    avg_sentiment = employee_data["反饋情緒分析"].mean()
    
    # 創建資料框來排序顯示
    plot_data = employee_data.sort_values("員工滿意度評分", ascending=False)
    
    plt.figure(figsize=(14, 7))
    
    # 長條圖與散點圖
    x = range(len(plot_data))
    plt.bar(x, plot_data["員工滿意度評分"], alpha=0.6, color="blue", label="員工滿意度評分")
    plt.scatter(x, plot_data["反饋情緒分析"], color="red", label="反饋情緒分析", s=50, zorder=3)
    
    # 添加平均線
    plt.axhline(y=avg_satisfaction, color='orange', linestyle='--', label=f"滿意度平均 ({avg_satisfaction:.2f})")
    plt.axhline(y=avg_sentiment, color='green', linestyle='--', label=f"情緒分析平均 ({avg_sentiment:.2f})")
    
    # 設置圖表
    plt.xlabel("員工")
    plt.ylabel("評分")
    plt.title(f"部門 {dept_id} 的員工滿意度與反饋情緒分析")
    
    # 設置x軸標籤（每隔5個員工顯示一個ID）
    sparse_indices = range(0, len(plot_data), 5)
    sparse_labels = [plot_data["員工ID"].iloc[i] for i in sparse_indices]
    plt.xticks([i for i in sparse_indices], sparse_labels, rotation=45)
    
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.ylim(0, 5.5)
    
    # 設置次要y軸來顯示滿意度等級
    ax2 = plt.gca().twinx()
    ax2.set_ylim(0, 5.5)
    ax2.set_yticks([1, 2, 3, 4, 5])
    ax2.set_yticklabels(['極不滿意', '不滿意', '中等', '滿意', '極滿意'])
    ax2.set_ylabel('滿意度等級')
    
    output_path = os.path.join(output_dir, f"satisfaction_trend_{dept_id}.png")
    plt.savefig(output_path)
    plt.close()
    return output_path