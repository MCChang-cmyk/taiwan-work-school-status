# 臺灣停班停課 — Home Assistant 自訂整合

<img src="custom_components/taiwan_work_school/brand/icon.png" width="120" alt="臺灣停班停課專案圖示">

從[行政院人事行政總處](https://www.dgpa.gov.tw/typh/daily/nds.html)讀取天然災害停班停課公告。支援 22 縣市複選、設定介面修改與兩種排程；不需帳號、API key 或額外 Python 套件。

## 透過 HACS 安裝

HACS 僅支援公開的 GitHub 儲存庫；若仍為 Private，新增時會出現 GitHub 404。

1. 在 HACS 右上角選單開啟「自訂儲存庫」。
2. 網址填入 `https://github.com/MCChang-cmyk/taiwan-work-school-status`。
3. 類型選擇 **Integration**，按「新增」。
4. 搜尋「臺灣停班停課」並下載；沒有 release 時使用預設分支 `main`。
5. 重新啟動 Home Assistant，再到「設定 → 裝置與服務 → 新增整合」搜尋「臺灣停班停課」。

本專案已提供 HACS 自訂儲存庫設定，尚未列入 HACS 預設清單。

## 手動安裝

1. 解壓縮 `dist/taiwan_work_school-1.3.2.zip`，將內含的 `custom_components` 合併至 Home Assistant 設定目錄。
2. 確認路徑為 `/config/custom_components/taiwan_work_school/manifest.json`，勿多包一層資料夾。
3. 重新啟動 Home Assistant。
4. 開啟「設定 → 裝置與服務 → 新增整合」，搜尋「臺灣停班停課」。
5. 複選縣市並設定更新模式。日後從整合卡片的設定選項修改，不需手動編輯 YAML。

若搜尋不到，先重新整理瀏覽器並確認上述路徑及 Home Assistant 日誌。這是可手動安裝的自訂整合，並非官方內建整合。GitHub 儲存庫：[MCChang-cmyk/taiwan-work-school-status](https://github.com/MCChang-cmyk/taiwan-work-school-status)。尚未登錄 HACS。

## 更新設定

所有縣市共用同一份資料。初次安裝、Home Assistant 重新啟動、重新載入整合及儲存設定後，都會先抓一次資料。

| 模式 | 行為 |
| --- | --- |
| 每小時整點更新 | 每天台灣時間 00:00、01:00、02:00……23:00 更新 |
| 每小時＋晚間密集更新（新安裝預設） | 上述每個整點更新，另在 20:00–20:15 依設定追加更新 |

**兩種模式都會在每天 00:00（前一天的 24:00）抓取官方網頁**，不受啟動時間或 Home Assistant 時區影響。20:00 的每小時更新與密集更新共用同一個排程，只抓一次。

晚間密集模式有兩個獨立參數：

- **間隔分鐘**：1–15。
- **總次數**：1–16，包含 20:00 的第一次。

公式：`間隔 ×（總次數 − 1）≤ 15`，超過會顯示錯誤，請調整後儲存。每小時模式不使用這兩個參數。

預設間隔 3 分鐘、共 6 次，晚間排程為 20:00、20:03、20:06、20:09、20:12、20:15；加上其餘整點，一天共 29 次排程抓取。間隔 5 分鐘、共 4 次則為 20:00、20:05、20:10、20:15。總次數設為 1 時，只有整點抓取。啟動、重新載入及手動更新不計入上述次數。

若 20:07 重新啟動，啟動時先抓一次，接著執行 20:09、20:12、20:15、21:00……，不補發錯過的請求。所有排程固定採 `Asia/Taipei`。00:00 本地立即切換今天／明天的日期，同時透過共用排程讀取網頁；抓取失敗時標為無法使用，保留最後成功資料，下一個排程繼續嘗試。

00:00 抓取的是官方當時提供的內容；若官方尚未換日或稍後才更新，整合保留原公告日期，不自行改寫公告。可用更新按鈕提早再抓，否則下一整點會繼續更新。

舊版的「晚間模式」更新後自動成為「每小時＋晚間密集更新」，原有間隔及總次數保留。舊版每小時模式則改為固定整點，包含 00:00。實體 ID 及自動化不需修改。

## 手動更新按鈕

重開機、重新載入整合、儲存設定時，本來就會立即讀取最新公告，不必等排程。

另提供一個共用按鈕 **臺灣停班停課 更新資訊**（`button.taiwan_work_school_refresh`）。在「設定 → 裝置與服務 → 臺灣停班停課 → 實體」找到它，或加到儀表板。按一次更新全部已選縣市，無論目前是每小時或晚間模式。按鈕在抓取失敗時仍可按，方便網路恢復後重試；更新失敗會顯示錯誤。連續點擊會由共用 coordinator 合併／限制頻率，避免對官方網站發出大量請求。手動更新不改變下一次原定排程。

也可從「開發者工具 → 動作」執行：

```yaml
action: button.press
target:
  entity_id: button.taiwan_work_school_refresh
```

可從 sensor 的 `last_successful_fetch` 屬性確認最後一次成功抓取時間，`source_updated` 則是官方網頁標示的更新時間，兩者意義不同。按鈕顯示的時間代表按下時間，不能代替抓取成功時間。

## 實體

每個縣市建立 3 個 sensor：今天、明天的合併狀態，以及公告。以臺北市為例（若已存在相同 entity ID，HA 可能加上數字後綴）：

| 實體 ID | 用途 |
| --- | --- |
| `sensor.taiwan_work_school_taipei_announcement` | 公告摘要；完整內容在 `announcements` 屬性 |
| `sensor.taiwan_work_school_taipei_today` | 臺北市 今天停班停課 |
| `sensor.taiwan_work_school_taipei_tomorrow` | 臺北市 明天停班停課 |

狀態實體底層值：

| 值 | 中文顯示 | 解讀 |
| --- | --- | --- |
| `suspended` | 停止上班、停止上課 | 公告為全縣市、全日停班停課 |
| `normal` | 正常上班上課 | 明確照常公告，或官方有效的「無停班停課訊息」頁面（當日及次日） |
| `work_only` | 僅停班、照常上課 | 停班但照常上課 |
| `school_only` | 照常上班、僅停課 | 照常上班但停課 |
| `partial` | 局部或部分時段停止 | 有鄉鎮、學校或時段限制，須查看完整公告 |
| `criteria_met` | 已達停班停課標準 | 官方公布已達標準，保留其評估用語，不視為正式停班停課公告 |
| `criteria_not_met` | 未達停班停課標準 | 官方公布未達標準，不等同照常上班上課公告 |
| `unannounced` | 尚未宣布 | 未找到該日期可辨識的停班／停課結論；不代表照常 |
| `undetermined` | 無法判定 | 同一天的全縣市公告存在衝突，須查看原文 |
| `unavailable` | 無法使用 | 網路、HTTP 或頁面格式出錯；保留最後成功資料供查閱 |

所有實體包含 `county`、`report_date`、`no_announcements`、`source_updated`、`last_successful_fetch`、`next_update`、`source`、`announcements` 屬性。日期狀態實體另有 `target_date`、`work_status` 與 `school_status`，保留個別停班／停課結果。兩者不一致但任一側尚未宣布時顯示 `undetermined`；任一側為局部停止時顯示 `partial`，原文仍須查閱。

解析以網頁標題日期為基準換算「今天／明天」，不以下載時間猜測；跨午夜本地重算今天／明天的實體（不額外連線），避免隔天仍顯示上一天的「明天」。未涵蓋新日期的舊公告會顯示 `unannounced`。公告摘要保留原文日期語意，可能屬於較早日期，請搭配 `report_date` 查看。

針對局部或半日公告採保守分類，不嘗試推算個別學校、鄉鎮或當前時刻是否停班。更改縣市會移除取消選取縣市的實體登錄，重新選取時會再建立。

## 自動化範例

以下只對「明天全縣市全天停止」發通知；局部停止請另外處理 `partial`。將 `notify.mobile_app_your_phone` 換成自己的通知動作。

```yaml
alias: 明天臺北市停班停課通知
triggers:
  - trigger: state
    entity_id: sensor.taiwan_work_school_taipei_tomorrow
    to: suspended
conditions: []
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: 臺北市明天停班停課
      message: >-
        {{ state_attr('sensor.taiwan_work_school_taipei_announcement', 'announcements') | join('；') }}
mode: single
```

## 開發與驗證

`tests/fixtures/dgpa_20261022.html` 是 2026-10-22 擷取的官方頁面測試樣本，不是內建即時資料。執行測試不依賴外部網路。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python scripts/build_release.py
```

Home Assistant 2025.1.4 為本機測試基準（Python 3.12）。本整合以現行 coordinator、config flow、options flow、sensor API 撰寫；其他 HA 版本仍應在自己的環境驗證。一般公告頁要求完整 22 縣市及有效日期；官方明確提供「無停班停課訊息」空資料表格時，則驗證表頭、公告日期與更新時間後正常載入。其他不完整頁面及錯誤頁仍會標為無法使用，避免誤當作正常上班上課。

實作參考：[Home Assistant 資料更新](https://developers.home-assistant.io/docs/integration_fetching_data/)、[設定流程](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)、[Sensor](https://developers.home-assistant.io/docs/core/entity/sensor/)。

## 1.0.1：DGPA 憑證相容性修正

若新版 Python 的嚴格驗證回報 `Missing Subject Key Identifier`，整合只針對 `www.dgpa.gov.tw:443` 的這項錯誤重試一次，使用獨立的憑證相容性 context。仍驗證受信任 CA、憑證有效期及主機名稱，不使用 `ssl=False`，不修改 HA 共用的 SSL 設定，也不跟隨重新導向。其他憑證錯誤維持失敗。

已安裝者請在 HACS 的此整合選單重新下載最新 `main`，然後重新啟動 Home Assistant。確認版本為 `1.3.2`，再重新載入整合。

## 1.1.0：合併停班停課與專案圖示

- 每縣市改為「今天停班停課」「明天停班停課」與「停班停課公告」3 個實體。
- 原本 `_today_work`、`_today_school`、`_tomorrow_work`、`_tomorrow_school` 實體在重新載入時會移除。自動化及儀表板請改用 `_today`、`_tomorrow`；若只關心停班，請判斷新實體的 `work_status` 屬性。
- 新狀態 `school_only` 與 `work_only` 保留停班／停課不同的情況，`suspended` 代表兩者皆停止。
- 新增透明背景的原創青藍颱風／琥珀提醒圖示。來源與生成提示見 [assets/README.md](assets/README.md)。
- 圖示隨整合放在 `brand/icon.png`；Home Assistant 2026.3 以上支援本機品牌圖示。舊版 HA 仍可使用整合，但不一定顯示品牌圖示。HACS 自己的列表是否顯示本機圖示取決於 HACS 版本。

HACS 重新下載最新 `main` 後，重新啟動 Home Assistant，並重新整理瀏覽器。

## 1.1.1：辨識已達／未達停班停課標準

支援「明天已達停止上班及上課標準」「明天未達停止上班及上課標準」，分別顯示 `criteria_met` 與 `criteria_not_met`。不再把這兩種文字中的「停止上班」片段誤判為實際停班，也不會因缺少「停止上課」而遺漏評估訊息。當同一日期另有明確的停止／照常公告時，優先顯示該公告。局部地區的標準評估與衝突評估不擴大解讀成全縣市結果，顯示 `undetermined` 並保留原文。

停班停課通知範例仍只對 `suspended` 觸發；若也想在「已達標準」時收到提醒，請另外處理 `criteria_met`。

## 1.2.0：手動更新資訊按鈕

新增共用的更新按鈕，可隨時更新全部縣市，並可在抓取失敗後重試。啟動及重新載入時立即抓取公告的既有行為保持不變。

## 1.3.0：整點、晚間密集與午夜更新整合

兩種模式都固定於每小時整點抓取公告，含每天 00:00。晚間模式另保留 20:00–20:15 可設定的追加更新，20:00 重疊去重；新安裝預設使用合併模式。跨日會先更新實體的今天／明天日期，再由共用排程抓取官方最新資料。

## 1.3.1：支援官方無公告頁面

官方沒有公告時，會用「無停班停課訊息。」單一列取代 22 縣市資料。整合現在能辨識這個有效的空資料版面，清除上一份公告並正常載入；每個縣市的公告顯示「無停班停課訊息。」，1.3.1 當時將今天與明天設為 `unannounced`；1.3.2 起依下方規則改為 `normal`（正常上班上課）。需要有效日期、更新時間及正確表頭，才接受這種空資料頁；缺少縣市資料的異常頁面仍視為抓取失敗。

## 1.3.2：無停班停課訊息時顯示正常上班上課

當官方有效頁面明確顯示「無停班停課訊息。」時，依本整合的顯示規則，該頁日期及次日的今天／明天實體顯示 `normal`（正常上班上課）。公告實體仍保留官方原文，並以 `no_announcements: true` 屬性標示狀態依據。這是整合對空公告頁的預設判定，並非官方對未來日期發布了逐縣市照常公告。

一般公告頁缺少特定日期、未宣布訊息或過期空公告超出涵蓋日期時，仍顯示 `unannounced`。網路與解析失敗維持 `unavailable`，不會顯示正常。實體 ID 與底層 `normal` 值不變。
