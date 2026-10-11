import os
import re
import sys
import json
import requests
import yt_dlp

CHANNELS_FILE = "channels.json"

session = requests.Session()
session.cookies.set("SOCS", "CAESEwgDEgk0ODEzNzk5NDIaAnpoIAEaBgiA_LyaBg", domain=".youtube.com")
session.cookies.set("CONSENT", "PENDING+999", domain=".youtube.com")
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
})

def resolve_via_ytdlp(target_url: str) -> tuple[str, str, str]:
    """優先透過 yt-dlp 輕量擷取頻道核心資訊（最穩定的方案）"""
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 1
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if info:
                channel_id = info.get("channel_id") or info.get("id") or ""
                # 如果 id 不是 UC 開頭的 24 碼，檢查 channel_id
                if not (channel_id.startswith("UC") and len(channel_id) == 24):
                    channel_id = info.get("channel_id", "")
                
                channel_name = info.get("channel") or info.get("uploader") or ""
                
                # 抽取 handle
                handle = ""
                channel_url = info.get("channel_url") or target_url
                m_h = re.search(r'@([a-zA-Z0-9_\-\.]+)', channel_url)
                if m_h:
                    handle = f"@{m_h.group(1)}"
                
                return handle, channel_id, channel_name
    except Exception:
        pass
    return "", "", ""

def resolve_youtube_metadata(user_input: str) -> tuple[str, str, str]:
    raw = user_input.strip()
    handle = ""
    channel_id = ""
    channel_name = ""

    # 1. 規範化 URL 與初步抽取
    if raw.startswith("UC") and len(raw) == 24:
        channel_id = raw
        url = f"https://www.youtube.com/channel/{channel_id}"
    elif "youtube.com/" in raw:
        url = raw
        m_h = re.search(r'youtube\.com/@([a-zA-Z0-9_\-\.]+)', raw)
        m_id = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_\-]{22})', raw)
        if m_h:
            handle = f"@{m_h.group(1)}"
        if m_id:
            channel_id = m_id.group(1)
    else:
        # 輸入純名稱或純 handle
        handle = raw if raw.startswith("@") else f"@{raw}"
        url = f"https://www.youtube.com/{handle}"

    print(f"📡 正在驗證與解析 YouTube 頻道資訊：{url} ...")

    # 2. 第一優先保險：使用 yt-dlp 抽取
    y_handle, y_id, y_name = resolve_via_ytdlp(url)
    if y_id and y_id.startswith("UC"):
        handle = y_handle or handle
        channel_id = y_id
        channel_name = y_name
        return handle, channel_id, channel_name

    # 3. 第二備援保險：透過 requests 抓取 HTML 正則比對
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            html = resp.text

            # 搜尋 Channel ID (支援多種常見欄位)
            if not channel_id:
                patterns_id = [
                    r'itemprop="channelId"\s+content="(UC[a-zA-Z0-9_\-]{22})"',
                    r'"channelId":"(UC[a-zA-Z0-9_\-]{22})"',
                    r'channel_id=(UC[a-zA-Z0-9_\-]{22})',
                    r'https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_\-]{22})'
                ]
                for pat in patterns_id:
                    m = re.search(pat, html)
                    if m:
                        channel_id = m.group(1)
                        break

            # 搜尋 Handle
            if not handle:
                patterns_h = [
                    r'"canonicalChannelUrl":"https://www\.youtube\.com/@([a-zA-Z0-9_\-\.]+)"',
                    r'link rel="canonical"\s+href="https://www\.youtube\.com/@([a-zA-Z0-9_\-\.]+)"'
                ]
                for pat in patterns_h:
                    m = re.search(pat, html)
                    if m:
                        handle = f"@{m.group(1)}"
                        break

            # 搜尋頻道名稱
            if not channel_name:
                m_title = re.search(r'<title>(.*?) - YouTube</title>', html)
                if m_title:
                    channel_name = m_title.group(1).strip()
                else:
                    m_meta_title = re.search(r'<meta property="og:title"\s+content="([^"]+)"', html)
                    if m_meta_title:
                        channel_name = m_meta_title.group(1).strip()
    except Exception as e:
        print(f"  ⚠️ HTML 請求解析發生錯誤：{e}")

    return handle, channel_id, channel_name

def add_channel(name_input: str, url_or_handle: str):
    handle, channel_id, auto_name = resolve_youtube_metadata(url_or_handle)

    if not channel_id:
        print("\n❌ 錯誤：無法解析該頻道的 Channel ID！")
        print("💡 建議：請嘗試提供頻道首頁的完整網址，例如：https://www.youtube.com/@ChannelName")
        return

    final_name = name_input.strip() if name_input.strip() else auto_name
    if not final_name:
        final_name = handle or channel_id or "未命名頻道"

    channels = []
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                channels = json.load(f)
        except Exception:
            channels = []

    # 檢查是否重複
    for ch in channels:
        if ch.get("id") == channel_id or (handle and ch.get("handle") == handle):
            print(f"\n⚠️ 該頻道已經在清單中：【{ch.get('name')}】(ID: {ch.get('id')})，略過新增。")
            return

    channel_url = f"https://www.youtube.com/{handle}" if handle else f"https://www.youtube.com/channel/{channel_id}"
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    new_item = {
        "name": final_name,
        "handle": handle,
        "id": channel_id,
        "url": channel_url,
        "rss_url": rss_url
    }

    channels.append(new_item)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("✅ 成功新增追蹤頻道至 channels.json！")
    print(f"  📌 頻道名稱：{final_name}")
    print(f"  📌 原生 Handle：{handle or '無'}")
    print(f"  📌 Channel ID：{channel_id}")
    print(f"  📌 官方 RSS  ：{rss_url}")
    print("=" * 50)

def main():
    print("=" * 55)
    print("       YouTube 智慧資訊匯流 - 新增追蹤頻道")
    print("=" * 55)

    if len(sys.argv) >= 3:
        name_input = sys.argv[1]
        url_input = sys.argv[2]
    else:
        url_input = input("請輸入頻道網址、@Handle 或 頻道ID：\n> ").strip()
        if not url_input:
            print("未輸入網址，取消操作。")
            return
        name_input = input("請輸入顯示名稱（直接按 Enter 自動偵測）：\n> ").strip()

    add_channel(name_input, url_input)

if __name__ == "__main__":
    main()