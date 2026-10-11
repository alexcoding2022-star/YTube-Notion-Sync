\# YouTube 智慧資訊匯流與 Notion 自動化筆記系統 - 專案移交手冊



\*\*專案名稱\*\*：YouTube 智慧資訊匯流與 Notion 結構化總結自動化管線

\*\*版本編號\*\*：v4.0.0 (Production Stable - Integrated Single Pipeline)

\*\*文件更新日期\*\*：2026 年 10 月 11 日

\*\*專案目錄路徑\*\*：`E:\\antigravity\\YTube-Notion\\`

\*\*文件性質\*\*：系統架構移交、完整部署指南、單一設定驅動與全模組原始碼



\---



\## 1. 系統架構與設計核心理念



本系統旨在追蹤指定的 YouTube 頻道，自動篩選近期新片並透過 Gemini AI 生成結構化教學與知識筆記，自動同步至 Notion 資料庫。



\### 核心特色：

1\. \*\*單一管線整合 (Unified Pipeline)\*\*：將「巡邏頻道」與「AI 總結」合而為一（`main.py`），發現新片後即時取得逐字稿並調用 Gemini 生成結構化總結，直接寫入 Notion，無需暫存與二次清理逐字稿。

2\. \*\*單一設定檔驅動 (`.env`)\*\*：金鑰、備援模型清單（`GEMINI\_MODELS`）與多分類提示詞範本（`AI\_PROMPT\_TEMPLATES`）全部收攏於 `.env`，免除零散檔案管理。

3\. \*\*官方 RSS 優先與時間容錯\*\*：優先解析 YouTube 官方 RSS Feed 取得秒級發布時間，嚴格鎖定近 2 天（48 小時內）影片，並內建 `-86400s` 負秒數時區與時鐘容錯。

4\. \*\*模型無縫降級切換\*\*：調用 Gemini 時若遇 HTTP 429 配額限制，系統會自動切換至備援模型繼續完成總結。

5\. \*\*健壯的頻道解析 (`add\_channel.py`)\*\*：結合 `yt-dlp` 與 HTML 雙層備援解析，徹底解決 YouTube 反爬阻擋與正則失效問題。



\---



\## 2. 目錄結構與檔案清單



專案根目錄：`E:\\antigravity\\YTube-Notion\\`



| 檔案名稱 | 類型 | 功能說明 |

| :--- | :--- | :--- |

| `.env` | 設定檔 | 集中存放系統金鑰、Gemini 備援模型清單與 Markdown 提示詞範本庫。 |

| `channels.json` | 資料清單 | 追蹤頻道清單，含名稱、Handle、Channel ID、首頁與 RSS 網址。 |

| `main.py` | 核心腳本 | 一鍵全自動巡邏頻道、比對 2 天內新片、Gemini 總結並寫入 Notion。 |

| `add\_channel.py` | 輔助工具 | 互動式新增追蹤頻道，自動解析 Handle 與 Channel ID 並寫入清單。 |

| `一鍵巡邏與AI總結.bat` | 批次啟動檔 | Windows 桌面捷徑，一鍵執行 `main.py`，完成後等待 3 秒自動關閉。 |

| `新增YT頻道.bat` | 批次啟動檔 | Windows 桌面捷徑，啟動新增頻道互動介面，結束後等待 3 秒自動關閉。 |



\---



\## 3. 環境建置與部屬步驟



\### 3.1 建立目錄與 Python 虛擬環境



在 Windows 命令提示字元 (CMD) 中執行以下指令：



```cmd

cd /d "E:\\antigravity\\YTube-Notion"

python -m venv venv

venv\\Scripts\\activate



pip install --upgrade pip

pip install requests python-dotenv feedparser youtube-transcript-api yt-dlp google-genai

```



\### 3.2 Notion 資料庫欄位規格



Notion 資料庫需具備以下欄位名稱與屬性：

\- \*\*`Name`\*\* (Title)：影片標題

\- \*\*`URL`\*\* (URL)：YouTube 完整影片網址（用於比對是否重複收錄）

\- \*\*`Channel`\*\* (Select 或 Text)：來源頻道名稱

\- \*\*`Published`\*\* (Date)：影片實際上架日期

\- \*\*`Category`\*\* (Select)：由 AI 自動填入之題材分類

\- \*\*版面設定建議\*\*：可將檢視切換為 \*\*畫廊（Gallery）\*\*，並在「版面配置」設定 \*\*Card preview: Page cover\*\*。



\---



\## 4. 全套模組完整原始碼



\### 4.1 整合設定檔：`.env`



