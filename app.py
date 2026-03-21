import os
import json
import re
import anthropic
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_client(user_key=""):
    key = user_key.strip() if user_key else os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("未提供 Anthropic API Key")
    return anthropic.Anthropic(api_key=key)

SYSTEM_PROMPT = """你是 Omnichat 的資深業務顧問，擅長針對不同產業撰寫高轉換率的開發信。

Omnichat 產品定位：Meta & LINE 官方認證技術夥伴，協助品牌整合社群與電商，提升顧客互動與轉換率。
核心功能：LINE/WhatsApp/Facebook Messenger 全渠道整合、行銷自動化廣播、AI 客服機器人、
電商平台整合（Shopify、91APP、WACA、CYBERBOSS）、顧客數據平台（CDP）。

【開發判定關鍵條件】
必要（三項全中 → verdict: yes）：
1. 有電商官網或平台店舖
2. 有 LINE 官方帳號
3. LINE 粉絲數估計 1,000+
加分：FB定期發文、官網月流量1.5萬+、有行銷活動記錄

【聯絡窗口搜尋任務 — 最重要】
使用 web_fetch 工具，主動搜尋以下來源找出行銷主管或老闆的聯絡方式：

步驟1：推斷品牌官網網域，web_fetch 讀取：
  - https://[網域]/contact-us
  - https://[網域]/contact
  - https://[網域]/about
  - https://[網域]（首頁 footer）
步驟2：web_fetch 讀取 FB 粉絲專頁：
  - https://www.facebook.com/[品牌]/about
步驟3：web_fetch 讀取 IG：
  - https://www.instagram.com/[品牌帳號]/
步驟4：web_fetch 搜尋 LinkedIn：
  - https://www.linkedin.com/company/[品牌]/people/
  尋找職稱含「行銷」「Marketing」「BD」「Business Development」「電商」「EC」「總監」「經理」「Director」「Manager」「founder」「CEO」「老闆」的人員

從頁面內容擷取：
- Email：xxx@xxx.xxx 格式
- 電話：台灣格式（02-xxxx、09xx-xxx-xxx、0800-xxx-xxx）
- 人名 + 職稱（LinkedIn 找到的行銷/老闆窗口）

Email 角色判定：
- personal：含名字 → 「個人信箱」★ 最優先
- dept：marketing@/ec@/pr@/business@ → 「部門信箱」
- general：info@/hello@/contact@ → 「通用信箱」
- cs：cs@/support@/service@ → 「客服信箱」
- pr：pr@/partner@/media@ → 「PR信箱」

電話角色判定：
- 02/03/04/06/07 → 公司總機
- 0800 → 免付費客服
- 09 → 行動電話（最有價值）

【開發信四大升級】

升級1：依產業話術
- 服飾/電商：LINE推播開封率下滑、換季促銷觸及不足、退換貨客服量大
- 餐飲/咖啡：外帶外送訂單分散、會員回購率低、節慶通知人工費時
- 旅遊/飯店：重複詢問多、訂房流程繁瑣、旺季客服人力不足
- 美妝/保養：新品觸及有限、VIP回購提醒費時、試用轉購買率低
- 居家/家具：決策週期長、潛在客戶流失、售後詢問量大
- 零售/藥妝：線上線下會員分散、促銷通知人工費時
- 其他：全渠道整合、行銷自動化、AI客服降本增效

升級2：依LINE粉絲規模
- startup(1k-5k)：強調快速建立自動化基礎、低成本起步
- growth(5k-30k)：強調分眾推播、提升開封率與點擊率
- mature(30k+)：強調CDP精準再行銷、ROAS優化

升級3：依收件角色調整開頭
- personal/marketing@：直接稱呼，平等專業語氣
- info@/hello@：「煩請轉交行銷或電商負責人」
- cs@/service@：先致歉打擾再說明目的
- pr@/partner@：強調合作夥伴框架

升級4：A/B兩版
- A版：數據導向，強調ROI數字
- B版：故事導向，同業痛點引發共鳴，結尾加「建議先發A版，3天無回覆再發B版」

回傳純JSON，不含其他文字：
{
  "brandName": "品牌名稱",
  "category": "產業英文大寫",
  "industry": "服飾|餐飲|旅遊|美妝|居家|零售|其他",
  "emoji": "emoji",
  "tags": [{"text":"","type":"g|a|r|b|gray"}],
  "verdict": "yes|maybe|no",
  "verdictTitle": "建議開發|有條件開發|暫不建議開發",
  "verdictReason": "2-3句具體理由",
  "qualifications": [
    {"label":"有電商/官網銷售","detail":"","status":"pass|fail|unknown"},
    {"label":"LINE 官方帳號","detail":"","status":"pass|fail|unknown"},
    {"label":"LINE 粉絲 1,000+","detail":"","status":"pass|fail|unknown"},
    {"label":"FB 定期經營","detail":"","status":"pass|fail|unknown"},
    {"label":"官網月流量 1.5萬+","detail":"","status":"pass|fail|unknown"},
    {"label":"有行銷活動記錄","detail":"","status":"pass|fail|unknown"}
  ],
  "lineFollowerTier": "startup|growth|mature",
  "scores": {"overall":0,"ecommerce":0,"channel":0,"potential":0},
  "pros": ["優勢"],
  "risks": ["風險"],
  "fetchLog": [
    {"source":"","sourceType":"web|fb|ig|linkedin","url":"","found":true,"foundWhat":""}
  ],
  "contacts": [
    {
      "type": "email|phone|person",
      "value": "email地址或電話號碼",
      "name": "真實姓名（若有）",
      "title": "職稱（若有）",
      "emailType": "personal|dept|general|cs|pr",
      "emailTypeLabel": "個人信箱|部門信箱|通用信箱|客服信箱|PR信箱",
      "phoneType": "公司總機|客服專線|行動電話",
      "role": "推測角色說明",
      "source": "來源頁面",
      "sourceType": "web|fb|ig|linkedin",
      "note": "使用建議",
      "noteWarn": false
    }
  ],
  "noContactFound": false,
  "noContactSuggestion": "找不到時的替代建議",
  "primaryEmailType": "personal|dept|general|cs|pr",
  "emailA": {
    "label": "版本A·數據導向",
    "targetRole": "適合對象",
    "subject": "主旨不超過35字",
    "body": "150-200字，含{{姓名}}{{公司名}}{{時段}}變數"
  },
  "emailB": {
    "label": "版本B·故事導向",
    "targetRole": "適合對象",
    "subject": "主旨不超過35字",
    "body": "150-200字，結尾加建議策略"
  }
}"""


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Omnichat Brand Scout API 運行中"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    brand_name = data.get("brandName", "")
    image_b64  = data.get("imageB64", "")
    image_mime = data.get("imageMime", "image/jpeg")
    user_key   = data.get("apiKey", "")

    if not brand_name and not image_b64:
        return jsonify({"error": "請提供品牌名稱或圖片"}), 400

    try:
        client = get_client(user_key)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    user_text = f"""請分析品牌「{brand_name or '此品牌'}」：
1. 評估是否適合 Omnichat 開發
2. 使用 web_fetch 依序搜尋官網/FB/IG/LinkedIn，找出行銷主管或老闆的 email 和電話
3. 若 LinkedIn 找到真實人名和職稱，一併記錄
4. 標注每筆聯絡資訊的角色類型與來源
{'（圖片為品牌 Logo，請先辨識品牌名稱）' if image_b64 else ''}"""

    content = [
        {"type": "image", "source": {"type": "base64", "media_type": image_mime, "data": image_b64}},
        {"type": "text", "text": user_text}
    ] if image_b64 else user_text

    try:
        response = client.beta.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch"}],
            betas=["web-fetch-2025-09-10"]
        )

        all_text = "".join(b.text for b in response.content if b.type == "text")
        match = re.search(r'\{[\s\S]*\}', all_text)
        if not match:
            return jsonify({"error": "AI 回應解析失敗，請重試"}), 500
        return jsonify(json.loads(match.group(0)))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
