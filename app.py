import os
from flask import Flask, render_template, request, jsonify
import dashscope
from dashscope import Generation
import docx
import PyPDF2

app = Flask(__name__)

# --- 核心配置 ---
# 请注意保护 Key 安全
dashscope.api_key = "sk-56de1645973146d6a18633f434eea729"
ADMIN_PASSWORD = "666"
DB_PATH = "rules_storage"

if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)


# --- 工具函数 ---
def read_file_content(file):
    text = ""
    try:
        filename = file.filename
        if filename.endswith('.docx'):
            doc = docx.Document(file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        elif filename.endswith('.txt'):
            text = file.read().decode('utf-8')
    except Exception as e:
        print(f"解析失败: {e}")
    return text


def load_local_knowledge():
    all_rules = ""
    files = [f for f in os.listdir(DB_PATH) if f.endswith(".txt")]
    if not files: return ""
    for filename in files:
        with open(os.path.join(DB_PATH, filename), "r", encoding="utf-8") as f:
            all_rules += f"\n【依据库：{filename.replace('.txt', '')}】\n" + f.read()
    return all_rules


# --- 路由定义 ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/verify_admin', methods=['POST'])
def verify_admin():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 403


@app.route('/api/upload_rules', methods=['POST'])
def upload_rules():
    files = request.files.getlist('files')
    if not files:
        return jsonify({"message": "无文件上传"}), 400

    count = 0
    for f in files:
        content = read_file_content(f)
        if content:
            save_name = f"{os.path.splitext(f.filename)[0]}.txt"
            with open(os.path.join(DB_PATH, save_name), "w", encoding="utf-8") as s:
                s.write(content)
            count += 1
    return jsonify({"message": f"成功入库 {count} 个文件"})


@app.route('/api/list_rules', methods=['GET'])
def list_rules():
    files = [f.replace('.txt', '') for f in os.listdir(DB_PATH) if f.endswith(".txt")]
    return jsonify({"files": files})


@app.route('/api/delete_rule', methods=['POST'])
def delete_rule():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({"message": "文件名不能为空"}), 400

    file_path = os.path.join(DB_PATH, f"{filename}.txt")
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"成功删除 {filename}"})
    return jsonify({"message": "文件不存在"}), 404


@app.route('/api/audit', methods=['POST'])
def audit():
    text_content = request.form.get('text', '')
    file = request.files.get('file')

    target = text_content
    if file:
        target += read_file_content(file)

    if not target:
        return jsonify({"error": "内容为空"}), 400

    knowledge = load_local_knowledge()

    prompt = f"""
    你现在是一位国家机关政策合规性审查专家。请严格基于以下提供的【法律法规底座】，对【政策草案】进行全维度扫描。

    【法律法规底座】：
    {knowledge if knowledge else "暂无外部法规，请按国家通用《公平竞争审查条例》执行。"}

    【待审查政策草案】：
    {target}

    【审查任务清单】：
    1. 市场准入限制：是否存在排斥外地经营者、设置歧视性准入条件的情况？
    2. 经营行为规范：是否存在强制交易、影响生产经营成本或影响生产经营行为的条款？
    3. 智能预警：若不修改，可能面临哪些法律风险或行政复议风险？

    【输出要求】：
    请使用HTML格式输出（不要使用Markdown代码块标记），风险点加粗，建议分点列出。
    """

    try:
        res = Generation.call(model="qwen-plus", prompt=prompt)

        # --- 核心修复：清洗掉 Markdown 标记 ---
        raw_text = res.output.text
        # 1. 去掉 ```html 和 ```
        clean_text = raw_text.replace("```html", "").replace("```", "")
        # 2. 转换换行符 (以防万一模型没有完全输出HTML标签)
        clean_text = clean_text.replace('\n', '<br>')

        return jsonify({"result": clean_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat_ip', methods=['POST'])
def chat_ip():
    data = request.json
    query = data.get('query')
    try:
        res = Generation.call(model="qwen-plus", prompt=query)
        return jsonify({"result": res.output.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)