"""Verify interpretation against a real DGPA page and edge cases."""

from datetime import date
from pathlib import Path

import pytest

from custom_components.taiwan_work_school.const import CITIES
from custom_components.taiwan_work_school.parser import ParseError, Report, parse_html

FIXTURE = Path(__file__).parent / "fixtures/dgpa_20261022.html"


def test_real_page():
    report = parse_html(FIXTURE.read_text())
    assert len(report.announcements) == 22
    assert report.report_date == date(2026, 10, 22)
    assert report.source_updated.isoformat() == "2026-10-22T23:26:04+08:00"
    assert report.status("taipei", date(2026, 10, 23), "上班") == "suspended"
    assert report.status("taipei", date(2026, 10, 22), "上班") == "unannounced"
    assert report.status("kinmen", date(2026, 10, 23), "上課") == "normal"
    assert report.status("taitung", date(2026, 10, 23), "上班") == "partial"
    assert report.status("taoyuan", date(2026, 10, 22), "上課") == "partial"
    assert report.status("taoyuan", date(2026, 10, 23), "上課") == "suspended"
    assert report.status("taipei", date(2026, 10, 24), "上班") == "unannounced"


@pytest.mark.parametrize(
    ("text", "work", "school"),
    [
        ("今天停止上班、停止上課。", "suspended", "suspended"),
        ("照常上班、照常上課。", "normal", "normal"),
        ("今天照常上班、停止上課。", "normal", "suspended"),
        ("今天下午停止上班、停止上課。", "partial", "partial"),
        ("今天上午10時起停止上班、停止上課。", "partial", "partial"),
        ("某某國民小學:今天停止上班、停止上課。", "partial", "partial"),
        ("某某鄉：今天停止上班、停止上課。", "partial", "partial"),
        ("尚未宣布訊息", "unannounced", "unannounced"),
        ("", "unannounced", "unannounced"),
        ("今天停止上班、停止上課。今天照常上班、照常上課。", "undetermined", "undetermined"),
    ],
)
def test_status(text, work, school):
    report = Report(date(2026, 10, 22), None, {"taipei": (text,)})
    assert report.status("taipei", report.report_date, "上班") == work
    assert report.status("taipei", report.report_date, "上課") == school


@pytest.mark.parametrize(
    "text",
    ["115年10月23日停止上班、停止上課", "10月23日停止上班、停止上課", "明日停止上班、停止上課"],
)
def test_explicit_dates(text):
    report = Report(date(2026, 10, 22), None, {"taipei": (text,)})
    assert report.status("taipei", date(2026, 10, 23), "上班") == "suspended"
    assert report.status("taipei", date(2026, 10, 22), "上班") == "unannounced"


def test_new_year():
    report = Report(date(2026, 12, 31), None, {"taipei": ("1月1日停止上班、停止上課",)})
    assert report.status("taipei", date(2027, 1, 1), "上班") == "suspended"


def test_layout_changes_fail_closed():
    with pytest.raises(ParseError):
        parse_html("<html>Service temporarily unavailable</html>")
    with pytest.raises(ParseError):
        parse_html(FIXTURE.read_text().replace("基隆市", "未知縣市"))


def test_alias_and_blank_rows():
    html = FIXTURE.read_text().replace("臺北市", "台北市").replace("明天停止上班、停止上課。", "")
    report = parse_html(html)
    assert set(report.announcements) == set(CITIES)
    assert report.status("taipei", report.report_date, "上班") == "unannounced"
