#!/usr/bin/env python3
"""Receipt scanning + expense analytics CLI.

Features:
- Manual entry for purchases without receipts.
- Receipt ingestion from image OCR (optional) or plain text.
- Automatic category bucketing.
- Daily, weekly, and monthly summaries.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DB_PATH = Path("expenses.db")

CATEGORY_RULES: dict[str, list[str]] = {
    "groceries": ["market", "grocery", "supermarket", "whole foods", "trader joe", "kroger"],
    "dining": ["restaurant", "cafe", "coffee", "bar", "pizza", "burger", "doordash", "ubereats"],
    "transport": ["uber", "lyft", "shell", "chevron", "exxon", "fuel", "gas"],
    "shopping": ["amazon", "target", "walmart", "best buy", "costco"],
    "health": ["pharmacy", "walgreens", "cvs", "clinic", "hospital", "dental"],
    "utilities": ["electric", "water", "internet", "phone", "verizon", "att", "comcast"],
    "entertainment": ["netflix", "spotify", "movie", "cinema", "game", "steam"],
    "travel": ["airlines", "hotel", "marriott", "hilton", "airbnb", "booking"],
}


@dataclass
class Expense:
    purchased_at: str
    merchant: str
    amount: float
    category: str
    source: str
    notes: str = ""
    metadata: dict | None = None


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchased_at TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            source TEXT NOT NULL,
            notes TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    return conn


def normalize_date(value: str | None) -> str:
    if value is None:
        return dt.date.today().isoformat()
    return dt.date.fromisoformat(value).isoformat()


def categorize(merchant: str, notes: str = "") -> str:
    haystack = f"{merchant} {notes}".lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(word in haystack for word in keywords):
            return category
    return "misc"


def insert_expense(conn: sqlite3.Connection, item: Expense) -> int:
    cursor = conn.execute(
        """
        INSERT INTO expenses (purchased_at, merchant, amount, category, source, notes, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.purchased_at,
            item.merchant,
            item.amount,
            item.category,
            item.source,
            item.notes,
            json.dumps(item.metadata or {}),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def extract_text_from_image(path: Path) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires Pillow + pytesseract installed. "
            "Run: pip install Pillow pytesseract"
        ) from exc

    image = Image.open(path)
    return pytesseract.image_to_string(image)


def parse_receipt_text(raw_text: str) -> tuple[str, float]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Receipt text is empty")

    merchant = lines[0][:120]

    money_matches = [
        float(match.replace(",", ""))
        for match in re.findall(r"\$?\s*([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]{2}))", raw_text)
    ]

    if not money_matches:
        raise ValueError("Unable to find amount in receipt text")

    amount = max(money_matches)
    return merchant, amount


def start_end_for_period(anchor: dt.date, period: str) -> tuple[str, str]:
    if period == "day":
        start = end = anchor
    elif period == "week":
        start = anchor - dt.timedelta(days=anchor.weekday())
        end = start + dt.timedelta(days=6)
    elif period == "month":
        start = anchor.replace(day=1)
        if anchor.month == 12:
            next_month = anchor.replace(year=anchor.year + 1, month=1, day=1)
        else:
            next_month = anchor.replace(month=anchor.month + 1, day=1)
        end = next_month - dt.timedelta(days=1)
    else:
        raise ValueError(f"Invalid period: {period}")
    return start.isoformat(), end.isoformat()


