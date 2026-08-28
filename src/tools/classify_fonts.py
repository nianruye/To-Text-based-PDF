#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字体自动分类: 抽样(坐标聚类) → 裁剪 → DeepSeek-Vision 分类 → 渲染字体建议。

用法:
  python3 src/tools/classify_fonts.py <扫描pdf> <lines.json> <coords.json> [--out dir] [--DPI 144]
产出: <out>/combo_<cat>.png + <out>/font_class.json
  font_class.json: {"body": "song", "title": "song", "footnote": "song", "suggest": "..."}
"""
import sys, os, json, base64, subprocess, tempfile, shutil, re
from PIL import Image, ImageDraw

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash-vision-exp"

PROMPT = (
    "这是扫描书中「{cat}」文字的 N 个裁剪样本（横向拼接，每段上方有红色标签）。"
    "请判断这些文字使用的中文字体类别，只回答一个词：song(宋体) / hei(黑体) / fangsong(仿宋) / kai(楷体) / 其他请写具体类别名。"
    "判断依据：横细竖粗+三角顿角=宋体；笔画等粗无衬线=黑体；字形清瘦棱角硬朗=仿宋；有毛笔笔意=楷体。"
)

def classify(api_key, img_path, cat, n):
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    import urllib.request
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT.format(cat=cat, n=n)},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "temperature": 0,
        "max_tokens": 300,   # 推理模型 reasoning 占用 token, 30 会被吃光致 content 空
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()

def main():
    src_pdf, lines_f, coords_f = sys.argv[1], sys.argv[2], sys.argv[3]
    out_dir = "/tmp/font_rows"
    DPI = 144
    for a in sys.argv[4:]:
        if a.startswith("--out"): out_dir = a.split("=")[1]
        if a.startswith("--DPI"): DPI = int(a.split("=")[1])
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # 从 Hermes .env 读(优先 Windows 实际路径, WSL ~ 是 /root)
        for env_path in (os.path.expanduser("~/AppData/Local/hermes/.env"),
                         "/mnt/c/Users/xyp/AppData/Local/hermes/.env",
                         os.path.expanduser("~/.hermes/.env")):
            if os.path.exists(env_path):
                for line in open(env_path, encoding="utf-8"):
                    line = line.strip().strip("\r")
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if api_key:
                break
    if not api_key:
        print("未找到 DEEPSEEK_API_KEY"); sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    # 1) 抽样(复用 sample_font_rows.py)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "sample_font_rows.py"),
                    src_pdf, lines_f, coords_f, f"--out={out_dir}", f"--DPI={DPI}"], check=True)
    manifest = json.load(open(f"{out_dir}/samples.json"))

    # 2) 每张抽样图单独分类(combo 拼图精度差: 图小+红标签干扰, 单张判断更准)
    by_cat = {}
    for path, info in manifest.items():
        by_cat.setdefault(info["cat"], []).append((path, info))

    # 3) 逐类逐图调视觉 API, 按类投票
    result = {}
    votes = {}
    for cat, items in by_cat.items():
        v = []
        for idx, (path, info) in enumerate(items):
            try:
                ans = classify(api_key, path, cat, len(items))
            except Exception as e:
                ans = f"ERR:{e}"
            a = ans.strip().lower()
            if "宋" in a or "song" in a or "ming" in a: norm = "song"
            elif "黑" in a or "hei" in a: norm = "hei"
            elif "仿" in a or "fang" in a: norm = "fangsong"
            elif "楷" in a or "kai" in a: norm = "kai"
            else: norm = a.split()[0] if a and not a.startswith("err") else "unknown"
            v.append(norm)
            print(f"  [{cat}/{idx}] p{info['page']} {info['text'][:14]}... → {norm}")
        from collections import Counter
        c = Counter(x for x in v if x != "unknown")
        votes[cat] = dict(c)
        result[cat] = c.most_common(1)[0][0] if c else "unknown"

    # 4) 渲染建议
    suggest = []
    for role in ("body", "title", "footnote"):
        f = result.get(role, "song")
        font = {"song": "Noto Serif CJK SC", "hei": "Noto Sans CJK SC",
                "fangsong": "FangSong(需安装)", "kai": "KaiTi(需安装)"}.get(f, f)
        suggest.append(f"{role}={f}→{font}")
    result["suggest"] = "; ".join(suggest)
    json.dump(result, open(f"{out_dir}/font_class.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n分类结果 → {out_dir}/font_class.json")
    print("建议:", result["suggest"])

if __name__ == "__main__":
    main()