```env

\# ==========================================

\# 1. 系統 API 金鑰與 Notion 資料庫設定

\# ==========================================

GEMINI\_API\_KEY="AIzaSy...你的Gemini金鑰..."

NOTION\_API\_KEY="ntn\_...你的Notion內部整合Secret..."

NOTION\_DATABASE\_ID="...32位元資料庫ID..."



\# ==========================================

\# 2. 模型調用優先級清單 (以逗號分隔，遇 429 自動切換)

\# ==========================================

GEMINI\_MODELS="gemini-3.8-flash,gemini-2.5-flash,gemini-2.5-pro"



\# ==========================================

\# 3. 提示詞範本庫 (Markdown 格式多行字串)

\# ==========================================

AI\_PROMPT\_TEMPLATES="

\## 教學實作類

1\. 【教學亮點】：一句話點出本單元核心技能與應用場景。

2\. 【步驟拆解】：依操作順序條列具體步驟（標註時間點或操作流程）。

3\. 【關鍵參數與提示詞】：整理所有出現的設定值、指令代碼或 Prompt。

4\. 【實用避坑技巧】：提醒初學者最常犯的錯誤與排除方法。



\---



\## 新聞時事類

1\. 【焦點速覽】：100 字內摘要本次事件核心焦點。

2\. 【核心要點拆解】：條列關鍵事實，並標註各項事件帶來的潛在影響。

3\. 【各方立場與反應】：整理相關利害關係人的態度或回應。

4\. 【深度觀察結論】：分析事件背後趨勢與後續關注指標。



\---



\## 科技評測類

1\. 【結論先行】：以 3 句話總結這款產品的總體評價與市場定位。

2\. 【核心規格與特色亮點】：列出最具突破性的功能或規格指標。

3\. 【優缺點深度對比】：清晰條列「入手優勢」與「遺憾缺點」。

4\. 【選購與適合族群建議】：明確指出哪些使用者適合購買，哪些使用者應避開。



\---



\## 通用知識類

1\. 【核心概念】：用一句話闡述本影片最核心的底層邏輯。

2\. 【三大關鍵思維】：梳理影片中最具啟發性的 3 個觀點或模型。

3\. 【生活與工作應用】：列出觀眾可以立刻展開的具體行動步驟 (Actionable Items)。

"

```



\---



\### 4.2 頻道設定檔：`channels.json`



```json

\[

&#x20; {

&#x20;   "name": "茶米老師教室",

&#x20;   "handle": "@edreamerTW",

&#x20;   "id": "UCNkm31jX3472Ef5PGFroacQ",

&#x20;   "url": "\[https://www.youtube.com/@edreamerTW](https://www.youtube.com/@edreamerTW)",

&#x20;   "rss\_url": "\[https://www.youtube.com/feeds/videos.xml?channel\_id=UCNkm31jX3472Ef5PGFroacQ](https://www.youtube.com/feeds/videos.xml?channel\_id=UCNkm31jX3472Ef5PGFroacQ)"

&#x20; },

&#x20; {

&#x20;   "name": "文昭談古論今 -Wen Zhao Official",

&#x20;   "handle": "@wenzhaoofficial",

&#x20;   "id": "UCtAIPjABiQD3qjlEl1T5VpA",

&#x20;   "url": "\[https://www.youtube.com/@wenzhaoofficial](https://www.youtube.com/@wenzhaoofficial)",

&#x20;   "rss\_url": "\[https://www.youtube.com/feeds/videos.xml?channel\_id=UCtAIPjABiQD3qjlEl1T5VpA](https://www.youtube.com/feeds/videos.xml?channel\_id=UCtAIPjABiQD3qjlEl1T5VpA)"

&#x20; },

&#x20; {

&#x20;   "name": "PAPAYA 電腦教室",

&#x20;   "handle": "@papayacomputer",

&#x20;   "id": "UCdEpz2A4DzV\_\_4C1x2quKLw",

&#x20;   "url": "\[https://www.youtube.com/@papayacomputer](https://www.youtube.com/@papayacomputer)",

&#x20;   "rss\_url": "\[https://www.youtube.com/feeds/videos.xml?channel\_id=UCdEpz2A4DzV\_\_4C1x2quKLw](https://www.youtube.com/feeds/videos.xml?channel\_id=UCdEpz2A4DzV\_\_4C1x2quKLw)"

&#x20; }

]

```



\---



\### 4.3 核心執行腳本：`main.py`



