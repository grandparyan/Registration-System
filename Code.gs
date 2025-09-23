function doPost(e) {
try {
// 取得試算表
const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
const sheet = spreadsheet.getSheetByName("報修紀錄");

// 確認工作表是否存在，如果不存在則建立一個
if (!sheet) {
  sheet = spreadsheet.insertSheet("報修紀錄");
  // 設定標題列
  sheet.getRange(1, 1, 1, 5).setValues([["報修者姓名", "設備位置", "設備問題描述", "協助老師", "報修時間"]]);
}

// 解析從前端傳來的 JSON 資料
const requestData = JSON.parse(e.postData.contents);

// 取得資料
const reporterName = requestData.reporter_name;
const location = requestData.location;
const problemDescription = requestData.problem_description;
const teacher = requestData.teacher;
const timestamp = new Date();

// 將資料新增到工作表的最後一行
sheet.appendRow([reporterName, location, problemDescription, teacher, timestamp]);

// 回傳成功訊息
return ContentService
  .createTextOutput(JSON.stringify({ status: "success" }))
  .setMimeType(ContentService.MimeType.JSON);

} catch (error) {
// 回傳錯誤訊息
return ContentService
.createTextOutput(JSON.stringify({ status: "error", message: error.message }))
.setMimeType(ContentService.MimeType.JSON);
}
}
