# Receipt Expense Tracker CLI

A lightweight tool to scan receipts and categorize expenses into buckets, with summaries for day/week/month windows.

## What it supports

- **Receipt ingestion** from:
  - text dump (`--text`)
  - image OCR (`--image`, optional dependency)
- **Manual entry** for purchases where no receipt is available.
- **Automatic categorization** into buckets like groceries, dining, transport, etc.
- **Analytics summaries** with:
  - total spend
  - spend by category
  - top merchants

All entries are saved in a local SQLite database `expenses.db`.

## Quick start

```bash
python3 receipt_tracker.py add-manual --merchant "Trader Joe's" --amount 42.55 --notes "weekly groceries"
python3 receipt_tracker.py summary --period day
```

## Commands

### 1) Add purchase manually

```bash
python3 receipt_tracker.py add-manual \
  --merchant "Corner Store" \
  --amount 12.40 \
  --notes "snacks" \
  --date 2026-04-23
```

Optional `--category` can override auto-bucketing.

### 2) Scan a receipt from text

```bash
python3 receipt_tracker.py scan-receipt --text sample_receipt.txt --date 2026-04-23
```

### 3) Scan a receipt from an image (OCR)

Install dependencies first:

```bash
pip install Pillow pytesseract
```

Then run:

```bash
python3 receipt_tracker.py scan-receipt --image ./receipt.jpg
```

### 4) Get summaries

```bash
# Daily summary for today
python3 receipt_tracker.py summary --period day

# Weekly summary for the week containing the provided date
python3 receipt_tracker.py summary --period week --date 2026-04-23

# Monthly summary
python3 receipt_tracker.py summary --period month --date 2026-04-01
```

## Notes

- For OCR mode, your system also needs the **Tesseract** binary installed.
- If a receipt has multiple amounts, the parser currently uses the **largest monetary value** as total.
- You can customize categories by editing `CATEGORY_RULES` in `receipt_tracker.py`.
