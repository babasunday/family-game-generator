# Daily AI News Digest

This repository contains a small Python program that sends you a morning update
with AI-related news published during the previous local calendar day.

The script uses RSS/Atom feeds, filters stories to the previous day, removes
obvious duplicates, and emails the digest through your SMTP account. If SMTP is
not configured, it prints the digest to the terminal so you can test it safely.

## Requirements

- Python 3.11 or newer
- Network access to RSS feeds
- Optional: an SMTP account for email delivery
- Optional: `cron` for automatic daily scheduling on Linux/macOS

No third-party Python packages are required.

## Quick start

1. Copy the example config:

   ```bash
   cp ai_news_config.example.json ai_news_config.json
   ```

2. Edit `ai_news_config.json` with your timezone and email settings.

3. Test the digest without sending email:

   ```bash
   python3 ai_news_digest.py --config ai_news_config.json --print-only
   ```

4. Install a daily 8:00 AM cron job:

   ```bash
   python3 ai_news_digest.py --config ai_news_config.json --install-cron --run-at 08:00
   ```

Cron output is appended to `~/ai-news-digest.log`.

## Configuration

The script looks for configuration in this order:

1. The file passed with `--config`
2. `./ai_news_config.json`
3. `~/.config/ai-news-digest/config.json`
4. Environment variables for SMTP and timezone settings

Supported environment variables:

- `AI_NEWS_TIMEZONE`
- `AI_NEWS_EMAIL_TO`
- `AI_NEWS_EMAIL_FROM`
- `AI_NEWS_SMTP_HOST`
- `AI_NEWS_SMTP_PORT`
- `AI_NEWS_SMTP_USERNAME`
- `AI_NEWS_SMTP_PASSWORD`

## Feeds

By default, the program checks a broad set of AI-focused sources, including
Google News AI search results and AI feeds from major labs and technology
publishers. You can override the defaults by adding a `feeds` array to your
config file:

```json
{
  "timezone": "America/New_York",
  "feeds": [
    "https://news.google.com/rss/search?q=artificial%20intelligence%20when:2d&hl=en-US&gl=US&ceid=US:en"
  ]
}
```

## Manual run examples

Print yesterday's AI news for New York time:

```bash
python3 ai_news_digest.py --timezone America/New_York --print-only
```

Send email using environment variables instead of a config file:

```bash
AI_NEWS_EMAIL_TO=you@example.com \
AI_NEWS_EMAIL_FROM=sender@example.com \
AI_NEWS_SMTP_HOST=smtp.example.com \
AI_NEWS_SMTP_USERNAME=sender@example.com \
AI_NEWS_SMTP_PASSWORD='app-password' \
python3 ai_news_digest.py
```
