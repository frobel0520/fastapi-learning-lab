# 02 System Analysis

## 使用者流程

選擇學習路徑 → 閱讀概念 → 執行範例 → 修改程式 → 通過測試 → 保存進度 → 前往下一課。

## 核心契約

- `Course`：學習路徑與章節集合
- `Lesson`：概念、先備知識、解釋、範例與官方來源
- `Exercise`：起始碼、測試、提示與預期學習成果
- `Execution`：程式碼、測試結果、stdout、錯誤與資源限制
- `Progress`：課程狀態、最佳分數與最後活動時間

## 部署限制

GitHub Pages 是靜態託管，無法執行 FastAPI。專案支援兩種拓撲：

1. 建議：Cloudflare Static Assets → Python Worker FastAPI → Sandbox SDK。
2. 備援：GitHub Pages React → Cloudflare Python Worker FastAPI → Sandbox SDK。

Sandbox 必須採每位使用者／執行工作分離，並限制網路、資源與生命週期。
