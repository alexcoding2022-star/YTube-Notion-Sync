import os
import re
import json
import time
import random
import datetime
from typing import List, Dict, Optional
import requests
import feedparser
import yt_dlp
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("請檢查 .env 檔案中的 NOTION_API_KEY 與 NOTION_DATABASE_ID！")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

session = requests.Session()
session.cookies.set("SOCS", "CAESEwgDEgk0ODEzNzk5NDIaAnpoIAEaBgiA_LyaBg", domain=".youtube.com")
session.cookies.set("CONSENT", "PENDING+999", domain=".youtube.com")
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
})

DB_SCHEMA = None

def get_db_schema() -> Dict:
    global DB_SCHEMA
    if DB_SCHEMA is not None:
        return DB_SCHEMA
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    resp = requests.get(url, headers=NOTION_HEADERS)
    if resp.status_code == 200:
        DB_SCHEMA = resp.json().get("properties", {})
        return DB_SCHEMA
    return {}

def parse_iso_datetime(dt_str: str) -> Optional[datetime.datetime]:
    """解析 ISO 8601 或 YYYY-MM-DD 時間字串並轉為 UTC datetime"""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass

    try:
        date_part = dt_str.split("T")[0].split(" ")[0]
        dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
        return dt.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        pass
    return None

