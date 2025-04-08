from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()
NAME = os.getenv("NAME")
PASSWORD = os.getenv("PASSWORD")

if not NAME or not PASSWORD:
    print("請先在 .env 中設定 NAME 和 PASSWORD")
    exit()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("啟動瀏覽器，前往 GitHub 登入頁面")
    page.goto("https://github.com/login")
    page.wait_for_timeout(2000)

    # 登入 GitHub
    page.fill("input[name='login']", NAME)
    page.wait_for_timeout(1000)
    page.fill("input[name='password']", PASSWORD)
    page.wait_for_timeout(1000)
    page.click("input[type='submit']")

    page.wait_for_timeout(3000)

    # 前往 repo 列表頁面
    repo_url = f"https://github.com/{NAME}/HW3_TEST"
    page.goto(repo_url)
     # 等待頁面載入，並點擊鉛筆圖標的編輯按鈕
    page.wait_for_selector("button[aria-label='Edit file']", timeout=10000)
    page.click("button[aria-label='Edit file']")
    page.wait_for_timeout(2000)

    # 等待 contenteditable 元素加載完成
    page.wait_for_selector("div[contenteditable='true']", timeout=5000)

    # 在下一行插入文本
    page.evaluate("""
    const editor = document.querySelector('div[contenteditable="true"]');
    const newLine = document.createElement('div');
    newLine.classList.add('cm-line');
    newLine.setAttribute('dir', 'auto');
    newLine.innerHTML = '## 這是資料結構作業三playwright自動輸入的測試文字';
    // 找到當前的最後一行並在其後插入新行
    const lastLine = editor.querySelector('.cm-line:last-child');
    lastLine.parentNode.insertBefore(newLine, lastLine.nextSibling);
    editor.scrollTop = editor.scrollHeight;  // 滾動到新行
""")

    
    page.click("button:has-text('Commit changes...')")
    page.wait_for_timeout(2000)  # 等待按鈕的點擊效果穩定

    # 使用 class 名稱來進行更精確的定位
    page.click("span.prc-Button-ButtonContent-HKbr- >> span.prc-Button-Label-pTQ3x >> text='Commit changes'")
    page.wait_for_timeout(5000)

    print("✅ 變更已成功提交")