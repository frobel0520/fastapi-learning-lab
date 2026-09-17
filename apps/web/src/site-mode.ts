export type SiteMode = "api" | "static";

export function resolveSiteMode(flag: string | undefined): SiteMode {
  return flag?.trim().toLowerCase() === "true" ? "static" : "api";
}

export type SiteCopy = {
  runtimeLabel: string;
  running: string;
  runFailed: string;
  contentErrorTitle: string;
  contentErrorDetail: string;
};

export const SITE_COPY: Record<SiteMode, SiteCopy> = {
  api: {
    runtimeLabel: "Python 3.12",
    running: "正在建立隔離環境並執行 hidden checks…",
    runFailed: "無法連線課程 API。請確認 FastAPI 後端位於 8010，或設定 VITE_API_BASE_URL。",
    contentErrorTitle: "課程 API 尚未連線",
    contentErrorDetail: "請在 8010 啟動 FastAPI 後端，再重新整理頁面。",
  },
  static: {
    runtimeLabel: "Python 3.14 · Pyodide",
    running: "正在瀏覽器內執行 hidden checks…",
    runFailed: "瀏覽器內執行失敗。請重新整理頁面後再試一次。",
    contentErrorTitle: "課程內容載入失敗",
    contentErrorDetail: "無法讀取靜態課程資料，請重新整理頁面。",
  },
};
