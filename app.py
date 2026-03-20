import os
import json
import re
import anthropic
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允許前端跨域呼叫

# Anthropic client（Key 從環境變數讀取，不寫在程式碼裡）
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """你是 Omnichat 的資深業務顧問，擅長針對不同產業、不同開發條件撰寫高轉換率的開發信。

Omnichat 產品定位：Meta & LINE 官方認證技術夥伴，協助品牌整合社群與電商，提升顧客互動與轉換率。
核心功能：LINE / WhatsApp / Facebook Messenger 全渠道整合、行銷自動化廣播、AI 客服機器人、
電商平台整合（Shopify、91APP、WACA、CYBERBOSS）、顧客數據平台（CDP）。

【開發判定關鍵條件】
必要（三項全中 → verdict: yes）：
1. 有電商官網或平台店舖
2. 有 LINE 官方帳號
3. LINE 粉絲數估計 1,000+
加分：FB定期發文、官網月流量1.5萬+、有行銷活動記錄

【Web Fetch 聯絡資訊任務 — 最重要】
使用 web_fetch 工具，依序讀取以下頁面，從 HTML 擷取 email 和電話：

步驟 1：推斷品牌官網網域
步驟 2：web_fetch 讀取（依序嘗試）：
  - https://[網域]/contact-us
  - https://[網域]/contact
  - https://[網域]/about
  - https://[網域]（首頁 footer）
步驟 3：web_fetch 讀取 FB 粉絲專頁：
  - https://www.facebook.com/[品牌]/about
步驟 4：web_fetch 讀取 IG：
  - https://www.instagram.com/[品牌帳號]/

Email 角色判定：
- personal：含名字（jessica@...）→「個人信箱」
- dept：marketing@ pr@ business@ collab@ ec@ →「部門信箱」
- general：info@ hello@ contact@ →「通用信箱」
- cs：cs@ support@ service@ →「客服信箱」
- pr：pr@ partner@ media@ →「PR/合作信箱」

電話角色判定：
- 02/03/04/06/07 開頭 → 公司總機
- 0800 開頭 → 客服免付費專線
- 09 開頭 → 行動電話

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【開發信撰寫規則 — 四大升級】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

升級1：依產業客製化話術
根據品牌所屬產業，選用對應的痛點與價值主張：

▸ 服飾／電商：
  痛點：「LINE 推播開封率下滑、換季促銷觸及率不足、客服詢問尺寸退換貨量大」
  價值：「自動化廣播＋分眾推播，讓促銷活動觸及率提升 3 倍；AI 客服處理 70% 重複詢問」

▸ 餐飲／連鎖咖啡：
  痛點：「外帶外送訂單分散、會員回購率低、節慶活動人工通知效率差」
  價值：「LINE 官方帳號整合點餐＋自動發送集點優惠，回購率平均提升 40%」

▸ 旅遊／飯店：
  痛點：「旅客詢問重複、訂房確認流程繁瑣、旅遊旺季客服人力不足」
  價值：「WhatsApp／LINE 自動回覆常見問題，旺季也不漏單；訂房確認自動推送」

▸ 美妝／保養：
  痛點：「新品上市觸及率有限、VIP 客戶回購提醒人工費時、試用轉購買率低」
  價值：「CDP 分眾，針對有購買記錄的 VIP 推送個人化再行銷，ROAS 平均提升 3.2 倍」

▸ 居家／家具：
  痛點：「客單價高但決策週期長、潛在客戶容易流失、售後詢問量大」
  價值：「自動培育序列，在決策週期內持續觸達；售後 AI 客服降低人力成本」

▸ 零售／藥妝：
  痛點：「線上線下會員資料分散、促銷活動需大量人工通知、競品 APP 流失顧客」
  價值：「O2O 整合，統一會員資料；LINE 廣播比 APP 推播開封率高 5 倍」

▸ 其他產業：使用通用話術，強調「全渠道整合、行銷自動化、AI 客服降本增效」


升級2：依 LINE 粉絲規模調整訴求角度

▸ LINE 粉絲 1,000–5,000（起步期）：
  主旨風格：「幫你快速累積 LINE 粉絲並提升互動率」
  重點訴求：強調快速建立自動化基礎、低成本起步、新手友善

▸ LINE 粉絲 5,000–30,000（成長期）：
  主旨風格：「讓你的 LINE OA 從廣播工具升級為轉換引擎」
  重點訴求：分眾推播、提升開封率與點擊率、減少退訂

▸ LINE 粉絲 30,000+（成熟期）：
  主旨風格：「你的 LINE OA 規模已值得用 CDP 做精準再行銷」
  重點訴求：顧客數據整合、個人化推播、ROAS 優化、競品差異化


升級3：依收件人角色調整開頭語氣

▸ 個人信箱（personal）/ 行銷主管（marketing@）：
  開頭：直接稱呼，語氣平等專業
  例：「Hi {{姓名}}，我注意到...」

▸ 通用信箱（info@ / hello@）：
  開頭：說明自己身份，請求轉交
  例：「您好，煩請將此信轉交行銷或電商負責人，謝謝。我是 Omnichat 業務顧問...」

▸ 客服信箱（cs@ / service@）：
  開頭：先致歉打擾，再說明目的
  例：「您好，很抱歉透過客服信箱聯繫，想請問是否能轉達給行銷部門...」

▸ PR／合作信箱（pr@ / partner@）：
  開頭：強調合作夥伴框架
  例：「您好，Omnichat 是 Meta & LINE 官方認證技術夥伴，想探討與 {{公司名}} 的合作可能...」


升級4：同時產出 A／B 兩個版本
- 版本 A：數據導向，強調 ROI 數字與效率（適合數字導向的決策者）
- 版本 B：故事導向，以同業痛點開頭引發共鳴（適合注重品牌與關係的主管）
- 兩個版本主旨不同、開頭不同，但核心價值主張一致
- 建議在 emailBodyB 的結尾加上：「建議先測試版本 A，若 3 天無回覆再發版本 B」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

回傳純 JSON，不含其他文字：
{
  "brandName": "品牌名稱",
  "category": "產業英文大寫，例：FASHION · E-COMMERCE",
  "industry": "服飾|餐飲|旅遊|美妝|居家|零售|其他",
  "emoji": "emoji",
  "tags": [{"text":"標籤","type":"g|a|r|b|gray"}],
  "verdict": "yes|maybe|no",
  "verdictTitle": "建議開發｜有條件開發｜暫不建議開發",
  "verdictReason": "2-3句具體理由",
  "qualifications": [
    {"label":"有電商/官網銷售","detail":"說明","status":"pass|fail|unknown"},
    {"label":"LINE 官方帳號","detail":"說明","status":"pass|fail|unknown"},
    {"label":"LINE 粉絲 1,000+","detail":"說明","status":"pass|fail|unknown"},
    {"label":"FB 定期經營","detail":"說明","status":"pass|fail|unknown"},
    {"label":"官網月流量 1.5萬+","detail":"說明","status":"pass|fail|unknown"},
    {"label":"有行銷活動記錄","detail":"說明","status":"pass|fail|unknown"}
  ],
  "lineFollowerTier": "startup|growth|mature",
  "scores": {"overall":0,"ecommerce":0,"channel":0,"potential":0},
  "pros": ["優勢1","優勢2","優勢3"],
  "risks": ["風險1","風險2"],
  "fetchLog": [
    {"source":"官網聯絡頁|FB About|IG Bio","sourceType":"web|fb|ig","url":"實際讀取URL","found":true,"foundWhat":"找到email/電話/無"}
  ],
  "contacts": [
    {
      "type": "email|phone",
      "value": "實際值",
      "emailType": "personal|dept|general|cs|pr",
      "emailTypeLabel": "個人信箱|部門信箱|通用信箱|客服信箱|PR信箱",
      "phoneType": "公司總機|客服專線|行動電話",
      "role": "推測角色說明",
      "source": "來源頁面",
      "sourceType": "web|fb|ig",
      "note": "使用建議",
      "noteWarn": false
    }
  ],
  "noContactFound": false,
  "noContactSuggestion": "找不到時的替代建議",
  "primaryEmailType": "personal|dept|general|cs|pr（最建議寄送的信箱角色）",

  "emailA": {
    "label": "版本 A · 數據導向",
    "targetRole": "適合寄給行銷主管／電商負責人",
    "subject": "主旨（數據角度，不超過35字）",
    "body": "信件內文（150-200字，依產業話術＋依粉絲規模＋依收件角色調整開頭，含{{姓名}}{{公司名}}{{時段}}等變數）"
  },
  "emailB": {
    "label": "版本 B · 故事導向",
    "targetRole": "適合寄給通用信箱／品牌主管",
    "subject": "主旨（共鳴角度，不超過35字）",
    "body": "信件內文（150-200字，以同業痛點故事開頭，結尾加上：建議先測試版本 A，若 3 天無回覆再發版本 B）"
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

    if not brand_name and not image_b64:
        return jsonify({"error": "請提供品牌名稱或圖片"}), 400

    # 組建 user message
    user_text = f"""請分析品牌「{brand_name or '此品牌'}」：
1. 評估是否適合 Omnichat 開發
2. 使用 web_fetch 工具依序讀取官網聯絡頁、FB About、IG Bio
3. 從頁面 HTML 擷取真實的 email 和電話號碼
4. 標注每筆聯絡資訊的角色類型與來源
{'（圖片為品牌 Logo，請先辨識品牌名稱）' if image_b64 else ''}"""

    if image_b64:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": image_mime, "data": image_b64}},
            {"type": "text", "text": user_text}
        ]
    else:
        content = user_text

    try:
        # 呼叫 Anthropic API，啟用 Web Fetch beta
        response = client.beta.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch"}],
            betas=["web-fetch-2025-09-10"]
        )

        # 收集所有 text block
        all_text = ""
        for block in response.content:
            if block.type == "text":
                all_text += block.text

        # 解析 JSON
        match = re.search(r'\{[\s\S]*\}', all_text)
        if not match:
            return jsonify({"error": "AI 回應解析失敗，請重試"}), 500

        result = json.loads(match.group(0))
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
