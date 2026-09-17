# 01 Project Plan

## 產品目標

建立一套以繁體中文重新解析 FastAPI 官方課程的互動式學習平台。每一課必須具備概念解析、原創程式碼範例、可驗證的 coding exercise，以及官方來源連結。

## MVP success criteria

1. 課程 coverage manifest 能對應 FastAPI Learn 的所有章節。
2. 學習者能閱讀課程、編輯程式碼、提交練習並得到測試回饋。
3. 進度可在本機持久化，資料層保留升級至帳號同步的介面。
4. React 前端可部署到 GitHub Pages。
5. FastAPI 與 runner 不依賴 GitHub Pages，可獨立部署。
6. CI 必須通過前端型別檢查、建置、後端測試、內容 schema 與 coverage gate。

## Source authority

1. FastAPI 官方 Learn 與 Reference
2. FastAPI 官方 release notes
3. Pydantic、Starlette、Python 官方文件

課程內容不得整頁複製來源；採重新組織、重新解釋、原創範例與來源指標。

