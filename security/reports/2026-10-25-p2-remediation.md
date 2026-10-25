# SEC-P2-20261025：fastapi-learning-lab

日期：2026-10-25。基準：3bed40a02f1fa9147f9f0f39facc18e355e254e2（main）。

狀態：隔離修補已備妥，待整合。未推送／合併／部署；原始工作目錄保留。

Vite8.3.5、API pytest9.0.3，API48個解析版本加約束。另修共享容器／Pyodide runner的multipart0.0.32、PyJWT2.15.0、pytest9.0.3，移除8個直接套件公告；容器閉包43版本加約束，保留FastAPI0.141.1。

- 前端24 tests／type build
- API非container 11 tests；本機Pyodide全111堂參考解答及錯誤解答／跨執行狀態／輸出洪水負例通過
- API48版本、runner43版本及pnpm公告均0；117個container測試由遠端CI另驗，不以本機WASM替代

npm公告：{"info":0,"low":0,"moderate":0,"high":0,"critical":0,"total":0}。
Python公告：0個獨立命中／48個解析版本。



效能：{"beforeGzipBytes":81529,"afterGzipBytes":81649,"growth":0.001471868905542813,"thresholdGrowth":0.05,"performance":"pass","results":[{"script":"build","exitCode":0},{"script":"test","exitCode":0}]}。

範圍與成本：只跑本機及合成fixture，不啟用付費API或遠端CI。沒有完整正式安全或發布驗收；未評項目not_scored。

- 原始工作目錄、未提交修改與分支全部保留；本報告僅適用此隔離分支。
- 完整history／秘密輪替／正式服務與二進位鑑識不在此輪驗收，未評項目not_scored。

Task契約：輸入為固定基準及既有測試；交付為獨立修補分支、manifest/lockfile或來源修補與此去敏證據；無跨專案依賴。驗收是原生工具成功、已知發現逐項處置、適當真實回歸及影響範圍效能門檻；未完成項目明記，不以fixture代表正式環境。

## 合併前追查：Linux 輸出洪水清理

舊CI容器矩陣超過30分鐘。以無網路、唯讀、無Docker socket的Linux容器重現：stdout／stderr真實洪水各使清理超過5秒，2項回歸先失敗。修正為取消舊讀取工作、終止程序，再以4096-byte固定區塊丟棄剩餘管線輸出並同時等待結束，finally移除容器；不把無限輸出存入記憶體。

Linux兩個洪水／三次連續使用槽位及既有契約合計8測試0.71秒通過；Windows非容器13測試0.84秒通過。原程式Windows實際Docker矩陣117項179.02秒通過，不能用來證明Linux修復。新版Linux遠端矩陣待驗。保留64000-byte、既有執行／課程時限與30分鐘CI門檻，只加入逐項輸出及60秒堆疊診斷。Python官方文件亦說明等待PIPE程序的死鎖風險：https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.subprocess.Process.wait 。
