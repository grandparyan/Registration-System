設備報修留言板 (使用 Python & Google 試算表)
這是一個基於 Flask 框架的簡單網頁應用程式，允許使用者提交設備報修請求。後端使用 Google 試算表作為資料庫，提供建立、讀取、更新和刪除 (CRUD) 的功能。

功能
報修留言板: 提交新的設備報修請求，包含報修者姓名、設備位置、問題描述、協助老師和報修時間。

報修清單: 顯示所有現有的報修紀錄。

編輯: 可以修改任何一條報修紀錄的內容。

刪除: 可以刪除不再需要的報修紀錄。

準備工作
1. 安裝 Python 套件
請先在您的專案資料夾中建立並啟用虛擬環境，然後安裝必要的套件：

pip install -r requirements.txt

2. Google 試算表 API 設定 (針對 Render 部署)
當您部署到 Render 等雲端平台時，為了安全，您不應直接上傳金鑰檔案。相反，您需要將金鑰內容設定為環境變數。

建立 Google Cloud Platform 專案:

前往 Google Cloud Platform Console。

建立一個新專案。

啟用 Google Sheets API:

在專案儀表板中，搜尋並選擇 Google Sheets API。

點選「啟用」。

建立服務帳號 (Service Account):

在左側導覽列中，找到「IAM 與管理」>「服務帳號」。

點選「建立服務帳號」。

輸入服務帳號名稱，例如 repair-app，然後點選「建立並繼續」。

點選「完成」。

下載金鑰檔案:

回到服務帳號清單，點選您剛建立的帳號。

選擇「金鑰」分頁，然後點選「新增金鑰」>「建立新金鑰」。

選擇 JSON 格式，然後點選「建立」。

瀏覽器會自動下載一個 JSON 檔案。請開啟此檔案，並複製其所有內容。

分享 Google 試算表:

建立一個新的 Google 試算表，並為其命名（例如：設備報修紀錄）。

在試算表的右上方，點選「共用」。

將您服務帳號的電子郵件（格式為 repair-app@<專案名稱>.iam.gserviceaccount.com）貼到共用清單中。

將其權限設定為 編輯者，然後點選「傳送」。

3. 設定 Render 環境變數
在 Render 儀表板上，找到您的應用程式服務，然後進行以下設定：

GOOGLE_SERVICE_ACCOUNT_CREDENTIALS: 將您在步驟 4 複製的 credentials.json 檔案內容完整貼上。

GOOGLE_SHEET_NAME: 填入您的試算表名稱，例如 設備報修紀錄。

如何執行
在您的終端機中，執行以下指令：

python app.py

然後在瀏覽器中開啟 http://127.0.0.1:5000，即可使用您的設備報修留言板。
