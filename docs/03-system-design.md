# 03 System Design

## Design Read

- Artifact：互動式 developer learning workbench
- Audience：具備 Python 基礎的繁體中文 FastAPI 學習者
- Visual language：Google Cloud Console-inspired information architecture
- Mode：greenfield
- Dials：variance 4、motion 3、density 8、assets 1、fidelity 6

## Design decisions

- Palette：action `#1a73e8`、success `#34a853`、warning `#fbbc04`、error `#ea4335`、surface `#f8fafd`、ink `#202124`
- Typography：Noto Sans TC；程式碼使用 JetBrains Mono
- Spacing：4px base，主要節奏 8/12/16/24/32
- Radius：控制項 6px、面板 10px；狀態 badge 才使用 pill
- Shadow：只在浮動控制與高層面板使用低幅陰影
- Motion：140–220ms；只表達 hover、focus、切換與執行狀態
- Layout：桌面三欄、平板兩欄、手機單欄分頁

## Positioning

- Narrative role：直接進入工作台，不設封面頁
- Viewing distance：以 1m laptop 為主，兼容手機 10cm 閱讀
- Temperature：可靠、專注、帶少量探索感
- Capacity：左側導覽 264px、中間正文 minmax 440px、右側 lab 420px

## Runtime boundaries

`web → api → runner` 單向依賴。課程內容透過 schema 載入；UI 不直接依賴 runner 實作。

靜態模式（`vite --mode static`）沒有 API：`scripts/export_static_content.py` 在 build 時把 API 會回傳的課程與 coverage 匯出成 JSON，執行則交給瀏覽器內的 Pyodide runner。兩種模式共用同一份 `harness.py` 與 `ExecutionResult` 格式。

## Release topologies

### Current: GitHub Pages static + browser runner

- 目標：免費公開展示，不需要任何雲端帳號或付費方案
- `GitHub Pages`：React static build 與 build 時匯出的 `generated/course.json`、`generated/coverage.json`、runner Python 檔
- `Web Worker + Pyodide`：第一次按「執行測試」才從 jsDelivr 載入 Pyodide `314.0.7`，再以 micropip 安裝與 runner image 相同版本的套件
- `apps/runner/pyodide_shim.py`：Pyodide 沒有 thread，把 TestClient 的 blocking portal、`anyio.to_thread` 與 a2wsgi 的 executor 改成在單一 event loop 上以 JSPI `run_sync` 執行
- 需要支援 WebAssembly JSPI 的瀏覽器（目前以 Chrome／Edge 驗證）；不支援時回傳 `unavailable` 並提示改用支援的瀏覽器

### Future: Cloudflare same-origin（需要 Workers Paid）

Cloudflare 的 Sandbox／Containers 只在付費方案提供，因此目前不部署；保留設計與 `app/worker.py` 入口。

- `Static Assets`：React build output
- `Python Worker`：透過 Cloudflare ASGI adapter 執行既有 FastAPI app
- `D1`：後續保存課程索引與使用者進度
- `R2`：後續保存大型課程／評測 artifacts
- `Sandbox SDK`：後續執行不受信任的 coding exercise；每個使用者使用獨立 sandbox

核心 FastAPI app 不匯入 Cloudflare SDK；`app/worker.py` 是平台 adapter，確保本機 Uvicorn 與其他容器平台仍可使用同一套 API。

正式版前端未設定 `VITE_API_BASE_URL` 時會使用目前網頁 origin，因此 Cloudflare Static Assets 與 Python Worker 可以共用一個網域，不需要把環境 URL 寫死在 bundle。

若日後改回 API 模式，GitHub Pages 前端可用 `VITE_API_BASE_URL` 指向公開的 HTTPS API，並把 Pages origin 加進 `FASTAPI_LAB_ALLOWED_ORIGINS`。

## CI and task boundaries

- 每個 `Txxx` 對應一個 Issue、`task/Txxx-description` branch、PR 與獨立 CI run。
- CI 的 `web`、`api`、`runner-image`、`browser-runner` 是四個穩定 required-check 名稱；`browser-runner` 以 Node 24 + JSPI 在 Pyodide 中跑完全部參考解答，確保瀏覽器 runner 與 container runner 的 hidden checks 結果一致。
- 同一 branch 的新 commit 會取消舊的 CI run；不同 task branch 使用不同 concurrency group，不會互相取消。
- GitHub Pages deployment 只從 `main` 或人工 dispatch 執行，不作為 PR CI 的替代品。
- Task branch 併入 `main` 前，所有 CI jobs 必須通過；實際建立 branch、push、PR 與 required checks 等 repository 操作留到 GitHub 專案建立後逐 task 進行。

## Runner contract

`POST /api/v1/executions` 只依賴 `Runner` protocol，回傳固定的 `ExecutionResult`：`status`、`checks`、`stdout`、`stderr`、`duration_ms` 與 `runner`。React 不知道 Podman 或 Cloudflare 的存在。

本機 `LocalContainerRunner` 安全邊界：

- 不提供 host subprocess fallback
- container network 設為 `none`
- root filesystem 唯讀，只給 32 MB `/tmp`
- 限制 192 MB memory、0.5 CPU、64 PIDs
- drop all Linux capabilities，啟用 `no-new-privileges`
- 使用非 root UID 65532
- API 外層 6 秒 timeout，stdout/stderr 各保留最後 12 KB

瀏覽器 runner（`apps/web/src/runner/`）邊界：

- 每個分頁一個專用 Web Worker；學習者程式碼不在 UI thread 執行
- 20 秒執行 timeout，逾時直接 terminate worker，下次執行重新載入 runtime
- stdout／stderr 超過 64 KB 時寫入失敗並回傳 `error`；streams 無緩衝，被截斷的輸出不會漏進下一次執行
- 每次執行前清除 SQLModel metadata，避免上一課註冊的 table 影響下一課
- 結果 `runner` 為 `browser-pyodide`

部署 Cloudflare 時新增 `CloudflareSandboxRunner`，不得改動 API request／response schema。