```python

import os

import re

import json

import time

import random

import datetime

from typing import List, Dict, Optional

import requests

import feedparser

import yt\_dlp

from dotenv import load\_dotenv

from youtube\_transcript\_api import YouTubeTranscriptApi

from google import genai

from google.genai import types



load\_dotenv()



GEMINI\_API\_KEY = os.getenv("GEMINI\_API\_KEY") or os.getenv("GOOGLE\_API\_KEY")

NOTION\_API\_KEY = os.getenv("NOTION\_API\_KEY")

NOTION\_DATABASE\_ID = os.getenv("NOTION\_DATABASE\_ID")



if not GEMINI\_API\_KEY or not NOTION\_API\_KEY or not NOTION\_DATABASE\_ID:

&#x20;   raise ValueError("環境變數不足！請檢查 .env 檔案中的金鑰與 NOTION\_DATABASE\_ID！")



ai\_client = genai.Client(api\_key=GEMINI\_API\_KEY)



NOTION\_HEADERS = {

&#x20;   "Authorization": f"Bearer {NOTION\_API\_KEY}",

&#x20;   "Content-Type": "application/json",

&#x20;   "Notion-Version": "2022-06-28"

}



session = requests.Session()

session.cookies.set("SOCS", "CAESEwgDEgk0ODEzNzk5NDIaAnpoIAEaBgiA\_LyaBg", domain=".youtube.com")

session.cookies.set("CONSENT", "PENDING+999", domain=".youtube.com")

session.headers.update({

&#x20;   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

&#x20;   "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"

})



DB\_SCHEMA = None



def load\_model\_list() -> List\[str]:

&#x20;   models\_env = os.getenv("GEMINI\_MODELS", "")

&#x20;   if models\_env.strip():

&#x20;       models = \[m.strip() for m in models\_env.split(",") if m.strip()]

&#x20;       if models:

&#x20;           return models

&#x20;   return \["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"]



def parse\_markdown\_templates\_text(content: str) -> Dict\[str, str]:

&#x20;   templates = {}

&#x20;   sections = re.split(r'(?m)^##\\s+', content)

&#x20;   for sec in sections:

&#x20;       sec = sec.strip()

&#x20;       if not sec:

&#x20;           continue

&#x20;       lines = sec.split("\\n", 1)

&#x20;       cat\_name = lines\[0].strip()

&#x20;       body = lines\[1].strip() if len(lines) > 1 else ""

&#x20;       if cat\_name and body:

&#x20;           templates\[cat\_name] = body

&#x20;   return templates



def load\_prompt\_templates() -> Dict\[str, str]:

&#x20;   templates\_str = os.getenv("AI\_PROMPT\_TEMPLATES", "")

&#x20;   if templates\_str.strip():

&#x20;       try:

&#x20;           templates = parse\_markdown\_templates\_text(templates\_str)

&#x20;           if templates:

&#x20;               return templates

&#x20;       except Exception:

&#x20;           pass



&#x20;   return {

&#x20;       "教學實作類": "1. 【教學亮點】：一句話點出本單元核心技能與應用場景。\\n2. 【步驟拆解】：依操作順序條列具體步驟。\\n3. 【關鍵參數與提示詞】：整理設定值或 Prompt。\\n4. 【實用避坑技巧】：提醒常犯錯誤與排除方法。",

&#x20;       "新聞時事類": "1. 【焦點速覽】：100 字內摘要本次事件核心焦點。\\n2. 【核心要點拆解】：條列關鍵事實與潛在影響。\\n3. 【各方立場與反應】：整理相關利害關係人態度。\\n4. 【深度觀察結論】：分析事件背後趨勢與後續關注指標。",

&#x20;       "科技評測類": "1. 【結論先行】：以 3 句話總結總體評價與定位。\\n2. 【核心規格與特色亮點】：列出最具突破性指標。\\n3. 【優缺點深度對比】：清晰條列優勢與缺點。\\n4. 【選購與適合族群建議】：指出推薦與應避開族群。",

&#x20;       "通用知識類": "1. 【核心概念】：用一句話闡述底層邏輯。\\n2. 【三大關鍵思維】：梳理 3 個最具啟發性觀點。\\n3. 【生活與工作應用】：列出具體行動步驟。"

&#x20;   }



def get\_db\_schema() -> Dict:

&#x20;   global DB\_SCHEMA

&#x20;   if DB\_SCHEMA is not None:

&#x20;       return DB\_SCHEMA

&#x20;   url = f"\[https://api.notion.com/v1/databases/](https://api.notion.com/v1/databases/){NOTION\_DATABASE\_ID}"

&#x20;   resp = requests.get(url, headers=NOTION\_HEADERS)

&#x20;   if resp.status\_code == 200:

&#x20;       DB\_SCHEMA = resp.json().get("properties", {})

&#x20;       return DB\_SCHEMA

&#x20;   return {}



def check\_notion\_exists(video\_url: str) -> bool:

&#x20;   schema = get\_db\_schema()

&#x20;   url\_key = "URL"

&#x20;   for k, v in schema.items():

&#x20;       if v.get("type") == "url":

&#x20;           url\_key = k

&#x20;           break



&#x20;   query\_url = f"\[https://api.notion.com/v1/databases/](https://api.notion.com/v1/databases/){NOTION\_DATABASE\_ID}/query"

&#x20;   payload = {

&#x20;       "filter": {

&#x20;           "property": url\_key,

&#x20;           "url": {"equals": video\_url}

&#x20;       }

&#x20;   }

&#x20;   resp = requests.post(query\_url, headers=NOTION\_HEADERS, json=payload)

&#x20;   if resp.status\_code == 200:

&#x20;       return len(resp.json().get("results", \[])) > 0

&#x20;   return False



def split\_text\_blocks(text: str, max\_len: int = 1900) -> List\[Dict]:

&#x20;   chunks = \[text\[i:i+max\_len] for i in range(0, len(text), max\_len)]

&#x20;   blocks = \[]

&#x20;   for chunk in chunks:

&#x20;       blocks.append({

&#x20;           "object": "block",

&#x20;           "type": "paragraph",

&#x20;           "paragraph": {

&#x20;               "rich\_text": \[{"type": "text", "text": {"content": chunk}}]

&#x20;           }

&#x20;       })

&#x20;   return blocks



def create\_summary\_notion\_page(video\_id: str, title: str, url: str, channel\_name: str, pub\_date: str, category: str, summary: str):

&#x20;   schema = get\_db\_schema()

&#x20;   props = {}



&#x20;   for k, v in schema.items():

&#x20;       if v.get("type") == "title":

&#x20;           props\[k] = {"title": \[{"type": "text", "text": {"content": title}}]}

&#x20;           break



&#x20;   for k, v in schema.items():

&#x20;       if v.get("type") == "url":

&#x20;           props\[k] = {"url": url}

&#x20;           break



&#x20;   if "Channel" in schema:

&#x20;       t = schema\["Channel"].get("type")

&#x20;       if t == "select":

&#x20;           props\["Channel"] = {"select": {"name": channel\_name\[:100]}}

&#x20;       elif t == "rich\_text":

&#x20;           props\["Channel"] = {"rich\_text": \[{"type": "text", "text": {"content": channel\_name\[:100]}}]}



&#x20;   if "Published" in schema:

&#x20;       t = schema\["Published"].get("type")

&#x20;       if t == "date":

&#x20;           props\["Published"] = {"date": {"start": pub\_date}}



&#x20;   for k in schema.keys():

&#x20;       if k in \["Category", "類別", "分類"]:

&#x20;           props\[k] = {"select": {"name": category}}

&#x20;           break



&#x20;   cover\_url = f"\[https://i.ytimg.com/vi/](https://i.ytimg.com/vi/){video\_id}/hqdefault.jpg"

&#x20;   endpoint = "\[https://api.notion.com/v1/pages](https://api.notion.com/v1/pages)"

&#x20;   body = {

&#x20;       "parent": {"database\_id": NOTION\_DATABASE\_ID},

&#x20;       "cover": {

&#x20;           "type": "external",

&#x20;           "external": {"url": cover\_url}

&#x20;       },

&#x20;       "properties": props,

&#x20;       "children": \[

&#x20;           {

&#x20;               "object": "block",

&#x20;               "type": "heading\_1",

&#x20;               "heading\_1": {

&#x20;                   "rich\_text": \[{"type": "text", "text": {"content": f"✨ AI 智慧總結（{category}）"}}],

&#x20;                   "color": "blue\_background"

&#x20;               }

&#x20;           }

&#x20;       ] + split\_text\_blocks(summary)

&#x20;   }



&#x20;   resp = requests.post(endpoint, headers=NOTION\_HEADERS, json=body)

&#x20;   if resp.status\_code == 200:

&#x20;       print(f"    └─ 成功收錄至 Notion，並完成【{category}】結構化總結！")

&#x20;   else:

&#x20;       print(f"    └─ Notion 寫入失敗: {resp.status\_code} - {resp.text}")



def parse\_iso\_datetime(dt\_str: str) -> Optional\[datetime.datetime]:

&#x20;   if not dt\_str:

&#x20;       return None

&#x20;   try:

&#x20;       clean\_str = dt\_str.replace("Z", "+00:00")

&#x20;       dt = datetime.datetime.fromisoformat(clean\_str)

&#x20;       if dt.tzinfo is None:

&#x20;           dt = dt.replace(tzinfo=datetime.timezone.utc)

&#x20;       return dt.astimezone(datetime.timezone.utc)

&#x20;   except Exception:

&#x20;       pass

&#x20;   try:

&#x20;       date\_part = dt\_str.split("T")\[0].split(" ")\[0]

&#x20;       dt = datetime.datetime.strptime(date\_part, "%Y-%m-%d")

&#x20;       return dt.replace(tzinfo=datetime.timezone.utc)

&#x20;   except Exception:

&#x20;       pass

&#x20;   return None



def get\_video\_real\_upload\_date(video\_id: str) -> datetime.datetime:

&#x20;   url = f"\[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=){video\_id}"

&#x20;   try:

&#x20;       resp = session.get(url, timeout=6)

&#x20;       if resp.status\_code == 200:

&#x20;           patterns = \[

&#x20;               r'itemprop="datePublished"\\s+content="(\[^"]+)"',

&#x20;               r'itemprop="uploadDate"\\s+content="(\[^"]+)"',

&#x20;               r'"publishDate":"(\[^"]+)"',

&#x20;               r'"uploadDate":"(\[^"]+)"'

&#x20;           ]

&#x20;           for pat in patterns:

&#x20;               m = re.search(pat, resp.text)

&#x20;               if m:

&#x20;                   parsed = parse\_iso\_datetime(m.group(1))

&#x20;                   if parsed:

&#x20;                       return parsed

&#x20;   except Exception:

&#x20;       pass



&#x20;   try:

&#x20;       with yt\_dlp.YoutubeDL({'quiet': True, 'skip\_download': True, 'no\_warnings': True}) as ydl:

&#x20;           info = ydl.extract\_info(url, download=False)

&#x20;           if info:

&#x20;               ts = info.get("timestamp") or info.get("release\_timestamp")

&#x20;               if ts:

&#x20;                   return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)

&#x20;               up\_date = info.get("upload\_date")

&#x20;               if up\_date and len(up\_date) == 8:

&#x20;                   dt = datetime.datetime.strptime(up\_date, "%Y%m%d")

&#x20;                   return dt.replace(tzinfo=datetime.timezone.utc)

&#x20;   except Exception:

&#x20;       pass



&#x20;   return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)



def fetch\_videos\_via\_rss(channel\_id: str) -> List\[Dict]:

&#x20;   if not channel\_id:

&#x20;       return \[]

&#x20;   rss\_url = f"\[https://www.youtube.com/feeds/videos.xml?channel\_id=](https://www.youtube.com/feeds/videos.xml?channel\_id=){channel\_id}"

&#x20;   try:

&#x20;       feed = feedparser.parse(rss\_url)

&#x20;       if not feed.entries:

&#x20;           return \[]

&#x20;       videos = \[]

&#x20;       for entry in feed.entries\[:10]:

&#x20;           v\_id = entry.get("yt\_videoid")

&#x20;           if not v\_id:

&#x20;               link = entry.get("link", "")

&#x20;               m = re.search(r'v=(\[a-zA-Z0-9\_-]{11})', link)

&#x20;               v\_id = m.group(1) if m else None



&#x20;           if not v\_id:

&#x20;               continue



&#x20;           pub\_str = entry.get("published", "")

&#x20;           pub\_dt = parse\_iso\_datetime(pub\_str)

&#x20;           if not pub\_dt and hasattr(entry, "published\_parsed") and entry.published\_parsed:

&#x20;               pub\_dt = datetime.datetime(\*entry.published\_parsed\[:6], tzinfo=datetime.timezone.utc)



&#x20;           if not pub\_dt:

&#x20;               pub\_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)



&#x20;           videos.append({

&#x20;               "id": v\_id,

&#x20;               "title": entry.get("title", ""),

&#x20;               "url": f"\[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=){v\_id}",

&#x20;               "description": entry.get("summary", ""),

&#x20;               "published\_dt": pub\_dt,

&#x20;               "published\_str": pub\_dt.strftime("%Y-%m-%d")

&#x20;           })

&#x20;       return videos

&#x20;   except Exception:

&#x20;       return \[]



def extract\_channel\_videos\_via\_ytdlp(channel\_target: str) -> List\[Dict]:

&#x20;   target = channel\_target.strip()

&#x20;   if target.startswith("http"):

&#x20;       url = target

&#x20;   elif target.startswith("@"):

&#x20;       url = f"\[https://www.youtube.com/](https://www.youtube.com/){target}/videos"

&#x20;   elif target.startswith("UC") and len(target) == 24:

&#x20;       url = f"\[https://www.youtube.com/channel/](https://www.youtube.com/channel/){target}/videos"

&#x20;   else:

&#x20;       url = f"\[https://www.youtube.com/](https://www.youtube.com/)@{target}/videos"



&#x20;   ydl\_opts = {

&#x20;       'playlistend': 10,

&#x20;       'quiet': True,

&#x20;       'no\_warnings': True,

&#x20;       'ignoreerrors': True,

&#x20;       'skip\_download': True,

&#x20;       'extract\_flat': True,

&#x20;       'http\_headers': {

&#x20;           'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',

&#x20;           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

&#x20;       },

&#x20;       'extractor\_args': {'youtube': {'lang': \['zh-TW', 'zh-Hant']}}

&#x20;   }



&#x20;   raw\_videos = \[]

&#x20;   try:

&#x20;       with yt\_dlp.YoutubeDL(ydl\_opts) as ydl:

&#x20;           info = ydl.extract\_info(url, download=False)

&#x20;           if not info:

&#x20;               return \[]

&#x20;           for e in info.get('entries', \[]):

&#x20;               if not e:

&#x20;                   continue

&#x20;               v\_id = e.get('id')

&#x20;               title = e.get('title')

&#x20;               if not v\_id or not title:

&#x20;                   continue

&#x20;               raw\_videos.append({

&#x20;                   "id": v\_id,

&#x20;                   "title": title,

&#x20;                   "url": f"\[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=){v\_id}",

&#x20;                   "description": e.get('description', '') or ""

&#x20;               })

&#x20;   except Exception as e:

&#x20;       print(f"  └─ 擷取清單異常：{e}")

&#x20;       return \[]



&#x20;   final\_videos = \[]

&#x20;   for item in raw\_videos:

&#x20;       real\_dt = get\_video\_real\_upload\_date(item\["id"])

&#x20;       item\["published\_dt"] = real\_dt

&#x20;       item\["published\_str"] = real\_dt.strftime("%Y-%m-%d")

&#x20;       final\_videos.append(item)

&#x20;       time.sleep(0.1)



&#x20;   return final\_videos



def get\_channel\_videos(ch: Dict) -> List\[Dict]:

&#x20;   channel\_id = ch.get("id")

&#x20;   videos = \[]

&#x20;   if channel\_id and channel\_id.startswith("UC"):

&#x20;       videos = fetch\_videos\_via\_rss(channel\_id)

&#x20;   if not videos:

&#x20;       target = ch.get("handle") or ch.get("url") or ch.get("id")

&#x20;       videos = extract\_channel\_videos\_via\_ytdlp(target)

&#x20;   if not videos:

&#x20;       return \[]



&#x20;   videos.sort(key=lambda x: x\["published\_dt"], reverse=True)

&#x20;   now = datetime.datetime.now(datetime.timezone.utc)

&#x20;   

&#x20;   recent\_2\_days = \[

&#x20;       v for v in videos 

&#x20;       if -86400 <= (now - v\["published\_dt"]).total\_seconds() <= 172800

&#x20;   ]

&#x20;   return recent\_2\_days



def get\_transcript(video\_id: str) -> Optional\[str]:

&#x20;   try:

&#x20;       transcript\_list = YouTubeTranscriptApi().list(video\_id)

&#x20;       transcript = None

&#x20;       for code in \['zh-TW', 'zh-Hant', 'zh', 'zh-CN', 'en']:

&#x20;           try:

&#x20;               transcript = transcript\_list.find\_transcript(\[code])

&#x20;               break

&#x20;           except Exception:

&#x20;               continue



&#x20;       if not transcript:

&#x20;           try:

&#x20;               transcript = transcript\_list.find\_generated\_transcript(\['zh-TW', 'zh-Hant', 'zh', 'zh-CN', 'en'])

&#x20;           except Exception:

&#x20;               transcript = None



&#x20;       if transcript:

&#x20;           data = transcript.fetch()

&#x20;           lines = \[]

&#x20;           for seg in data:

&#x20;               text\_val = getattr(seg, 'text', None)

&#x20;               if text\_val is None and isinstance(seg, dict):

&#x20;                   text\_val = seg.get('text', '')

&#x20;               if text\_val:

&#x20;                   lines.append(str(text\_val))

&#x20;           return " ".join(lines)

&#x20;   except Exception:

&#x20;       pass

&#x20;   return None



def summarize\_content(title: str, text\_content: str, templates: Dict\[str, str], models: List\[str]) -> Dict\[str, str]:

&#x20;   template\_instructions = "\\n\\n".join(\[f"### 分類【{k}】之標準結構：\\n{v}" for k, v in templates.items()])



&#x20;   prompt = f"""你是一名專業知識轉化專家與教學設計顧問。請依據下方提供的影片資訊與逐字稿，以「臺灣繁體中文」產出結構化總結筆記。



【總結範本庫規則】：

請先判斷該影片最屬於哪一個分類（{ "、".join(templates.keys()) }），並嚴格套用該分類對應的結構規範進行撰寫：



{template\_instructions}



\---

【影片標題】：{title}

【影片內容片段】：

{text\_content\[:7500]}



\---

【輸出格式嚴格規範】：

第一行：分類：\[你所判斷的分類名稱]（例如：分類：教學實作類）

第二行起：嚴格依據該分類之標準結構輸出條列筆記，標題與小節請加粗（例如 \*\*【教學亮點】\*\* 或 \*\*【核心概念】\*\*）。"""



&#x20;   for model\_name in models:

&#x20;       try:

&#x20;           print(f"    ↳ 調用模型：{model\_name} 產出筆記中...")

&#x20;           config = types.GenerateContentConfig(temperature=0.3)

&#x20;           response = ai\_client.models.generate\_content(

&#x20;               model=model\_name,

&#x20;               contents=prompt,

&#x20;               config=config

&#x20;           )

&#x20;           raw = response.text.strip()

&#x20;           category = list(templates.keys())\[0] if templates else "通用知識類"

&#x20;           summary = raw

&#x20;           first\_line = raw.split("\\n", 1)\[0]

&#x20;           for cat in templates.keys():

&#x20;               if cat in first\_line:

&#x20;                   category = cat

&#x20;                   if len(raw.split("\\n", 1)) > 1:

&#x20;                       summary = raw.split("\\n", 1)\[1].strip()

&#x20;                   break

&#x20;           return {"category": category, "summary": summary}

&#x20;       except Exception as e:

&#x20;           err\_msg = str(e)

&#x20;           if "429" in err\_msg or "RESOURCE\_EXHAUSTED" in err\_msg:

&#x20;               print(f"    ⚠️ \[{model\_name}] 配額限制 (429)，自動降級切換至下一個模型...")

&#x20;               time.sleep(1.5)

&#x20;               continue

&#x20;           else:

&#x20;               print(f"    ⚠️ \[{model\_name}] 異常：{e}")

&#x20;               time.sleep(1.0)

&#x20;               continue



&#x20;   raise RuntimeError("所有設定的備用模型皆已嘗試完畢，配額耗盡。")



def main():

&#x20;   print("=" \* 65)

&#x20;   print("  YouTube 智慧資訊匯流 - 一鍵全自動巡邏與 AI 總結")

&#x20;   print("=" \* 65)



&#x20;   if not os.path.exists("channels.json"):

&#x20;       print("❌ 找不到 channels.json 設定檔！")

&#x20;       return



&#x20;   with open("channels.json", "r", encoding="utf-8") as f:

&#x20;       channels = json.load(f)



&#x20;   templates = load\_prompt\_templates()

&#x20;   models = load\_model\_list()



&#x20;   total\_added = 0



&#x20;   for ch in channels:

&#x20;       name = ch\["name"]

&#x20;       print(f"\\n📡 正在巡邏頻道：{name} ...")

&#x20;       time.sleep(random.uniform(0.8, 1.2))



&#x20;       target\_videos = get\_channel\_videos(ch)



&#x20;       if not target\_videos:

&#x20;           print("  💤 最近 2 天內無新影片，略過。")

&#x20;           continue



&#x20;       for v in target\_videos:

&#x20;           if check\_notion\_exists(v\["url"]):

&#x20;               print(f"  ⏭️ \[已存在略過]：{v\['title']}")

&#x20;               continue



&#x20;           print(f"\\n  🎯 \[發現新影片]：{v\['title']} ({v\['published\_str']})")

&#x20;           

&#x20;           transcript\_text = get\_transcript(v\["id"])

&#x20;           if transcript\_text:

&#x20;               raw\_content = f"【字幕內容】\\n{transcript\_text}"

&#x20;           else:

&#x20;               raw\_content = f"【影片簡介】\\n{v\['description']}"



&#x20;           if len(raw\_content.strip()) < 30:

&#x20;               raw\_content = f"標題：{v\['title']}（無字幕且簡介過短）"



&#x20;           try:

&#x20;               res = summarize\_content(v\["title"], raw\_content, templates, models)

&#x20;               create\_summary\_notion\_page(

&#x20;                   v\["id"], 

&#x20;                   v\["title"], 

&#x20;                   v\["url"], 

&#x20;                   name, 

&#x20;                   v\["published\_str"], 

&#x20;                   res\["category"], 

&#x20;                   res\["summary"]

&#x20;               )

&#x20;               total\_added += 1

&#x20;               time.sleep(2.0)

&#x20;           except Exception as e:

&#x20;               print(f"    ❌ 處理該影片時發生錯誤：{e}")



&#x20;   print("\\n" + "=" \* 65)

&#x20;   print(f"🎉 任務完成！本次共發現並處理 {total\_added} 部新影片至 Notion。")

&#x20;   print("=" \* 65)



if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   main()

```



