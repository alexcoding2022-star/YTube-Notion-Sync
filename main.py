import os
import re
import json
import time
import random
import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import requests
import feedparser
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not GEMINI_API_KEY or not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("環境變數不足！請檢查 .env 或 GitHub Secrets 中的金鑰與 NOTION_DATABASE_ID！")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 乾淨的請求 Session，不放可能導致 Google 轉址的 CONSENT Cookie
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
})

DB_SCHEMA = None

def load_model_list() -> List[str]:
    models_env = os.getenv("GEMINI_MODELS", "")
    if models_env.strip():
        models = [m.strip() for m in models_env.split(",") if m.strip()]
        if models:
            return models
    return ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"]

def parse_markdown_templates_text(content: str) -> Dict[str, str]:
    templates = {}
    sections = re.split(r'(?m)^##\s+', content)
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        lines = sec.split("\n", 1)
        cat_name = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if cat_name and body:
            templates[cat_name] = body
    return templates

def load_prompt_templates() -> Dict[str, str]:
    templates_str = os.getenv("AI_PROMPT_TEMPLATES", "")
    if templates_str.strip():
        try:
            templates = parse_markdown_templates_text(templates_str)
            if templates:
                return templates
        except Exception:
            pass

    return {
        "教學實作類": "1. 【教學亮點】：一句話點出本單元核心技能與應用場景。\n2. 【步驟拆解】：依操作順序條列具體步驟。\n3. 【關鍵參數與提示詞】：整理設定值或 Prompt。\n4. 【實用避坑技巧】：提醒常犯錯誤與排除方法。",
        "新聞時事類": "1. 【焦點速覽】：100 字內摘要本次事件核心焦點。\n2. 【核心要點拆解】：條列關鍵事實與潛在影響。\n3. 【各方立場與反應】：整理相關利害關係人態度。\n4. 【深度觀察結論】：分析事件背後趨勢與後續關注指標。",
        "科技評測類": "1. 【結論先行】：以 3 句話總結總體評價與定位。\n2. 【核心規格與特色亮點】：列出最具突破性指標。\n3. 【優缺點深度對比】：清晰條列優勢與缺點。\n4. 【選購與適合族群建議】：指出推薦與應避開族群。",
        "通用知識類": "1. 【核心概念】：用一句話闡述底層邏輯。\n2. 【三大關鍵思維】：梳理 3 個最具啟發性觀點。\n3. 【生活與工作應用】：列出具體行動步驟。"
    }

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

def create_summary_notion_page(video_id: str, title: str, url: str, channel_name: str, pub_date: str, category: str, summary: str):
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

    for k in schema.keys():
        if k in ["Category", "類別", "分類"]:
            props[k] = {"select": {"name": category}}
            break

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
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"✨ AI 智慧總結（{category}）"}}],
                    "color": "blue_background"
                }
            }
        ] + split_text_blocks(summary)
    }

    resp = requests.post(endpoint, headers=NOTION_HEADERS, json=body)
    if resp.status_code == 200:
        print(f"    └─ ✅ 成功收錄至 Notion，完成【{category}】結構化總結！", flush=True)
    else:
        print(f"    └─ ❌ Notion 寫入失敗: {resp.status_code} - {resp.text}", flush=True)

def parse_iso_datetime(dt_str: str) -> Optional[datetime.datetime]:
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

def fetch_videos_via_rss(channel_id: str) -> List[Dict]:
    """使用原生 XML 解析 YouTube 官方 RSS，極速、秒級發布時間且 100% 免遭機器人驗證"""
    if not channel_id:
        return []
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = session.get(rss_url, timeout=10)
        if resp.status_code != 200 or not resp.content:
            print(f"  ⚠️ RSS HTTP 回應異常：{resp.status_code}", flush=True)
            return []

        # 優先使用 Python 內建 ElementTree 解析標準 Atom XML
        root = ET.fromstring(resp.content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/"
        }
        
        videos = []
        for entry in root.findall("atom:entry", ns)[:10]:
            v_id_node = entry.find("yt:videoId", ns)
            title_node = entry.find("atom:title", ns)
            pub_node = entry.find("atom:published", ns)
            desc_node = entry.find("media:group/media:description", ns)

            v_id = v_id_node.text.strip() if v_id_node is not None and v_id_node.text else ""
            title = title_node.text.strip() if title_node is not None and title_node.text else ""
            pub_str = pub_node.text.strip() if pub_node is not None and pub_node.text else ""
            desc = desc_node.text.strip() if desc_node is not None and desc_node.text else ""

            if not v_id:
                continue

            pub_dt = parse_iso_datetime(pub_str)
            if not pub_dt:
                pub_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)

            videos.append({
                "id": v_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={v_id}",
                "description": desc or "",
                "published_dt": pub_dt,
                "published_str": pub_dt.strftime("%Y-%m-%d")
            })
            
        return videos
    except Exception as e:
        print(f"  ⚠️ 原生 XML 解析異常：{e}，嘗試 feedparser 備援...", flush=True)

    # 備援：feedparser
    try:
        feed = feedparser.parse(rss_url)
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