def get_video_real_upload_date(video_id: str) -> datetime.datetime:
    """精確解析單支影片真實發布日期（三層保險：HTML 正則 -> yt-dlp 精確擷取 -> 保守 7 天前）"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        resp = session.get(url, timeout=6)
        if resp.status_code == 200:
            patterns = [
                r'itemprop="datePublished"\s+content="([^"]+)"',
                r'itemprop="uploadDate"\s+content="([^"]+)"',
                r'"publishDate":"([^"]+)"',
                r'"uploadDate":"([^"]+)"'
            ]
            for pat in patterns:
                m = re.search(pat, resp.text)
                if m:
                    parsed = parse_iso_datetime(m.group(1))
                    if parsed:
                        return parsed
    except Exception:
        pass

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                ts = info.get("timestamp") or info.get("release_timestamp")
                if ts:
                    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                up_date = info.get("upload_date")
                if up_date and len(up_date) == 8:
                    dt = datetime.datetime.strptime(up_date, "%Y%m%d")
                    return dt.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        pass

    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)

def fetch_videos_via_rss(channel_id: str) -> List[Dict]:
    """優先透過官方 RSS Feed 取得最新影片與 100% 精確發布時間"""
    if not channel_id:
        return []
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            return []
        videos = []
        for entry in feed.entries[:10]:
            v_id = entry.get("yt_videoid")
            if not v_id:
                link = entry.get("link", "")
                m = re.search(r'v=([a-zA-Z0-9_-]{11})', link)
                v_id = m.group(1) if m else None

            if not v_id:
                continue

            pub_str = entry.get("published", "")
            pub_dt = parse_iso_datetime(pub_str)
            if not pub_dt and hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_dt = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)

            if not pub_dt:
                pub_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)

            videos.append({
                "id": v_id,
                "title": entry.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={v_id}",
                "description": entry.get("summary", ""),
                "published_dt": pub_dt,
                "published_str": pub_dt.strftime("%Y-%m-%d")
            })
        return videos
    except Exception:
        return []

def extract_channel_videos_via_ytdlp(channel_target: str) -> List[Dict]:
    """備用：若無 channel_id 則透過 yt-dlp 抽取"""
    target = channel_target.strip()
    if target.startswith("http"):
        url = target
    elif target.startswith("@"):
        url = f"https://www.youtube.com/{target}/videos"
    elif target.startswith("UC") and len(target) == 24:
        url = f"https://www.youtube.com/channel/{target}/videos"
    else:
        url = f"https://www.youtube.com/@{target}/videos"

    ydl_opts = {
        'playlistend': 10,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
        'extract_flat': True,
        'http_headers': {
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        },
        'extractor_args': {
            'youtube': {
                'lang': ['zh-TW', 'zh-Hant']
            }
        }
    }

    raw_videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return []
            entries = info.get('entries', [])
            for e in entries:
                if not e:
                    continue
                v_id = e.get('id')
                title = e.get('title')
                if not v_id or not title:
                    continue
                raw_videos.append({
                    "id": v_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={v_id}",
                    "description": e.get('description', '') or ""
                })
    except Exception as e:
        print(f"  └─ 擷取清單時發生異常：{e}")
        return []

    if not raw_videos:
        return []

    print(f"  ⚡ 正在精確比對這 {len(raw_videos)} 部影片的真實發布日期...")
    final_videos = []
    for item in raw_videos:
        real_dt = get_video_real_upload_date(item["id"])
        item["published_dt"] = real_dt
        item["published_str"] = real_dt.strftime("%Y-%m-%d")
        final_videos.append(item)
        time.sleep(0.1)

    return final_videos

def get_channel_videos(ch: Dict) -> List[Dict]:
    channel_id = ch.get("id")
    videos = []

    if channel_id and channel_id.startswith("UC"):
        videos = fetch_videos_via_rss(channel_id)

    if not videos:
        target = ch.get("handle") or ch.get("url") or ch.get("id")
        videos = extract_channel_videos_via_ytdlp(target)

    if not videos:
        print("  ⚠️ 警告：該頻道未能抓取到任何影片內容。")
        return []

    videos.sort(key=lambda x: x["published_dt"], reverse=True)

    print(f"\n  📋 【頻道最後 {len(videos)} 部影片數據（真實日期）】")
    for idx, v in enumerate(videos, 1):
        print(f"    [{idx:02d}] 發布日期: {v['published_str']} | ID: {v['id']}")
        print(f"         標題: {v['title']}")
        print(f"         連結: {v['url']}")
    print("  " + "-" * 65)

    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 嚴格篩選最近 2 天（48 小時內）
    # -86400s 為防範跨時區/時鐘誤差之負秒數容錯
    recent_2_days = [
        v for v in videos 
        if -86400 <= (now - v["published_dt"]).total_seconds() <= 172800
    ]

    if recent_2_days:
        print(f"  🎯 篩選結果：符合「最近 2 天內」新片，共 {len(recent_2_days)} 部準備進行 Notion 比對")
        return recent_2_days
    else:
        print(f"  💤 篩選結果：該頻道最近 2 天內無發布新片，略過處理。")
        return []

def get_transcript(video_id: str) -> Optional[str]:
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
        transcript = None
        for code in ['zh-TW', 'zh-Hant', 'zh', 'zh-CN', 'en']:
            try:
                transcript = transcript_list.find_transcript([code])
                break
            except Exception:
                continue

        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['zh-TW', 'zh-Hant', 'zh', 'zh-CN', 'en'])
            except Exception:
                transcript = None

        if transcript:
            data = transcript.fetch()
            lines = []
            for seg in data:
                text_val = getattr(seg, 'text', None)
                if text_val is None and isinstance(seg, dict):
                    text_val = seg.get('text', '')
                if text_val:
                    lines.append(str(text_val))
            return " ".join(lines)
    except Exception:
        pass
    return None

def check_notion_exists(video_url: str) -> bool:
    schema = get_db_schema()
    url_key = "URL"
    for k, v in schema.items():
        if v.get("type") == "url":
            url_key = k
            break

    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": url_key,
            "url": {"equals": video_url}
        }
    }
    resp = requests.post(query_url, headers=NOTION_HEADERS, json=payload)
    if resp.status_code == 200:
        return len(resp.json().get("results", [])) > 0
    return False

def split_text_blocks(text: str, max_len: int = 1900) -> List[Dict]:
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    blocks = []
    for chunk in chunks:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    return blocks

def create_pending_notion_page(video_id: str, title: str, url: str, channel_name: str, pub_date: str, raw_content: str):
    schema = get_db_schema()
    props = {}

    for k, v in schema.items():
        if v.get("type") == "title":
            props[k] = {"title": [{"type": "text", "text": {"content": title}}]}
            break

    for k, v in schema.items():
        if v.get("type") == "url":
            props[k] = {"url": url}
            break

    if "Channel" in schema:
        t = schema["Channel"].get("type")
        if t == "select":
            props["Channel"] = {"select": {"name": channel_name[:100]}}
        elif t == "rich_text":
            props["Channel"] = {"rich_text": [{"type": "text", "text": {"content": channel_name[:100]}}]}

    if "Published" in schema:
        t = schema["Published"].get("type")
        if t == "date":
            props["Published"] = {"date": {"start": pub_date}}

    # YouTube 官方高清封面網址
    cover_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    endpoint = "https://api.notion.com/v1/pages"
    body = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "cover": {
            "type": "external",
            "external": {"url": cover_url}
        },
        "properties": props,
        "children": [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": "📌 此影片已成功收錄。執行「02_AI智慧總結.bat」可隨時產出結構化筆記。"}}],
                    "icon": {"emoji": "⏳"}
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "原始內容與逐字稿存檔"}}]
                }
            }
        ] + split_text_blocks(raw_content)
    }

    resp = requests.post(endpoint, headers=NOTION_HEADERS, json=body)
    if resp.status_code == 200:
        print(f"    └─ 成功登錄至 Notion（含封面）！")
    else:
        print(f"    └─ 寫入失敗: {resp.status_code} - {resp.text}")

def main():
    if not os.path.exists("channels.json"):
        print("找不到 channels.json！")
        return

    with open("channels.json", "r", encoding="utf-8") as f:
        channels = json.load(f)

    schema = get_db_schema()
    print(f"Notion 資料庫連線正常，已識別欄位：{list(schema.keys())}")

    new_found = 0
    for ch in channels:
        name = ch["name"]
        print(f"\n================ 巡邏頻道: {name} ================")
        time.sleep(random.uniform(1.0, 1.5))

        target_videos = get_channel_videos(ch)

        for v in target_videos:
            if check_notion_exists(v["url"]):
                print(f"  [已存在] 跳過：{v['title']}")
                continue

            print(f"  [新發現] 寫入中：{v['title']} ({v['published_str']})")
            transcript_text = get_transcript(v["id"])
            if transcript_text:
                raw_content = f"【字幕內容】\n{transcript_text}"
            else:
                raw_content = f"【影片簡介】\n{v['description']}"

            if len(raw_content.strip()) < 30:
                raw_content = f"標題：{v['title']}（無字幕且簡介過短）"

            create_pending_notion_page(v["id"], v["title"], v["url"], name, v["published_str"], raw_content)
            new_found += 1
            time.sleep(1.2)

    print(f"\n========================================================")
    print(f"巡邏完成！本次共發現並收錄 {new_found} 部最近 2 天新影片至 Notion。")
    print(f"========================================================")

if __name__ == "__main__":
    main()
