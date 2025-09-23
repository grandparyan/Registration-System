import os
import json
from flask import Flask, render_template_string, request, jsonify
from gspread import service_account
from json.decoder import JSONDecodeError

app = Flask(__name__)

# 使用 os.environ 讀取環境變數，確保程式碼可以在 Render 上運作
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')

def get_service_account_credentials():
    """安全地解析 JSON 憑證字串並返回憑證對象。"""
    if not GOOGLE_SERVICE_ACCOUNT_CREDENTIALS:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set.")
    
    try:
        # 嘗試解析 JSON 內容
        creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS)
        return creds_info
    except JSONDecodeError as e:
        print(f"嘗試解析的 JSON 憑證內容：{GOOGLE_SERVICE_ACCOUNT_CREDENTIALS}")
        raise ValueError(f"無法解析 JSON 憑證。請確認內容正確無誤。錯誤訊息: {e}")
    except Exception as e:
        print(f"憑證解析時發生未知錯誤，但 JSON 內容可能正確。錯誤訊息：{e}")
        raise ValueError(f"憑證解析時發生未知錯誤：{e}")

# 初始化 Google 憑證
try:
    creds_info = get_service_account_credentials()
    gc = service_account(json_info=creds_info)
    SPREADSHEET_NAME = "設備報修"  # 替換成你的 Google 試算表名稱
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.get_worksheet(0)  # 取得第一個工作表
    print("成功連線到 Google 試算表！")
except Exception as e:
    print(f"連線到 Google 試算表時發生錯誤：{e}")
    worksheet = None # 如果連線失敗，將 worksheet 設為 None

@app.route('/')
def home():
    """顯示報修表單網頁。"""
    # 讀取 index.html 檔案內容並回傳
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return render_template_string(html_content)

@app.route('/submit_repair', methods=['POST'])
def submit_repair():
    """接收表單資料並寫入 Google 試算表。"""
    if worksheet is None:
        return jsonify({'success': False, 'message': '後端連線到試算表失敗。'})

    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '沒有收到表單資料。'})

        # 取得表單欄位的值
        reporter_name = data.get('reporter_name')
        location = data.get('location')
        problem_description = data.get('problem_description')
        teacher = data.get('teacher')
        
        # 建立一個新的資料列，順序需與 Google 試算表欄位順序一致
        new_row = [reporter_name, location, problem_description, teacher]
        
        # 將資料附加到工作表的最後一行
        worksheet.append_row(new_row)
        
        print(f"成功將資料寫入試算表：{new_row}")
        return jsonify({'success': True, 'message': '報修申請已提交成功！'})

    except Exception as e:
        print(f"寫入試算表時發生錯誤：{e}")
        return jsonify({'success': False, 'message': f'提交失敗，請再試一次。錯誤：{e}'})

if __name__ == '__main__':
    # 為了方便本地測試，設定 host 為 '0.0.0.0'
    app.run(debug=True, host='0.0.0.0')
