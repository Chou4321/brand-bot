import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic

app = Flask(__name__, static_folder=".")
CORS(app)

# API KEY
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

# 首頁
@app.route("/", methods=["GET"])
def home():
    return app.send_static_file("index.html")

# 模擬搜尋結果（輕量版核心）
def get_brand_summary(brand_name):
    # ⚡這裡不爬網站，直接做簡單摘要（可換API）
    summaries = [
        f"{brand_name} 是一個知名品牌，專注於產品與品牌形象。",
        f"{brand_name} 在市場上具有一定影響力，並強調用戶體驗與設計。",
        f"{brand_name} 常透過數位行銷與社群媒體建立品牌聲量。"
    ]
    return "\n".join(summaries)

# 分析 API
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        brand_name = data.get("brandName", "")

        if not brand_name:
            return jsonify({"error": "請輸入品牌名稱"}), 400

        if not api_key:
            return jsonify({"error": "API KEY 未設定"}), 500

        # ✅ 輕量資料來源（不爆記憶體）
        content = get_brand_summary(brand_name)

        # Claude 分析
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": f"""
請分析以下品牌資訊，並輸出：
1. 品牌定位
2. 目標客群
3. 行銷策略建議

品牌名稱：{brand_name}

資料：
{content}
"""
                }
            ]
        )

        result_text = response.content[0].text

        return jsonify({
            "brand": brand_name,
            "analysis": result_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 啟動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
