# 臺灣停班停課 — Home Assistant 自訂整合

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

1. 解壓縮 `dist/taiwan_work_school-1.0.0.zip`，將內含的 `custom_components` 合併至 Home Assistant 設定目錄。
2. 確認路徑為 `/config/custom_components/taiwan_work_school/manifest.json`，勿多包一層資料夾。
3. 重新啟動 Home Assistant。
4. 開啟「設定 → 裝置與服務 → 新增整合」，搜尋「臺灣停班停課」。
5. 複選縣市並設定更新模式。日後從整合卡片的設定選項修改，不需手動編輯 YAML。

若搜尋不到，先重新整理瀏覽器並確認上述路徑及 Home Assistant 日誌。這是可手動安裝的自訂整合，並非官方內建整合。GitHub 儲存庫：[MCChang-cmyk/taiwan-work-school-status](https://github.com/MCChang-cmyk/taiwan-work-school-status)。尚未登錄 HACS。

## 更新設定

所有縣市共用一次 HTTP 請求。初次安裝、Home Assistant 重新啟動、重新載入整合及儲存設定後，都會先抓一次資料。

| 模式 | 行為 |
| --- | --- |
| 每小時 | 首次抓取後，每隔一小時更新；不是固定整點 |
| 晚間 | 每天台灣時間 20:00 起，依間隔及總次數更新，最晚 20:15（含） |

晚間模式有兩個獨立參數：

- **間隔分鐘**：1–15。
- **總次數**：1–16，包含 20:00 的第一次。

公式：`間隔 ×（總次數 − 1）≤ 15`，超過會顯示錯誤，請調整後儲存。

預設為每小時模式；切換晚間時，預設間隔 3 分鐘、共 6 次，即 20:00、20:03、20:06、20:09、20:12、20:15。間隔 5 分鐘、共 4 次即 20:00、20:05、20:10、20:15。若次數用完，當天就停止，不強制補抓 20:15。

晚間模式在其他時段不自動連線。若 20:07 重新啟動，啟動時抓一次，接著只執行尚未到的 20:09、20:12、20:15，不補發錯過的請求。全部時間固定採 `Asia/Taipei`，與 HA 本身時區無關。可用 Home Assistant 的 `homeassistant.update_entity` 動作手動更新。

官方可能在 20:15 之後才公布或修改。若需要追蹤其他時段變動，請選每小時模式。

## 實體

每個縣市建立 5 個 sensor。以臺北市為例（若已存在相同 entity ID，HA 可能加上數字後綴）：

| 實體 ID | 用途 |
| --- | --- |
| `sensor.taiwan_work_school_taipei_announcement` | 公告摘要；完整內容在 `announcements` 屬性 |
| `sensor.taiwan_work_school_taipei_today_work` | 今天停班 |
| `sensor.taiwan_work_school_taipei_today_school` | 今天停課 |
| `sensor.taiwan_work_school_taipei_tomorrow_work` | 明天停班 |
| `sensor.taiwan_work_school_taipei_tomorrow_school` | 明天停課 |

狀態實體底層值：

| 值 | 中文顯示 | 解讀 |
| --- | --- | --- |
| `suspended` | 停止 | 公告為全縣市、全日停止上班或上課 |
| `normal` | 照常 | 公告為全縣市照常上班或上課 |
| `partial` | 局部或部分時段停止 | 有鄉鎮、學校或時段限制，須查看完整公告 |
| `unannounced` | 尚未宣布 | 未找到該日期可辨識的停班／停課結論；不代表照常 |
| `undetermined` | 無法判定 | 同一天的全縣市公告存在衝突，須查看原文 |
| `unavailable` | 無法使用 | 網路、HTTP 或頁面格式出錯；保留最後成功資料供查閱 |

所有實體包含 `county`、`report_date`、`source_updated`、`last_successful_fetch`、`next_update`、`source`、`announcements` 屬性。日期狀態實體另有 `target_date`。

解析以網頁標題日期為基準換算「今天／明天」，不以下載時間猜測；跨午夜本地重算今天／明天的實體（不額外連線），避免隔天仍顯示上一天的「明天」。未涵蓋新日期的舊公告會顯示 `unannounced`。公告摘要保留原文日期語意，可能屬於較早日期，請搭配 `report_date` 查看。

針對局部或半日公告採保守分類，不嘗試推算個別學校、鄉鎮或當前時刻是否停班。更改縣市會移除取消選取縣市的實體登錄，重新選取時會再建立。

## 自動化範例

以下只對「明天全縣市全天停止」發通知；局部停止請另外處理 `partial`。將 `notify.mobile_app_your_phone` 換成自己的通知動作。

```yaml
alias: 明天臺北市停班通知
triggers:
  - trigger: state
    entity_id: sensor.taiwan_work_school_taipei_tomorrow_work
    to: suspended
conditions: []
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: 臺北市明天停班
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

Home Assistant 2025.1.4 為本機測試基準（Python 3.12）。本整合以現行 coordinator、config flow、options flow、sensor API 撰寫；其他 HA 版本仍應在自己的環境驗證。頁面若改版，解析會要求完整 22 縣市及有效日期，失敗時標為無法使用，避免將錯誤頁當作正常上班上課。

實作參考：[Home Assistant 資料更新](https://developers.home-assistant.io/docs/integration_fetching_data/)、[設定流程](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)、[Sensor](https://developers.home-assistant.io/docs/core/entity/sensor/)。
