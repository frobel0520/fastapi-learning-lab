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

## Release topologies

### Preferred: Cloudflare same-origin

- `Static Assets`：React build output
- `Python Worker`：透過 Cloudflare ASGI adapter 執行既有 FastAPI app
- `D1`：後續保存課程索引與使用者進度
- `R2`：後續保存大型課程／評測 artifacts
- `Sandbox SDK`：後續執行不受信任的 coding exercise；每個使用者使用獨立 sandbox

核心 FastAPI app 不匯入 Cloudflare SDK；`app/worker.py` 是平台 adapter，確保本機 Uvicorn 與其他容器平台仍可使用同一套 API。

正式版前端未設定 `VITE_API_BASE_URL` 時會使用目前網頁 origin，因此 Cloudflare Static Assets 與 Python Worker 可以共用一個網域，不需要把環境 URL 寫死在 bundle。

### Backup: GitHub Pages + Cloudflare API

GitHub Pages 只提供靜態 React 檔案，無法執行 FastAPI。部署 workflow 必須取得 repository variable `VITE_API_BASE_URL`，且值必須是 Cloudflare API 的公開 HTTPS origin；缺少或使用 HTTP 時 build job 會 fail fast，避免發布後錯連 `127.0.0.1`。

## CI and task boundaries

- 每個 `Txxx` 對應一個 Issue、`task/Txxx-description` branch、PR 與獨立 CI run。
- CI 的 `web`、`api`、`runner-image`、`browser-runner` 是四個穩定 required-check 名稱；`browser-runner` 以 Node 24 + JSPI 在 Pyodide 中跑完全部參考解答，確保瀏覽器 runner 與 container runner 的 hidden checks 結果一致。
- 同一 branch 的新 commit 會取消舊的 CI run；不同 task branch 使用不同 concurrency group，不會互相取消。
- GitHub Pages deployment 只從 `main` 或人工 dispatch 執行，不作為 PR CI 的替代品。
- Task branch 併入 `main` 前，三個 CI jobs 必須通過；實際建立 branch、push、PR 與 required checks 等 repository 操作留到 GitHub 專案建立後逐 task 進行。

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

部署 Cloudflare 時新增 `CloudflareSandboxRunner`，不得改動 API request／response schema。
