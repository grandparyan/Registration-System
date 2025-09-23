import os
import json
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from gspread import service_account, exceptions
from json.decoder import JSONDecodeError
from datetime import datetime

app = Flask(__name__)

# --- Google Sheet 連線設定 ---
try:
    GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    SPREADSHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME', '設備報修')

    if not GOOGLE_SERVICE_ACCOUNT_CREDENTIALS:
        raise ValueError("環境變數 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS' 尚未設定。")

    creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS)
    gc = service_account(credentials=creds_info)
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.sheet1
    print("成功連線到 Google 試算表！")

except (ValueError, JSONDecodeError, exceptions.SpreadsheetNotFound, exceptions.APIError) as e:
    print(f"初始化 Google 試算表連線時發生錯誤: {e}")
    worksheet = None

# --- Flask 路由 (Routes) ---

@app.route('/')
def home():
    """首頁，顯示所有報修紀錄。"""
    records = []
    error_message = None  # 初始化錯誤訊息變數
    
    if worksheet is None:
        error_message = "後端與 Google 試算表的連線建立失敗，請檢查後台日誌 (log)。"
    else:
        try:
            # get_all_records() 需要 'viewer' (檢視者) 或 'editor' (編輯者) 權限
            records = worksheet.get_all_records()
        except exceptions.APIError as e:
            print(f"讀取試算表資料時發生 API 錯誤: {e}")
            error_message = "讀取 Google 試算表資料時發生權限錯誤。請確認服務帳號 (gserviceaccount) 已被共用，並且擁有此試算表的 'Editor' (編輯者) 權限。"
        except Exception as e:
            print(f"讀取試算表資料時發生未知錯誤: {e}")
            error_message = f"讀取資料時發生未知錯誤: {e}"
            
    with open('index (3).html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    # 將錯誤訊息傳遞給模板
    return render_template_string(html_content, records=records, error=error_message)


@app.route('/submit_request', methods=['POST'])
def submit_request():
    """接收表單資料並寫入 Google 試算表。"""
    if worksheet is None:
        return "後端連線到試算表失敗，無法提交。", 500

    try:
        reporter_name = request.form.get('reporter_name')
        location = request.form.get('location')
        problem_description = request.form.get('problem_description')
        teacher = request.form.get('teacher')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_row = [reporter_name, location, problem_description, teacher, timestamp]
        # append_row() 通常只需要 'writer' (寫入者) 權限
        worksheet.append_row(new_row)
        
        print(f"成功將資料寫入試算表：{new_row}")
        return redirect(url_for('home'))

    except Exception as e:
        print(f"寫入試算表時發生錯誤: {e}")
        return "提交失敗，請再試一次。可能是權限不足或後端錯誤。", 500

@app.route('/delete_request/<int:row_index>')
def delete_request(row_index):
    """根據 row_index 刪除指定的報修紀錄。"""
    if worksheet is None:
        return "後端連線到試算表失敗，無法刪除。", 500

    try:
        # delete_rows() 需要 'editor' (編輯者) 權限
        worksheet.delete_rows(row_index + 1)
        print(f"成功刪除第 {row_index + 1} 列的紀錄。")
        return redirect(url_for('home'))
    except Exception as e:
        print(f"刪除試算表列時發生錯誤：{e}")
        return f"刪除失敗，這通常是因為權限不足，請確認服務帳號擁有 'Editor' 權限。錯誤詳情: {e}", 500

@app.route('/edit_request/<int:row_index>', methods=['GET'])
def edit_request(row_index):
    """顯示特定報修紀錄的修改頁面。"""
    if worksheet is None:
        return "後端連線到試算表失敗，無法修改。", 500
    
    try:
        # row_values() 需要 'viewer' (檢視者) 或 'editor' (編輯者) 權限
        record_values = worksheet.row_values(row_index + 1)
        headers = worksheet.row_values(1)
        record = dict(zip(headers, record_values))
        
        edit_html = f"""
        <!DOCTYPE html>
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <title>修改報修紀錄</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="p-6 bg-gray-100">
            <div class="max-w-xl mx-auto bg-white p-8 rounded-xl shadow-lg">
                <h1 class="text-2xl font-bold mb-6">修改報修紀錄</h1>
                <form action="{url_for('update_request', row_index=row_index)}" method="post" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">報修者姓名</label>
                        <input type="text" name="reporter_name" value="{record.get('報修者姓名', '')}" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm px-3 py-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">設備位置</label>
                        <input type="text" name="location" value="{record.get('設備位置', '')}" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm px-3 py-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">設備問題描述</label>
                        <textarea name="problem_description" rows="3" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm px-3 py-2">{record.get('設備問題描述', '')}</textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">協助老師</label>
                        <input type="text" name="teacher" value="{record.get('協助老師', '')}" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm px-3 py-2">
                    </div>
                    <div class="pt-4">
                         <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md">更新紀錄</button>
                         <a href="{url_for('home')}" class="mt-2 block w-full text-center bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded-md">取消</a>
                    </div>
                </form>
            </div>
        </body>
        </html>
        """
        return render_template_string(edit_html)
        
    except Exception as e:
        print(f"讀取要編輯的資料時發生錯誤：{e}")
        return f"無法載入編輯頁面，這通常是因為權限不足。請確認服務帳號擁有 'Editor' 權限。錯誤詳情: {e}", 500

@app.route('/update_request/<int:row_index>', methods=['POST'])
def update_request(row_index):
    """接收修改表單的資料並更新到 Google 試算表。"""
    if worksheet is None:
        return "後端連線到試算表失敗，無法更新。", 500

    try:
        reporter_name = request.form.get('reporter_name')
        location = request.form.get('location')
        problem_description = request.form.get('problem_description')
        teacher = request.form.get('teacher')
        
        # cell() 和 update() 都需要 'editor' (編輯者) 權限
        original_timestamp = worksheet.cell(row_index + 1, 5).value
        updated_row = [reporter_name, location, problem_description, teacher, original_timestamp]
        worksheet.update(f'A{row_index + 1}:E{row_index + 1}', [updated_row])
        
        print(f"成功更新第 {row_index + 1} 列的紀錄。")
        return redirect(url_for('home'))

    except Exception as e:
        print(f"更新試算表時發生錯誤：{e}")
        return f"更新失敗，這通常是因為權限不足。請確認服務帳號擁有 'Editor' 權限。錯誤詳情: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)

