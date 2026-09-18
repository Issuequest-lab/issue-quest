"""Fetch Japan's public Trends RSS; never replace good data on failure."""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = 'https://trends.google.com/trending/rss?geo=JP'

def parse_feed(raw):
    root = ET.fromstring(raw)
    topics = list(dict.fromkeys(
        (item.findtext('title') or '').strip()
        for item in root.findall('./channel/item')
    ))
    topics = [t for t in topics if t and len(t) <= 200][:12]
    if len(topics) < 5:
        raise ValueError('Not enough valid trends; retaining previous data')
    return topics

def main():
    request = urllib.request.Request(URL, headers={'User-Agent': 'IssueQuest/1.1'})
    with urllib.request.urlopen(request, timeout=45) as response:
        topics = parse_feed(response.read(2_000_000))
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    payload = dict(schemaVersion=2, updatedAt=now.date().isoformat(),
                   fetchedAt=now.isoformat(), source='Google Trends Japan',
                   sourceUrl=URL, mode='live', topics=topics)
    target = Path(__file__).resolve().parents[1] / 'daily-issues.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, target)
    print(f'Updated {len(topics)} topics: {payload["updatedAt"]} JST')

if __name__ == '__main__':
    main()