def get_channel_videos(ch: Dict) -> List[Dict]:
    channel_id = ch.get("id")
    videos = []
    
    if channel_id and channel_id.startswith("UC"):
        videos = fetch_videos_via_rss(channel_id)
        if videos:
            print(f"  📡 RSS 成功取得 {len(videos)} 部最新影片資訊", flush=True)

    if not videos:
        print("  ⚠️ RSS 無法取得該頻道影片，略過。", flush=True)
        return []

    videos.sort(key=lambda x: x["published_dt"], reverse=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    recent_2_days = [
        v for v in videos 
        if -86400 <= (now - v["published_dt"]).total_seconds() <= 172800
    ]

    if not recent_2_days and videos:
        print(f"  ℹ️ 最近一部影片上架日期為：{videos[0]['published_str']}（超過 48 小時範圍）", flush=True)

    return recent_2_days

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

def summarize_content(title: str, text_content: str, templates: Dict[str, str], models: List[str]) -> Dict[str, str]:
    template_instructions = "\n\n".join([f"### 分類【{k}】之標準結構：\n{v}" for k, v in templates.items()])

    prompt = f"""你是一名專業知識轉化專家與教學設計顧問。請依據下方提供的影片資訊與逐字稿，以「臺灣繁體中文」產出結構化總結筆記。

【總結範本庫規則】：
請先判斷該影片最屬於哪一個分類（{ "、".join(templates.keys()) }），並嚴格套用該分類對應的結構規範進行撰寫：

{template_instructions}

---
【影片標題】：{title}
【影片內容片段】：
{text_content[:7500]}

---
【輸出格式嚴格規範】：
第一行：分類：[你所判斷的分類名稱]（例如：分類：教學實作類）
第二行起：嚴格依據該分類之標準結構輸出條列筆記，標題與小節請加粗（例如 **【教學亮點】** 或 **【核心概念】**）。"""

    for model_name in models:
        try:
            print(f"    ↳ 調用模型：{model_name} 產出筆記中...", flush=True)
            config = types.GenerateContentConfig(temperature=0.3)
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            raw = response.text.strip()
            category = list(templates.keys())[0] if templates else "通用知識類"
            summary = raw
            first_line = raw.split("\n", 1)[0]
            for cat in templates.keys():
                if cat in first_line:
                    category = cat
                    if len(raw.split("\n", 1)) > 1:
                        summary = raw.split("\n", 1)[1].strip()
                    break
            return {"category": category, "summary": summary}
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print(f"    ⚠️ [{model_name}] 配額限制 (429)，自動降級切換至下一個模型...", flush=True)
                time.sleep(1.5)
                continue
            else:
                print(f"    ⚠️ [{model_name}] 異常：{e}", flush=True)
                time.sleep(1.0)
                continue

    raise RuntimeError("所有設定的備用模型皆已嘗試完畢，配額耗盡。")

def main():
    print("=" * 65, flush=True)
    print("  YouTube 智慧資訊匯流 - 一鍵全自動巡邏與 AI 總結", flush=True)
    print("=" * 65, flush=True)

    if not os.path.exists("channels.json"):
        print("❌ 找不到 channels.json 設定檔！", flush=True)
        return

    with open("channels.json", "r", encoding="utf-8") as f:
        channels = json.load(f)

    templates = load_prompt_templates()
    models = load_model_list()

    total_added = 0

    for ch in channels:
        name = ch["name"]
        print(f"\n📡 正在巡邏頻道：{name} ...", flush=True)
        time.sleep(random.uniform(0.8, 1.2))

        target_videos = get_channel_videos(ch)

        if not target_videos:
            print("  💤 最近 2 天內無新影片，略過。", flush=True)
            continue

        for v in target_videos:
            if check_notion_exists(v["url"]):
                print(f"  ⏭️ [已存在略過]：{v['title']}", flush=True)
                continue

            print(f"\n  🎯 [發現新影片]：{v['title']} ({v['published_str']})", flush=True)
            
            transcript_text = get_transcript(v["id"])
            if transcript_text:
                raw_content = f"【字幕內容】\n{transcript_text}"
            else:
                raw_content = f"【影片簡介】\n{v['description']}"

            if len(raw_content.strip()) < 30:
                raw_content = f"標題：{v['title']}（無字幕且簡介過短）"

            try:
                res = summarize_content(v["title"], raw_content, templates, models)
                create_summary_notion_page(
                    v["id"], 
                    v["title"], 
                    v["url"], 
                    name, 
                    v["published_str"], 
                    res["category"], 
                    res["summary"]
                )
                total_added += 1
                time.sleep(2.0)
            except Exception as e:
                print(f"    ❌ 處理該影片時發生錯誤：{e}", flush=True)

    print("\n" + "=" * 65, flush=True)
    print(f"🎉 任務完成！本次共發現並處理 {total_added} 部新影片至 Notion。", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    main()