\---



\### 4.4 頻道管理工具：`add\_channel.py`



```python

import os

import re

import sys

import json

import requests

import yt\_dlp



CHANNELS\_FILE = "channels.json"



session = requests.Session()

session.cookies.set("SOCS", "CAESEwgDEgk0ODEzNzk5NDIaAnpoIAEaBgiA\_LyaBg", domain=".youtube.com")

session.cookies.set("CONSENT", "PENDING+999", domain=".youtube.com")

session.headers.update({

&#x20;   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

&#x20;   "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"

})



def resolve\_via\_ytdlp(target\_url: str) -> tuple\[str, str, str]:

&#x20;   """優先透過 yt-dlp 輕量擷取頻道核心資訊（最穩定的方案）"""

&#x20;   ydl\_opts = {

&#x20;       'extract\_flat': True,

&#x20;       'skip\_download': True,

&#x20;       'quiet': True,

&#x20;       'no\_warnings': True,

&#x20;       'playlistend': 1

&#x20;   }

&#x20;   try:

&#x20;       with yt\_dlp.YoutubeDL(ydl\_opts) as ydl:

&#x20;           info = ydl.extract\_info(target\_url, download=False)

&#x20;           if info:

&#x20;               channel\_id = info.get("channel\_id") or info.get("id") or ""

&#x20;               if not (channel\_id.startswith("UC") and len(channel\_id) == 24):

&#x20;                   channel\_id = info.get("channel\_id", "")

&#x20;               

&#x20;               channel\_name = info.get("channel") or info.get("uploader") or ""

&#x20;               

&#x20;               handle = ""

&#x20;               channel\_url = info.get("channel\_url") or target\_url

&#x20;               m\_h = re.search(r'@(\[a-zA-Z0-9\_\\-\\.]+)', channel\_url)

&#x20;               if m\_h:

&#x20;                   handle = f"@{m\_h.group(1)}"

&#x20;               

&#x20;               return handle, channel\_id, channel\_name

&#x20;   except Exception:

&#x20;       pass

&#x20;   return "", "", ""



def resolve\_youtube\_metadata(user\_input: str) -> tuple\[str, str, str]:

&#x20;   raw = user\_input.strip()

&#x20;   handle = ""

&#x20;   channel\_id = ""

&#x20;   channel\_name = ""



&#x20;   if raw.startswith("UC") and len(raw) == 24:

&#x20;       channel\_id = raw

&#x20;       url = f"\[https://www.youtube.com/channel/](https://www.youtube.com/channel/){channel\_id}"

&#x20;   elif "\[youtube.com/](https://youtube.com/)" in raw:

&#x20;       url = raw

&#x20;       m\_h = re.search(r'youtube\\.com/@(\[a-zA-Z0-9\_\\-\\.]+)', raw)

&#x20;       m\_id = re.search(r'youtube\\.com/channel/(UC\[a-zA-Z0-9\_\\-]{22})', raw)

&#x20;       if m\_h:

&#x20;           handle = f"@{m\_h.group(1)}"

&#x20;       if m\_id:

&#x20;           channel\_id = m\_id.group(1)

&#x20;   else:

&#x20;       handle = raw if raw.startswith("@") else f"@{raw}"

&#x20;       url = f"\[https://www.youtube.com/](https://www.youtube.com/){handle}"



&#x20;   print(f"📡 正在驗證與解析 YouTube 頻道資訊：{url} ...")



&#x20;   y\_handle, y\_id, y\_name = resolve\_via\_ytdlp(url)

&#x20;   if y\_id and y\_id.startswith("UC"):

&#x20;       handle = y\_handle or handle

&#x20;       channel\_id = y\_id

&#x20;       channel\_name = y\_name

&#x20;       return handle, channel\_id, channel\_name



&#x20;   try:

&#x20;       resp = session.get(url, timeout=10)

&#x20;       if resp.status\_code == 200:

&#x20;           html = resp.text



&#x20;           if not channel\_id:

&#x20;               patterns\_id = \[

&#x20;                   r'itemprop="channelId"\\s+content="(UC\[a-zA-Z0-9\_\\-]{22})"',

&#x20;                   r'"channelId":"(UC\[a-zA-Z0-9\_\\-]{22})"',

&#x20;                   r'channel\_id=(UC\[a-zA-Z0-9\_\\-]{22})',

&#x20;                   r'https://www\\.youtube\\.com/channel/(UC\[a-zA-Z0-9\_\\-]{22})'

&#x20;               ]

&#x20;               for pat in patterns\_id:

&#x20;                   m = re.search(pat, html)

&#x20;                   if m:

&#x20;                       channel\_id = m.group(1)

&#x20;                       break



&#x20;           if not handle:

&#x20;               patterns\_h = \[

&#x20;                   r'"canonicalChannelUrl":"https://www\\.youtube\\.com/@(\[a-zA-Z0-9\_\\-\\.]+)"',

&#x20;                   r'link rel="canonical"\\s+href="https://www\\.youtube\\.com/@(\[a-zA-Z0-9\_\\-\\.]+)"'

&#x20;               ]

&#x20;               for pat in patterns\_h:

&#x20;                   m = re.search(pat, html)

&#x20;                   if m:

&#x20;                       handle = f"@{m.group(1)}"

&#x20;                       break



&#x20;           if not channel\_name:

&#x20;               m\_title = re.search(r'<title>(.\*?) - YouTube</title>', html)

&#x20;               if m\_title:

&#x20;                   channel\_name = m\_title.group(1).strip()

&#x20;               else:

&#x20;                   m\_meta\_title = re.search(r'<meta property="og:title"\\s+content="(\[^"]+)"', html)

&#x20;                   if m\_meta\_title:

&#x20;                       channel\_name = m\_meta\_title.group(1).strip()

&#x20;   except Exception as e:

&#x20;       print(f"  ⚠️ HTML 請求解析發生錯誤：{e}")



&#x20;   return handle, channel\_id, channel\_name



def add\_channel(name\_input: str, url\_or\_handle: str):

&#x20;   handle, channel\_id, auto\_name = resolve\_youtube\_metadata(url\_or\_handle)



&#x20;   if not channel\_id:

&#x20;       print("\\n❌ 錯誤：無法解析該頻道的 Channel ID！")

&#x20;       print("💡 建議：請嘗試提供頻道首頁的完整網址，例如：\[https://www.youtube.com/@ChannelName](https://www.youtube.com/@ChannelName)")

&#x20;       return



&#x20;   final\_name = name\_input.strip() if name\_input.strip() else auto\_name

&#x20;   if not final\_name:

&#x20;       final\_name = handle or channel\_id or "未命名頻道"



&#x20;   channels = \[]

&#x20;   if os.path.exists(CHANNELS\_FILE):

&#x20;       try:

&#x20;           with open(CHANNELS\_FILE, "r", encoding="utf-8") as f:

&#x20;               channels = json.load(f)

&#x20;       except Exception:

&#x20;           channels = \[]



&#x20;   for ch in channels:

&#x20;       if ch.get("id") == channel\_id or (handle and ch.get("handle") == handle):

&#x20;           print(f"\\n⚠️ 該頻道已經在清單中：【{ch.get('name')}】(ID: {ch.get('id')})，略過新增。")

&#x20;           return



&#x20;   channel\_url = f"\[https://www.youtube.com/](https://www.youtube.com/){handle}" if handle else f"\[https://www.youtube.com/channel/](https://www.youtube.com/channel/){channel\_id}"

&#x20;   rss\_url = f"\[https://www.youtube.com/feeds/videos.xml?channel\_id=](https://www.youtube.com/feeds/videos.xml?channel\_id=){channel\_id}"



&#x20;   new\_item = {

&#x20;       "name": final\_name,

&#x20;       "handle": handle,

&#x20;       "id": channel\_id,

&#x20;       "url": channel\_url,

&#x20;       "rss\_url": rss\_url

&#x20;   }



&#x20;   channels.append(new\_item)

&#x20;   with open(CHANNELS\_FILE, "w", encoding="utf-8") as f:

&#x20;       json.dump(channels, f, ensure\_ascii=False, indent=2)



&#x20;   print("\\n" + "=" \* 50)

&#x20;   print("✅ 成功新增追蹤頻道至 channels.json！")

&#x20;   print(f"  📌 頻道名稱：{final\_name}")

&#x20;   print(f"  📌 原生 Handle：{handle or '無'}")

&#x20;   print(f"  📌 Channel ID：{channel\_id}")

&#x20;   print(f"  📌 官方 RSS  ：{rss\_url}")

&#x20;   print("=" \* 50)



def main():

&#x20;   print("=" \* 55)

&#x20;   print("       YouTube 智慧資訊匯流 - 新增追蹤頻道")

&#x20;   print("=" \* 55)



&#x20;   if len(sys.argv) >= 3:

&#x20;       name\_input = sys.argv\[1]

&#x20;       url\_input = sys.argv\[2]

&#x20;   else:

&#x20;       url\_input = input("請輸入頻道網址、@Handle 或 頻道ID：\\n> ").strip()

&#x20;       if not url\_input:

&#x20;           print("未輸入網址，取消操作。")

&#x20;           return

&#x20;       name\_input = input("請輸入顯示名稱（直接按 Enter 自動偵測）：\\n> ").strip()



&#x20;   add\_channel(name\_input, url\_input)



if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   main()

```



