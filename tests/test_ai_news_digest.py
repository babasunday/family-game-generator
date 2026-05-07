import datetime as dt

import ai_news_digest as digest


RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example AI Feed</title>
    <item>
      <title>New artificial intelligence model launches</title>
      <link>https://example.com/model?utm_source=rss</link>
      <pubDate>Wed, 06 May 2026 13:00:00 GMT</pubDate>
      <description><![CDATA[Researchers released an LLM for testing.]]></description>
      <source>Example News</source>
    </item>
    <item>
      <title>Sports update</title>
      <link>https://example.com/sports</link>
      <pubDate>Wed, 06 May 2026 14:00:00 GMT</pubDate>
      <description>Not about technology.</description>
    </item>
  </channel>
</rss>
"""


def test_previous_day_window_uses_requested_timezone():
    now = dt.datetime(2026, 5, 7, 12, tzinfo=dt.timezone.utc)
    start, end = digest.previous_day_window("America/New_York", now)

    assert start.isoformat() == "2026-05-06T00:00:00-04:00"
    assert end.isoformat() == "2026-05-07T00:00:00-04:00"


def test_parse_feed_and_keyword_filter():
    items = digest.parse_feed(RSS, "fallback.example")

    assert len(items) == 2
    assert digest.is_ai_related(items[0], digest.AI_KEYWORDS)
    assert not digest.is_ai_related(items[1], digest.AI_KEYWORDS)


def test_render_digest_includes_story_details():
    item = digest.parse_feed(RSS, "fallback.example")[0]
    start = dt.datetime(2026, 5, 6, tzinfo=dt.timezone.utc)
    end = dt.datetime(2026, 5, 7, tzinfo=dt.timezone.utc)

    subject, body = digest.render_digest([item], [], start, end)

    assert "1 stories" in subject
    assert "New artificial intelligence model launches" in body
    assert "https://example.com/model" in body