def query_summary(conn: sqlite3.Connection, start: str, end: str) -> tuple[list[sqlite3.Row], list[sqlite3.Row], float]:
    by_category = conn.execute(
        """
        SELECT category, COUNT(*) AS purchases, ROUND(SUM(amount), 2) AS total
        FROM expenses
        WHERE purchased_at BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (start, end),
    ).fetchall()

    by_merchant = conn.execute(
        """
        SELECT merchant, COUNT(*) AS purchases, ROUND(SUM(amount), 2) AS total
        FROM expenses
        WHERE purchased_at BETWEEN ? AND ?
        GROUP BY merchant
        ORDER BY total DESC
        LIMIT 5
        """,
        (start, end),
    ).fetchall()

    grand_total = conn.execute(
        "SELECT ROUND(COALESCE(SUM(amount), 0), 2) AS total FROM expenses WHERE purchased_at BETWEEN ? AND ?",
        (start, end),
    ).fetchone()["total"]

    return by_category, by_merchant, float(grand_total)


def render_summary(start: str, end: str, by_category: Iterable[sqlite3.Row], by_merchant: Iterable[sqlite3.Row], total: float) -> str:
    out: list[str] = [f"Summary: {start} to {end}", f"Total spend: ${total:.2f}", "", "By category:"]

    rows = list(by_category)
    if not rows:
        out.append("- No expenses found in this period")
    else:
        for row in rows:
            out.append(f"- {row['category']:<16} ${row['total']:.2f} ({row['purchases']} purchases)")

    out.append("\nTop merchants:")
    rows = list(by_merchant)
    if not rows:
        out.append("- No merchants found in this period")
    else:
        for row in rows:
            out.append(f"- {row['merchant']:<20} ${row['total']:.2f} ({row['purchases']} purchases)")

    return "\n".join(out)


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receipt scanner and expense analytics tool")
    sub = parser.add_subparsers(dest="command", required=True)

    add_manual = sub.add_parser("add-manual", help="Add an expense manually")
    add_manual.add_argument("--amount", type=float, required=True)
    add_manual.add_argument("--merchant", required=True)
    add_manual.add_argument("--category", default=None)
    add_manual.add_argument("--notes", default="")
    add_manual.add_argument("--date", default=None, help="YYYY-MM-DD")

    add_receipt = sub.add_parser("scan-receipt", help="Add expense from receipt text/image")
    source = add_receipt.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Path to plain-text receipt dump")
    source.add_argument("--image", help="Path to receipt image file")
    add_receipt.add_argument("--date", default=None, help="YYYY-MM-DD")
    add_receipt.add_argument("--notes", default="")

    summary = sub.add_parser("summary", help="Generate day/week/month summary")
    summary.add_argument("--period", choices=["day", "week", "month"], required=True)
    summary.add_argument("--date", default=None, help="Anchor date YYYY-MM-DD (default: today)")

    return parser


def cmd_add_manual(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    purchased_at = normalize_date(args.date)
    category = args.category or categorize(args.merchant, args.notes)
    expense = Expense(
        purchased_at=purchased_at,
        merchant=args.merchant,
        amount=round(args.amount, 2),
        category=category,
        source="manual",
        notes=args.notes,
    )
    expense_id = insert_expense(conn, expense)
    print(f"Saved manual expense #{expense_id}: ${expense.amount:.2f} at {expense.merchant} [{expense.category}]")


def cmd_scan_receipt(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    purchased_at = normalize_date(args.date)

    if args.text:
        text = Path(args.text).read_text(encoding="utf-8")
        source_label = "receipt_text"
        source_path = args.text
    else:
        text = extract_text_from_image(Path(args.image))
        source_label = "receipt_image"
        source_path = args.image

    merchant, amount = parse_receipt_text(text)
    category = categorize(merchant, args.notes)
    expense = Expense(
        purchased_at=purchased_at,
        merchant=merchant,
        amount=round(amount, 2),
        category=category,
        source=source_label,
        notes=args.notes,
        metadata={"source_path": source_path},
    )
    expense_id = insert_expense(conn, expense)
    print(f"Saved receipt expense #{expense_id}: ${expense.amount:.2f} at {expense.merchant} [{expense.category}]")


def cmd_summary(args: argparse.Namespace, conn: sqlite3.Connection) -> None:
    anchor = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    start, end = start_end_for_period(anchor, args.period)
    by_category, by_merchant, total = query_summary(conn, start, end)
    print(render_summary(start, end, by_category, by_merchant, total))


def main() -> None:
    parser = build_cli()
    args = parser.parse_args()
    conn = get_connection()

    if args.command == "add-manual":
        cmd_add_manual(args, conn)
    elif args.command == "scan-receipt":
        cmd_scan_receipt(args, conn)
    elif args.command == "summary":
        cmd_summary(args, conn)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
