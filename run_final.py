#!/usr/bin/env python3
import json, time, asyncio, httpx
import markdown as md_lib
from weasyprint import HTML

TOK = open("/tmp/paddle_token").read().strip()
BASE = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
HEADERS = {"Authorization": f"Bearer {TOK}", "Client-Platform": "python-sdk"}

async def main():
    with open("/opt/test/优化前.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=120) as c:
        r = await c.post(BASE, data={"model": "PaddleOCR-VL-1.6"},
            files={"file": ("input.pdf", pdf_bytes, "application/pdf")})
        job_id = r.json()["data"]["jobId"]
        print(f"Job: {job_id}")
        
        for i in range(60):
            await asyncio.sleep(3)
            r = await c.get(f"{BASE}/{job_id}")
            s = r.json()["data"]["state"]
            if s == "done": break
        
        url = r.json()["data"]["resultUrl"]["jsonUrl"]
        r = await c.get(url)
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(r.text)
        print(f"DEBUG raw_decode keys: {list(data.keys())}")
        result = data["result"]
        
        blocks = []
        for lr in result["layoutParsingResults"]:
            for item in lr["prunedResult"]["parsing_res_list"]:
                content = item.get("block_content", "")
                label = item.get("block_label", "text")
                if label.startswith("title"):
                    blocks.append(f"## {content}")
                else:
                    blocks.append(content)
        
        md_text = "\n\n".join(blocks)
        print(f"Blocks: {len(blocks)}, Chars: {len(md_text)}")
        
        with open("/opt/test/paddleocr_markdown.json", "w", encoding="utf-8") as f:
            json.dump({"1": md_text}, f, ensure_ascii=False, indent=2)
        
        html = md_lib.markdown(md_text, extensions=["extra", "sane_lists"])
        css = "@page{size:A4;margin:2cm}body{font-family:'Noto Sans CJK SC',SimSun,serif;font-size:11pt;line-height:1.8;color:#222}h1{font-size:16pt;text-align:center}h2{font-size:14pt}p{text-indent:2em;text-align:justify}"
        full = f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><style>{css}</style></head><body>{html}</body></html>"
        HTML(string=full).write_pdf("/opt/test/最终版_v3.pdf")
        
        s = os.path.getsize("/opt/test/最终版_v3.pdf") / 1048576
        print(f"PDF: {s:.2f} MB")

asyncio.run(main())