\---



\### 4.5 Windows 批次啟動檔集合



\#### 1. `一鍵巡邏與AI總結.bat`

```bat

@echo off

chcp 65001 >nul

title YouTube 一鍵巡邏與 AI 智慧總結

cd /d "%\~dp0"

if exist "venv\\Scripts\\activate.bat" (

&#x20;   call "venv\\Scripts\\activate.bat"

) else if exist ".venv\\Scripts\\activate.bat" (

&#x20;   call ".venv\\Scripts\\activate.bat"

)

python main.py

echo.

echo 任務已全部執行完畢，視窗將於 3 秒後自動關閉...

timeout /t 3 /nobreak >nul

```



\#### 2. `新增YT頻道.bat`

```bat

@echo off

chcp 65001 >nul

title 新增 YouTube 追蹤頻道

cd /d "%\~dp0"

if exist "venv\\Scripts\\activate.bat" (

&#x20;   call "venv\\Scripts\\activate.bat"

) else if exist ".venv\\Scripts\\activate.bat" (

&#x20;   call ".venv\\Scripts\\activate.bat"

)

python add\_channel.py

echo.

echo 執行結束，視窗將於 3 秒後自動關閉...

timeout /t 3 /nobreak >nul

```



\---



\## 5. 日常維運標準作業程序 (SOP)



1\. \*\*日常一鍵巡邏與筆記同步\*\*：

&#x20;  - 雙擊執行 `一鍵巡邏與AI總結.bat`。

&#x20;  - 系統自動依據 `channels.json` 比對新片 $\\to$ 調用 Gemini 產出筆記 $\\to$ 寫入 Notion，完成後 3 秒自動關閉視窗。

2\. \*\*新增追蹤創作者\*\*：

&#x20;  - 雙擊執行 `新增YT頻道.bat`。

&#x20;  - 貼上創作者的網址或 `@Handle`，名稱按 Enter 自動帶入並儲存至 `channels.json`。

3\. \*\*更換模型或擴充筆記架構\*\*：

&#x20;  - 直接開啟 `.env` 檔案：

&#x20;    - 修改 `GEMINI\_MODELS` 即可調整模型優先級。

&#x20;    - 在 `AI\_PROMPT\_TEMPLATES` 新增 `## 新類別` 與條列結構，AI 即會自動適配新的題材規範。

