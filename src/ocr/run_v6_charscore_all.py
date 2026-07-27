from paddleocr import PaddleOCR
import json, os, time

ocr = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False,
                use_textline_orientation=False, lang='ch', enable_mkldnn=False)
out = {}
t0 = time.time()
for i in range(850):
    png = f'/data/pages/{i:03d}.png'
    if not os.path.exists(png): continue
    try:
        result = ocr.predict(png, return_word_box=True)
        r = result[0].json['res']
        lines = []
        for j, text in enumerate(r['rec_texts']):
            ls = float(r['rec_scores'][j])
            cs = [float(s) for s in r['rec_char_scores'][j]] if j < len(r.get('rec_char_scores',[])) else []
            poly = r['rec_polys'][j] if j < len(r.get('rec_polys',[])) else None
            lines.append([poly, text, ls, cs])
        out[str(i)] = lines
    except Exception as e:
        out[str(i)] = []
        print(f'  p{i+1} 失败: {e}')
    if (i+1) % 10 == 0 or i+1 == 850:
        print(f'  {i+1}/850 ({time.time()-t0:.0f}s)', flush=True)
json.dump(out, open('/data/data/wz3_v6_charscore.json','w'), ensure_ascii=False)
total = sum(len(v) for v in out.values())
low = sum(1 for v in out.values() for _,_,_,cs in v for s in cs if s<0.5)
print(f'完成: {len(out)}页 {total}行 低字(<0.5){low} -> wz3_v6_charscore.json')
