# FastAPI Learning Lab

以繁體中文學習 FastAPI 的互動式工作台。前端使用 React，後端使用 FastAPI；課程內容會依 FastAPI 官方 Learn 導覽建立版本化 coverage manifest。

線上展示：https://frobel0520.github.io/fastapi-learning-lab/ （GitHub Pages 靜態站，Coding 練習直接在瀏覽器內以 Pyodide 執行；需要支援 WebAssembly JSPI 的瀏覽器，已在 Chrome 驗證）

## 目前範圍

- GCP Console 風格的響應式三欄學習介面
- 14 模組、111 堂完整互動課程與 105 筆 ready FastAPI Learn coverage entries
- 課程、章節、概念、程式碼與練習的 Pydantic／TypeScript 契約
- 可切換 Workbench、Focus、Review 三種閱讀版面
- FastAPI health、課程／單課／coverage 與隔離執行 API
- Podman 隔離執行器、hidden checks、timeout 與資源限制
- Coding 練習可一鍵填入參考解答與實際 output observation，再送入隔離 runner 驗證
- SQL 課程使用 SQLModel 0.0.42 與每次執行獨立的 SQLite 記憶體資料庫
- GitHub Pages 靜態展示：課程 JSON 於 build 時匯出，練習在瀏覽器 Web Worker 內以 Pyodide 執行同一份 hidden checks
- CI 同時驗證 container runner 與 Pyodide runner 都能通過 111 堂參考解答
- Cloudflare Static Assets + Python Worker 部署入口（隔離執行需要 Workers Paid，暫未部署）

兩種執行模式共用同一份 `apps/runner/harness.py`：本機開發使用 FastAPI API + Podman container；公開展示使用 GitHub Pages + 瀏覽器內 Pyodide，不需要任何雲端帳號或費用。

## 本機啟動

需求：Node.js 22+、Python 3.12+。

先啟動 Podman machine 並建置 runner image：

```bash
podman machine start
pnpm build:runner:local-ca
```

一般網路環境使用 `pnpm build:runner`；`build:runner:local-ca` 是本機企業 CA 環境專用，不會影響 GitHub CI。

```bash
pnpm install
pnpm dev:web
```

另開終端機：

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m uvicorn app.main:app --port 8010
```

前端固定使用 `http://127.0.0.1:4173`（不使用 5173），預設連線 `http://127.0.0.1:8010`。也可在 `apps/web/.env.local` 設定：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8010
```

API 預設只接受上述兩個本機 4173 origins。GitHub Pages 或其他分離部署需設定逗號分隔的 origins（可由 `apps/api/.env.example` 複製）：

```dotenv
FASTAPI_LAB_ALLOWED_ORIGINS=http://localhost:4173,http://127.0.0.1:4173,https://YOUR_ACCOUNT.github.io
```

`POST /api/v1/executions` 不會在 FastAPI host process 直接執行學習者程式碼。每次執行都會建立暫時性 container，停用網路並限制 CPU、memory、PID、可寫空間與執行時間。一般課程限時 6 秒；CPU 較重的 password-hashing 與多請求 OAuth2 scopes 檢查限時 15 秒。

## 本機預覽 GitHub Pages 靜態版

不需要 API 與 Podman，只需要能匯出課程內容的 Python 環境（已安裝 `apps/api`）：

```bash
pnpm install
pnpm dev:web:static
```

`dev:web:static` 會先執行 `pnpm export:static`，把課程 JSON 與 runner 檔案寫到 `apps/web/public/generated/`（不進版控），再以 `vite --mode static` 啟動。第一次按「執行測試」會從 jsDelivr 下載 Pyodide 與課程套件，之後由瀏覽器快取。

驗證 Pyodide runner 與全部參考解答（需要 Node 24）：

```bash
pnpm export:static
pnpm verify:browser-runner
```

## 專案結構

```text
apps/web/       React + TypeScript + Vite
apps/api/       FastAPI API
apps/runner/    runner image、hidden-check harness 與 Pyodide shim
content/        版本化課程內容與 coverage manifest
docs/           SDLC、分析、設計與 release gate
scripts/        release ZIP 打包、靜態內容匯出與驗證
```

## 打包到 GitHub

完成本機驗證後執行：

```bash
pnpm package:release
```

輸出位於 `release/fastapi-learning-lab.zip`。封包只包含專案原始碼與部署設定，會排除 `node_modules`、虛擬環境、build outputs、Graphify 與本機進度紀錄；`PACKAGE-MANIFEST.json` 記錄每個檔案的 SHA-256。解壓後即可上傳至空的 GitHub repository。

## Cloudflare deployment plan

> Cloudflare 的 Sandbox／Containers 只在 Workers Paid 方案提供，因此目前公開展示改用 GitHub Pages。以下保留為日後上雲的入口。

核心 API 支援 Python 3.12+；Cloudflare Python Workers 目前使用 Python 3.13 runtime。安裝 `uv`、Node.js 與 Wrangler 後：

```bash
pnpm install
pnpm build:web
cd apps/api
uv sync --group cloudflare
uv run pywrangler dev
```

`apps/api/wrangler.jsonc` 會從 `apps/web/dist` 提供靜態檔案，API routes 優先交給 FastAPI。

Cloudflare 同源部署可以不設定 `VITE_API_BASE_URL`；正式版會使用目前網頁 origin。

GitHub Pages 只會在 `main` 的 CI 全數成功後自動部署（`pnpm build:web:static`）；手動 dispatch 也會先重跑前端 tests 與 typecheck。
