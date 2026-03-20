import os
import json
import re
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

SYSTEM_PROMPT = """你是 Omnichat 的資深業務顧問，擅長針對不同產業、不同開發條件撰寫高轉換率的開發信。

請根據使用者提供的品牌名稱或品牌資訊，分析品牌是否適合 Omnichat 開發，
並回傳純 JSON，不要輸出任何額外文字。

回傳格式：
{
  "brandName": "品牌名稱",
  "category": "產業英文大寫",
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
  "fetchLog": [],
  "contacts": [],
  "noContactFound": true,
  "noContactSuggestion": "可再人工查詢官網聯絡頁、Facebook About、Instagram Bio",
  "primaryEmailType": "general",
  "emailA": {
    "label": "版本 A · 數據導向",
    "targetRole": "適合寄給行銷主管／電商負責人",
    "subject": "主旨",
    "body": "信件內文"
  },
  "emailB": {
    "label": "版本 B · 故事導向",
    "targetRole": "適合寄給通用信箱／品牌主管",
    "subject": "主旨",
    "body": "信件內文"
  }
}
"""

@app.route("/", methods=["GET"])
def home():
return app.send_static_file("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Omnichat Brand Scout API 運行中"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY 未設定"}), 500

    data = request.json or {}
    brand_name = data.get("brandName", "")
    image_b64 = data.get("imageB64", "")
    image_mime = data.get("imageMime", "image/jpeg")

    if not brand_name and not image_b64:
        return jsonify({"error": "請提供品牌名稱或圖片"}), 400

    user_text = f"""請分析品牌「{brand_name or '此品牌'}」：
1. 評估是否適合 Omnichat 開發
2. 推測品牌產業、通路成熟度、LINE 經營可能性
3. 產出兩版開發信
4. 回傳純 JSON"""

    if image_b64:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_mime,
                    "data": image_b64
                }
            },
            {"type": "text", "text": user_text}
        ]
    else:
        content = user_text

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )

        all_text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                all_text += block.text

        match = re.search(r'\{[\s\S]*\}', all_text)
        if not match:
            return jsonify({
                "error": "AI 回應解析失敗",
                "raw": all_text
            }), 500

        result = json.loads(match.group(0))
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
