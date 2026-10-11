import os
import re
import time
from typing import List, Dict
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not GEMINI_API_KEY or not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("環境變數不足！請檢查 .env 檔案中的 GEMINI_API_KEY 與 NOTION 金鑰。")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def load_model_list() -> List[str]:
    """從 .env 中的 GEMINI_MODELS 讀取以逗號分隔的模型清單"""
    models_env = os.getenv("GEMINI_MODELS", "")
    if models_env.strip():
        models = [m.strip() for m in models_env.split(",") if m.strip()]
        if models:
            print(f"📄 成功自 .env 載入模型調用清單：{models}")
            return models

    default_models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    print(f"ℹ️ 未設定 GEMINI_MODELS，使用預設清單：{default_models}")
    return default_models

def parse_markdown_templates_text(content: str) -> Dict[str, str]:
    """解析 Markdown 字串格式的提示詞範本 (以 ## 標題為分類名稱)"""
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
    """從 .env 中的 AI_PROMPT_TEMPLATES 讀取範本"""
    templates_str = os.getenv("AI_PROMPT_TEMPLATES", "")
    if templates_str.strip():
        try:
            templates = parse_markdown_templates_text(templates_str)
            if templates:
                print(f"📄 成功自 .env 載入提示詞範本庫，共 {len(templates)} 種類別")
                return templates
        except Exception as e:
            print(f"⚠️ 解析 .env 中的 AI_PROMPT_TEMPLATES 失敗：{e}，將使用預設範本。")

    print("ℹ️ 使用系統內建預設提示詞範本。")
    return {
        "教學實作類": "1. 【教學亮點】：一句話點出本單元核心技能與應用場景。\n2. 【步驟拆解】：依操作順序條列具體步驟。\n3. 【關鍵參數與提示詞】：整理設定值或 Prompt。\n4. 【實用避坑技巧】：提醒常犯錯誤與排除方法。",
        "新聞時事類": "1. 【焦點速覽】：100 字內摘要本次事件核心焦點。\n2. 【核心要點拆解】：條列關鍵事實與潛在影響。\n3. 【各方立場與反應】：整理相關利害關係人態度。\n4. 【深度觀察結論】：分析事件背後趨勢與後續關注指標。",
        "科技評測類": "1. 【結論先行】：以 3 句話總結總體評價與定位。\n2. 【核心規格與特色亮點】：列出最具突破性指標。\n3. 【優缺點深度對比】：清晰條列優勢與缺點。\n4. 【選購與適合族群建議】：指出推薦與應避開族群。",
        "通用知識類": "1. 【核心概念】：用一句話闡述底層邏輯。\n2. 【三大關鍵思維】：梳理 3 個最具啟發性觀點。\n3. 【生活與工作應用】：列出具體行動步驟。"
    }

def get_db_schema() -> Dict:
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    resp = requests.get(url, headers=NOTION_HEADERS)
    return resp.json().get("properties", {}) if resp.status_code == 200 else {}

def get_page_blocks_and_content(page_id: str) -> tuple[List[str], str]:
    has_more = True
    start_cursor = None
    full_text = ""
    block_ids = []

    while has_more:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if start_cursor:
            url += f"&start_cursor={start_cursor}"
        resp = requests.get(url, headers=NOTION_HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        for b in data.get("results", []):
            b_id = b.get("id")
            if b_id:
                block_ids.append(b_id)
            b_type = b.get("type")
            rich_texts = b.get(b_type, {}).get("rich_text", [])
            for rt in rich_texts:
                full_text += rt.get("text", {}).get("content", "") + "\n"

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return block_ids, full_text

def get_pending_videos() -> List[Dict]:
    """檢索 Notion 中尚未有總結記錄的卡片（已總結者自動略過）"""
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "page_size": 50,
        "sorts": [{"timestamp": "created_time", "direction": "descending"}]
    }
    resp = requests.post(query_url, headers=NOTION_HEADERS, json=payload)
    if resp.status_code != 200:
        return []

    results = resp.json().get("results", [])
    pending = []

    for r in results:
        page_id = r["id"]
        title = "未命名影片"
        for prop_val in r.get("properties", {}).values():
            if prop_val.get("type") == "title":
                t_list = prop_val.get("title", [])
                if t_list:
                    title = t_list[0].get("text", {}).get("content", "未命名影片")
                break

        block_ids, content = get_page_blocks_and_content(page_id)
        
        # 核心判斷：內文若已包含「AI 智慧總結」，表示該卡片已處理過，直接略過
        if "AI 智慧總結" not in content:
            pending.append({
                "page_id": page_id,
                "title": title,
                "raw_content": content,
                "block_ids": block_ids
            })

    return pending

