# 04 MVP Release Gate

目前狀態：本機 MVP 功能與課程範圍完成；公開展示改採 GitHub Pages 靜態站 + 瀏覽器內 Pyodide runner（T009、T010）。Cloudflare runner 需要付費方案，暫不進行。

## Completed locally

- 14 模組、111 堂可執行課程、105 筆 ready coverage entries，FastAPI Learn 規劃缺口為 0。
- 每課都有自足概念解析、參考程式、練習、hidden checks 與可印出實際結果的 RUN & OUTPUT 程式。
- 「填入解答」會加入參考答案與 output observation；送出時兩者會被拆開，先跑 hidden checks、再執行 print observation。
- React production build、TypeScript typecheck、前端狀態／版面／正式環境 URL tests。
- `Runner` protocol 與 `ExecutionResult` 契約
- Podman ephemeral container：network none、read-only rootfs、非 root、CPU／memory／PID／file limits
- 正確答案 passed、錯誤答案 failed、無限迴圈 timeout、64 KB output flood termination
- 9 項 API／內容／runner unit tests，以及所有 111 個 reference solutions 的真實 container passing evidence。
- Runner 使用 framed protocol 分離學習者 stdout 與評分 JSON，`print()` 會顯示在 OUTPUT
- Runner threat model 與 accepted limitations
- GitHub Actions 三個 task checks：`web`、`api`、`runner-image`；不同 task branches 使用獨立 concurrency group。
- GitHub Pages workflow 只接續成功的 main CI，並拒絕缺少或非 HTTPS 的 `VITE_API_BASE_URL`。
- Runner CI 有 30 分鐘上限；request 被取消時會終止 process、移除暫存 container 並回收讀取 tasks。
- API CORS 可由 `FASTAPI_LAB_ALLOWED_ORIGINS` 設定，且保留 4173 本機預設值。
- `pnpm package:release` 會產生排除本機／generated files 的可重現 ZIP 與 SHA-256 manifest。
- Cloudflare 同源部署會讓 React 使用目前 origin；核心 FastAPI app 與平台 adapter 維持分離。
- 鍵盤分頁語意、跳至主要內容、mobile 課程選擇器、Coding 返回路徑、44px mobile controls 與 live output semantics 已加入。

## Public showcase (GitHub Pages)

- 課程內容於 build 時匯出為靜態 JSON，Pages 不需要 API。
- `browser-runner` CI job 在 Pyodide 中跑完 111 堂參考解答與錯誤答案、print output、output flood、flood 後重用檢查。
- 瀏覽器內 20 秒 timeout 會終止並重建 Web Worker；不支援 JSPI 的瀏覽器回傳 `unavailable`。

## Required before a paid cloud release

- 在 GitHub 建立各 task 的 Issue／branch／PR，並設定 `web`、`api`、`runner-image` required checks。
- 設定 GitHub Pages repository variable `VITE_API_BASE_URL`，完成 Pages preview smoke test。
- 連接 Cloudflare account，建立 preview Worker／Static Assets 環境與必要 secrets／bindings。
- 實作 `CloudflareSandboxRunner`，維持既有 request／response schema，完成平台 timeout、network、resource、cleanup 與 111 課 solution matrix。
- 完成公開 preview 的 CORS、HTTPS、health、execution、rollback smoke tests。
- 經人工確認 coverage、鍵盤導覽、對比度、reduced-motion 與手機／平板／桌面版面後簽核。

公開部署、Cloudflare account 連接與 secrets 建立不屬於 T017；需在後續 task 明確授權後執行。
