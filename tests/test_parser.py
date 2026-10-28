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


@pytest.mark.parametrize(
    "text,expected",
    [
        ("今天停止上班、停止上課。", "suspended"),
        ("今天照常上班、照常上課。", "normal"),
        ("今天照常上班、停止上課。", "school_only"),
        ("今天停止上班、照常上課。", "work_only"),
        ("某國小：今天停止上班、停止上課。", "partial"),
        ("今天下午停止上班、停止上課。", "partial"),
        ("今天停止上班。", "undetermined"),
        ("今天停止上課。", "undetermined"),
        ("尚未宣布訊息", "unannounced"),
        ("今天停止上班、停止上課。今天照常上班。", "undetermined"),
    ],
)
def test_combined_status(text, expected):
    report = Report(date(2026, 10, 23), None, {"taipei": (text,)})
    assert report.combined_status("taipei", report.report_date) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("明天已達停止上班及上課標準。", "criteria_met"),
        ("明天未達停止上班及上課標準。", "criteria_not_met"),
        ("明日已達停止上班及停止上課標準。", "criteria_met"),
        ("明天已達停止上課及上班標準。", "criteria_met"),
        ("明天未達停止上班及上課標準。明天照常上班、照常上課。", "normal"),
        ("明天已達停止上班及上課標準。明天停止上班、停止上課。", "suspended"),
        ("明天未達停止上班及上課標準。明天停止上班、停止上課。", "suspended"),
        ("某鄉：明天已達停止上班及上課標準。", "undetermined"),
        ("明天已達停止上班及上課標準。明天未達停止上班及上課標準。", "undetermined"),
    ],
)
def test_criteria_assessments_are_not_closure_decisions(text, expected):
    report = Report(date(2026, 10, 23), None, {"taipei": ("今天停止上班、停止上課。", text)})
    assert report.combined_status("taipei", date(2026, 10, 23)) == "suspended"
    assert report.combined_status("taipei", date(2026, 10, 24)) == expected
    assert report.status("taipei", date(2026, 10, 24), "上班") == expected
    assert report.status("taipei", date(2026, 10, 24), "上課") == expected


def test_real_criteria_page():
    html = (FIXTURE.parent / "dgpa_20261023_criteria.html").read_text()
    report = parse_html(html)
    assert report.report_date == date(2026, 10, 23)
    assert report.combined_status("taipei", date(2026, 10, 23)) == "suspended"
    assert report.combined_status("taipei", date(2026, 10, 24)) == "criteria_met"
    assert report.combined_status("kaohsiung", date(2026, 10, 24)) == "criteria_not_met"
    assert report.combined_status("hualien", date(2026, 10, 24)) == "criteria_not_met"
    assert report.combined_status("kinmen", date(2026, 10, 23)) == "normal"


def test_official_no_announcement_page():
    html = (FIXTURE.parent / "dgpa_20261025_no_announcements.html").read_text()
    report = parse_html(html)
    assert report.report_date == date(2026, 10, 25)
    assert report.source_updated is not None
    assert set(report.announcements) == set(CITIES)
    for city in CITIES:
        assert report.announcements[city] == ("無停班停課訊息。",)
        assert report.combined_status(city, date(2026, 10, 25)) == "normal"
        assert report.combined_status(city, date(2026, 10, 26)) == "unannounced"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda html: html.replace("無停班停課訊息。", "服務暫時無法使用"),
        lambda html: html.replace("縣市名稱", "unknown"),
        lambda html: html.replace("更新時間", "updated"),
        lambda html: html.replace("天然災害停止上班", "unknown"),
        lambda html: html.replace("無停班停課訊息。", "無停班停課訊息。系統錯誤"),
        lambda html: html.replace(
            '<TBODY class="Table_Body">',
            '<TBODY class="Table_Body"><TR><TD>臺北市</TD><TD>今天停止上班、停止上課。</TD></TR>',
        ),
    ],
)
def test_invalid_empty_pages_are_not_accepted(mutation):
    html = (FIXTURE.parent / "dgpa_20261025_no_announcements.html").read_text()
    with pytest.raises(ParseError):
        parse_html(mutation(html))


def test_empty_report_does_not_mark_unrelated_dates_as_normal():
    html = (FIXTURE.parent / "dgpa_20261025_no_announcements.html").read_text()
    report = parse_html(html)
    assert report.no_announcements
    assert report.combined_status("taipei", date(2026, 10, 24)) == "unannounced"
    assert report.combined_status("taipei", date(2026, 10, 27)) == "unannounced"


def test_missing_county_announcement_is_still_unannounced():
    report = Report(date(2026, 10, 25), None, {"taipei": ()})
    assert not report.no_announcements
    assert report.combined_status("taipei", date(2026, 10, 25)) == "unannounced"
    assert report.combined_status("taipei", date(2026, 10, 26)) == "unannounced"


def test_empty_report_normal_follows_page_date_after_rollover():
    from dataclasses import replace

    html = (FIXTURE.parent / "dgpa_20261025_no_announcements.html").read_text()
    old_report = parse_html(html)
    assert old_report.combined_status("taipei", date(2026, 10, 26)) == "unannounced"
    new_report = replace(old_report, report_date=date(2026, 10, 26))
    assert new_report.combined_status("taipei", date(2026, 10, 26)) == "normal"
    assert new_report.combined_status("taipei", date(2026, 10, 27)) == "unannounced"
