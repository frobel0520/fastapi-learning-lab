# FastAPI Learning Lab

以繁體中文學習 FastAPI 的互動式工作台。前端使用 React，後端使用 FastAPI；課程內容會依 FastAPI 官方 Learn 導覽建立版本化 coverage manifest。

## 目前範圍

- GCP Console 風格的響應式三欄學習介面
- 14 模組、111 堂完整互動課程與 105 筆 ready FastAPI Learn coverage entries
- 課程、章節、概念、程式碼與練習的 Pydantic／TypeScript 契約
- 可切換 Workbench、Focus、Review 三種閱讀版面
- FastAPI health、課程／單課／coverage 與隔離執行 API
- Podman 隔離執行器、hidden checks、timeout 與資源限制
- Coding 練習可一鍵填入參考解答與實際 output observation，再送入隔離 runner 驗證
- SQL 課程使用 SQLModel 0.0.42 與每次執行獨立的 SQLite 記憶體資料庫
- GitHub Pages 純前端部署流程
- Cloudflare Static Assets + Python Worker 部署入口

正式環境建議使用 Cloudflare：Static Assets 提供 React、Python Worker 執行 FastAPI、Sandbox SDK 執行隔離練習。GitHub Pages workflow 仍保留為純前端備援；使用 Pages 時，前端以 `VITE_API_BASE_URL` 連線 Cloudflare API。

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

## 專案結構

```text
apps/web/       React + TypeScript + Vite
apps/api/       FastAPI API
apps/runner/    本機隔離 runner image 與 hidden-check harness
content/        版本化課程內容與 coverage manifest
docs/           SDLC、分析、設計與 release gate
scripts/        可重現的 release ZIP 打包與驗證
```

## 打包到 GitHub

完成本機驗證後執行：

```bash
pnpm package:release
```

輸出位於 `release/fastapi-learning-lab.zip`。封包只包含專案原始碼與部署設定，會排除 `node_modules`、虛擬環境、build outputs、Graphify 與本機進度紀錄；`PACKAGE-MANIFEST.json` 記錄每個檔案的 SHA-256。解壓後即可上傳至空的 GitHub repository。

## Cloudflare deployment plan

核心 API 支援 Python 3.12+；Cloudflare Python Workers 目前使用 Python 3.13 runtime。安裝 `uv`、Node.js 與 Wrangler 後：

```bash
pnpm install
pnpm build:web
cd apps/api
uv sync --group cloudflare
uv run pywrangler dev
```

`apps/api/wrangler.jsonc` 會從 `apps/web/dist` 提供靜態檔案，API routes 優先交給 FastAPI。

Cloudflare 同源部署可以不設定 `VITE_API_BASE_URL`；正式版會使用目前網頁 origin。GitHub Pages 必須在 repository variables 設定公開的 HTTPS `VITE_API_BASE_URL`，部署 workflow 會在缺少或格式錯誤時停止。Pages 只會在 `main` 的 CI 全數成功後自動部署；手動 dispatch 也會先重跑前端 tests 與 typecheck。
