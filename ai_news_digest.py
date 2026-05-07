#!/usr/bin/env python3
"""Daily AI news digest.

Fetches AI-related RSS/Atom feeds, keeps items published during the previous
local calendar day, deduplicates them, and sends a morning digest by email (or
prints it if SMTP settings are not configured).
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import smtplib
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

AI_KEYWORDS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "large language model",
    "llm",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "mistral",
    "perplexity",
    "hugging face",
    "nvidia",
    "copilot",
    "agentic",
    "neural",
)

DEFAULT_FEEDS = (
    "https://news.google.com/rss/search?q="
    + urllib.parse.quote('("artificial intelligence" OR AI OR OpenAI OR Anthropic OR ChatGPT OR Claude OR Gemini OR "machine learning") when:2d')
    + "&hl=en-US&gl=US&ceid=US:en",
    "https://openai.com/news/rss.xml",
    "https://www.anthropic.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
)

CONFIG_PATHS = (
    Path("ai_news_config.json"),
    Path.home() / ".config" / "ai-news-digest" / "config.json",
)


@dataclasses.dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    published: dt.datetime
    source: str
    summary: str = ""


def previous_day_window(timezone_name: str, now: dt.datetime | None = None) -> tuple[dt.datetime, dt.datetime]:
    """Return the previous local day as an aware [start, end) datetime range."""
    timezone = ZoneInfo(timezone_name)
    current = now.astimezone(timezone) if now else dt.datetime.now(timezone)
    today = current.date()
    start = dt.datetime.combine(today - dt.timedelta(days=1), dt.time.min, timezone)
    end = dt.datetime.combine(today, dt.time.min, timezone)
    return start, end


def load_config(path: str | None) -> dict:
    """Load JSON configuration from an explicit path or the first default path that exists."""
    candidates = [Path(path)] if path else list(CONFIG_PATHS)
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    return {}


def fetch_url(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-news-digest/1.0 (+https://github.com/local/ai-news-digest)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def text_from(element: ET.Element | None, default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return html.unescape(re.sub(r"\s+", " ", element.text)).strip()


def parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = value.strip()
    for parser in (email.utils.parsedate_to_datetime, lambda text: dt.datetime.fromisoformat(text.replace("Z", "+00:00"))):
        try:
            parsed = parser(value)
        except (TypeError, ValueError, IndexError):
            continue
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    return None


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def parse_feed(xml_bytes: bytes, fallback_source: str) -> list[NewsItem]:
    root = ET.fromstring(xml_bytes)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    channel = root.find("channel")
    source = text_from(channel.find("title") if channel is not None else None, fallback_source)
    items: list[NewsItem] = []

    for item in root.findall(".//item"):
        title = text_from(item.find("title"))
        link = text_from(item.find("link"))
        published = parse_date(text_from(item.find("pubDate")) or text_from(item.find("{http://purl.org/dc/elements/1.1/}date")))
        summary = strip_html(text_from(item.find("description")))
        item_source = text_from(item.find("source"), source)
        if title and link and published:
            items.append(NewsItem(title=title, link=link, published=published, source=item_source, summary=summary))

    for entry in root.findall(".//atom:entry", ns):
        title = text_from(entry.find("atom:title", ns))
        link_element = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
        link = link_element.attrib.get("href", "") if link_element is not None else ""
        published = parse_date(text_from(entry.find("atom:published", ns)) or text_from(entry.find("atom:updated", ns)))
        summary = strip_html(text_from(entry.find("atom:summary", ns)) or text_from(entry.find("atom:content", ns)))
        if title and link and published:
            items.append(NewsItem(title=title, link=link, published=published, source=source, summary=summary))

    return items


def is_ai_related(item: NewsItem, keywords: Iterable[str]) -> bool:
    searchable = f"{item.title} {item.summary}".lower()
    for keyword in keywords:
        normalized = keyword.lower()
        if len(normalized) <= 3 and normalized.isalnum():
            if re.search(rf"\b{re.escape(normalized)}\b", searchable):
                return True
        elif normalized in searchable:
            return True
    return False


def canonical_key(item: NewsItem) -> str:
    parsed = urllib.parse.urlparse(item.link)
    if parsed.netloc:
        normalized_link = urllib.parse.urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))
        return normalized_link
    normalized_title = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
    return hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()


def collect_news(feeds: Iterable[str], start: dt.datetime, end: dt.datetime, keywords: Iterable[str], timeout: int) -> tuple[list[NewsItem], list[str]]:
    items_by_key: dict[str, NewsItem] = {}
    warnings: list[str] = []
    for feed_url in feeds:
        try:
            xml_bytes = fetch_url(feed_url, timeout)
            parsed_items = parse_feed(xml_bytes, fallback_source=urllib.parse.urlparse(feed_url).netloc)
        except Exception as exc:  # noqa: BLE001 - keep the digest running if one feed is down.
            warnings.append(f"Could not fetch {feed_url}: {exc}")
            continue
        for item in parsed_items:
            local_published = item.published.astimezone(start.tzinfo)
            if start <= local_published < end and is_ai_related(item, keywords):
                normalized_item = dataclasses.replace(item, published=local_published)
                items_by_key.setdefault(canonical_key(normalized_item), normalized_item)
    return sorted(items_by_key.values(), key=lambda news: news.published, reverse=True), warnings


def render_digest(items: list[NewsItem], warnings: list[str], start: dt.datetime, end: dt.datetime) -> tuple[str, str]:
    day_label = start.strftime("%A, %B %-d, %Y") if os.name != "nt" else start.strftime("%A, %B %#d, %Y")
    subject = f"AI news digest for {start.date().isoformat()} ({len(items)} stories)"
    lines = [f"AI news digest for {day_label}", "", f"Coverage window: {start.isoformat()} through {end.isoformat()}", ""]
    if items:
        for index, item in enumerate(items, start=1):
            summary = textwrap.shorten(item.summary, width=260, placeholder="…") if item.summary else "No summary provided by feed."
            lines.extend(
                [
                    f"{index}. {item.title}",
                    f"   Source: {item.source}",
                    f"   Published: {item.published.strftime('%Y-%m-%d %H:%M %Z')}",
                    f"   Link: {item.link}",
                    f"   Summary: {summary}",
                    "",
                ]
            )
    else:
        lines.extend(["No AI-related stories were found for the previous day.", ""])
    if warnings:
        lines.append("Feed warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    return subject, "\n".join(lines).strip() + "\n"


def send_email(subject: str, body: str, config: dict) -> bool:
    smtp_host = config.get("smtp_host") or os.environ.get("AI_NEWS_SMTP_HOST")
    smtp_port = int(config.get("smtp_port") or os.environ.get("AI_NEWS_SMTP_PORT", "587"))
    username = config.get("smtp_username") or os.environ.get("AI_NEWS_SMTP_USERNAME")
    password = config.get("smtp_password") or os.environ.get("AI_NEWS_SMTP_PASSWORD")
    sender = config.get("email_from") or os.environ.get("AI_NEWS_EMAIL_FROM") or username
    recipient = config.get("email_to") or os.environ.get("AI_NEWS_EMAIL_TO")

    if not smtp_host or not sender or not recipient:
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True


def install_cron(script_path: Path, run_at: str, config_path: str | None) -> None:
    hour, minute = run_at.split(":", maxsplit=1)
    command = f"{minute} {hour} * * * {sys.executable} {script_path}"
    if config_path:
        command += f" --config {Path(config_path).expanduser().resolve()}"
    command += " >> $HOME/ai-news-digest.log 2>&1"

    existing = subprocess.run(["crontab", "-l"], check=False, capture_output=True, text=True)
    current_lines = existing.stdout.splitlines() if existing.returncode == 0 else []
    marker = str(script_path)
    new_lines = [line for line in current_lines if marker not in line]
    new_lines.append(command)
    subprocess.run(["crontab", "-"], input="\n".join(new_lines) + "\n", text=True, check=True)
    print(f"Installed daily cron job: {command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a daily digest of AI-related news from the previous day.")
    parser.add_argument("--config", help="Path to a JSON config file. Defaults to ai_news_config.json or ~/.config/ai-news-digest/config.json.")
    parser.add_argument("--timezone", help="IANA timezone for the previous-day window, e.g. America/New_York.")
    parser.add_argument("--run-at", default="08:00", help="Morning time used by --install-cron in 24-hour HH:MM format. Default: 08:00.")
    parser.add_argument("--install-cron", action="store_true", help="Install this script in the current user's crontab to run every morning.")
    parser.add_argument("--print-only", action="store_true", help="Print the digest instead of sending email, even when SMTP is configured.")
    parser.add_argument("--timeout", type=int, default=20, help="Seconds to wait for each feed. Default: 20.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    timezone_name = args.timezone or config.get("timezone") or os.environ.get("AI_NEWS_TIMEZONE") or "America/New_York"

    if args.install_cron:
        install_cron(Path(__file__).resolve(), args.run_at, args.config)
        return 0

    start, end = previous_day_window(timezone_name)
    feeds = config.get("feeds") or list(DEFAULT_FEEDS)
    keywords = config.get("keywords") or list(AI_KEYWORDS)
    items, warnings = collect_news(feeds=feeds, start=start, end=end, keywords=keywords, timeout=args.timeout)
    subject, body = render_digest(items, warnings, start, end)

    if not args.print_only and send_email(subject, body, config):
        print(f"Sent: {subject}")
    else:
        print(f"Subject: {subject}\n")
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