def summarize_with_templates(title: str, text_content: str, templates: Dict[str, str], models: List[str]) -> Dict[str, str]:
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
            print(f"    ↳ 嘗試調用模型：{model_name}...")
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
                print(f"    ⚠️ [{model_name}] 配額限制 (429)，自動降級切換至下一個備用模型...")
                time.sleep(1.5)
                continue
            else:
                print(f"    ⚠️ [{model_name}] 遭遇非配額錯誤：{e}")
                time.sleep(1.0)
                continue

    raise RuntimeError("所有設定的備用模型皆已嘗試完畢，配額耗盡或連線異常。")

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

def clear_existing_blocks(block_ids: List[str]):
    for b_id in block_ids:
        del_url = f"https://api.notion.com/v1/blocks/{b_id}"
        try:
            requests.delete(del_url, headers=NOTION_HEADERS)
        except Exception:
            pass

def update_notion_page_only_summary(page_id: str, old_block_ids: List[str], category: str, summary: str):
    if old_block_ids:
        clear_existing_blocks(old_block_ids)

    schema = get_db_schema()
    for k in schema.keys():
        if k in ["Category", "類別", "分類"]:
            update_prop_url = f"https://api.notion.com/v1/pages/{page_id}"
            requests.patch(update_prop_url, headers=NOTION_HEADERS, json={"properties": {k: {"select": {"name": category}}}})
            break

    append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    summary_blocks = [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"✨ AI 智慧總結（{category}）"}}],
                "color": "blue_background"
            }
        }
    ] + split_text_blocks(summary)

    resp = requests.patch(append_url, headers=NOTION_HEADERS, json={"children": summary_blocks})
    if resp.status_code == 200:
        print(f"    └─ 成功寫入！已套用【{category}】結構規範，並移除原始逐字稿。")
    else:
        print(f"    └─ 寫入總結失敗: {resp.status_code} - {resp.text}")

def process_item(item: Dict, templates: Dict[str, str], models: List[str]):
    print(f"\n▶ 正在處理：{item['title']}")
    content = item.get("raw_content", "")
    if len(content.strip()) < 30:
        content = item['title']

    print("  └─ 讀取提示詞範本規範並產出總結中...")
    try:
        res = summarize_with_templates(item["title"], content, templates, models)
        update_notion_page_only_summary(
            item["page_id"], 
            item.get("block_ids", []), 
            res["category"], 
            res["summary"]
        )
    except Exception as e:
        print(f"  └─ 總結過程發生錯誤：{e}")

def main():
    print("=" * 65)
    print("  YouTube 智慧資訊匯流 - [步驟 2] AI 全自動批次總結")
    print("=" * 65)

    templates = load_prompt_templates()
    models = load_model_list()
    print(f"已識別總結類別範本：{list(templates.keys())}")
    print("正在檢索 Notion 資料庫中「尚未總結」的影片卡片...")
    
    items = get_pending_videos()

    if not items:
        print("\n✅ 目前 Notion 中所有影片皆已總結完成（已全部略過）！")
        return

    print(f"\n發現 {len(items)} 部尚未總結的影片，直接啟動全量批次處理：")
    for idx, it in enumerate(items, 1):
        print(f"  [{idx:02d}] {it['title']}")

    print("\n" + "=" * 65)
    print("🚀 開始自動總結流程...")
    print("=" * 65)

    for idx, it in enumerate(items, 1):
        print(f"\n進度：({idx}/{len(items)})")
        process_item(it, templates, models)
        time.sleep(2)  # 保持適度請求間隔避免觸發速率限制

    print("\n" + "=" * 65)
    print(f"🎉 全部批次總結完成！共處理 {len(items)} 部影片。")
    print("=" * 65)

if __name__ == "__main__":
    main()