"""Conservative, date-aware parser; independent of Home Assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

from .const import CITIES, TAIPEI


class ParseError(ValueError):
    """The response is not a recognizable DGPA announcement."""


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("台", "臺")


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag in ("br", "p", "div") and self.cell is not None:
            self.cell.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag in ("p", "div") and self.cell is not None:
            self.cell.append("\n")

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)


@dataclass(frozen=True)
class Report:
    report_date: date
    source_updated: datetime | None
    announcements: dict[str, tuple[str, ...]]

    def status(self, city: str, target: date, kind: str) -> str:
        """Never infer full-city closure from a scoped or timed announcement."""
        full: set[str] = set()
        partial = False
        scoped_normal = False
        for line in self.announcements.get(city, ()):
            for segment in re.split(r"[。；;\n]+", normalize(line)):
                if not segment or _target_date(segment, self.report_date) != target:
                    continue
                closed = f"停止{kind}" in segment
                normal = f"照常{kind}" in segment
                if not (closed or normal):
                    continue
                scoped = bool(
                    re.search(
                        r"[:：]|(?:上午|下午|晚上|晚間|中午|\d{1,2}[時:：]|起|部分|部份)", segment
                    )
                )
                if scoped:
                    partial |= closed
                    scoped_normal |= normal
                else:
                    full.add("suspended" if closed else "normal")
        if len(full) > 1:
            return "undetermined"
        if partial or (scoped_normal and "suspended" in full):
            return "partial"
        return next(iter(full), "unannounced")


def _target_date(text: str, base: date) -> date | None:
    explicit = re.search(r"(?:(\d{3,4})年)?(\d{1,2})月(\d{1,2})日", text)
    if explicit:
        year = int(explicit[1]) if explicit[1] else base.year
        if year < 1911:
            year += 1911
        try:
            result = date(year, int(explicit[2]), int(explicit[3]))
            if not explicit[1] and abs((result - base).days) > 180:
                result = result.replace(year=base.year + (1 if base.month == 12 else -1))
            return result
        except ValueError:
            return None
    if "明天" in text or "明日" in text:
        return base + timedelta(days=1)
    if "後天" in text:
        return base + timedelta(days=2)
    # Unqualified city-wide statements refer to the dated page, never fetch date.
    return base


def parse_html(html: str) -> Report:
    parser = _TableParser()
    parser.feed(html)
    text = normalize("".join(parser.text))
    header = re.search(r"(\d{3,4})年(\d{1,2})月(\d{1,2})日天然災害停止上班", text)
    if not header:
        raise ParseError("Missing announcement date")
    year = int(header[1])
    if year < 1911:
        year += 1911
    try:
        report_date = date(year, int(header[2]), int(header[3]))
        updated_match = re.search(r"更新時間[：:](\d{4}/\d{1,2}/\d{1,2})(\d{2}:\d{2}:\d{2})", text)
        updated = (
            datetime.strptime(" ".join(updated_match.groups()), "%Y/%m/%d %H:%M:%S").replace(
                tzinfo=TAIPEI
            )
            if updated_match
            else None
        )
    except ValueError as err:
        raise ParseError("Invalid announcement date") from err
    names = {normalize(name): key for key, name in CITIES.items()}
    announcements = {}
    for row in parser.rows:
        for index, cell in enumerate(row[:-1]):
            if (key := names.get(normalize(cell))) is not None:
                content = row[index + 1]
                lines = tuple(filter(None, (normalize(line) for line in content.splitlines())))
                if key in announcements:
                    raise ParseError("Duplicate county row")
                announcements[key] = lines
    # Fail closed on layout changes, error pages, and truncated downloads.
    if set(announcements) != set(CITIES):
        raise ParseError(f"Expected 22 county rows, found {len(announcements)}")
    return Report(report_date, updated, announcements)
