"""Constants for Taiwan work and school announcements."""

from zoneinfo import ZoneInfo

DOMAIN = "taiwan_work_school"
NAME = "臺灣停班停課"
SOURCE_URL = "https://www.dgpa.gov.tw/typh/daily/nds.html"
TAIPEI = ZoneInfo("Asia/Taipei")
CONF_CITIES = "cities"
CONF_MODE = "update_mode"
CONF_INTERVAL = "evening_interval"
CONF_COUNT = "evening_count"
DEFAULTS = {CONF_MODE: "hourly", CONF_INTERVAL: 3, CONF_COUNT: 6}
CITIES = {
    "keelung": "基隆市",
    "taipei": "臺北市",
    "new_taipei": "新北市",
    "taoyuan": "桃園市",
    "hsinchu_city": "新竹市",
    "hsinchu_county": "新竹縣",
    "miaoli": "苗栗縣",
    "taichung": "臺中市",
    "changhua": "彰化縣",
    "yunlin": "雲林縣",
    "nantou": "南投縣",
    "chiayi_city": "嘉義市",
    "chiayi_county": "嘉義縣",
    "tainan": "臺南市",
    "kaohsiung": "高雄市",
    "pingtung": "屏東縣",
    "yilan": "宜蘭縣",
    "hualien": "花蓮縣",
    "taitung": "臺東縣",
    "penghu": "澎湖縣",
    "lienchiang": "連江縣",
    "kinmen": "金門縣",
}
STATUS_OPTIONS = [
    "suspended",
    "normal",
    "partial",
    "unannounced",
    "undetermined",
    "work_only",
    "school_only",
    "criteria_met",
    "criteria_not_met",
]
