#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU 试跑评估:在 wz1 seg2 上对比 MinerU vs 现有 PaddleOCR-VL spotting OCR。
只读现有 OCR JSON(wz1p108_lines.json / wz1p108_coords.json),不改流水线。

六大维度:
  1. 段落结构(MinerU 真段落边界 vs 我们的合并块)
  2. 首行缩进信号可恢复性(行级 x0 双峰?——采用与否核心依据)
  3. 页眉/页脚/页码 去除(MinerU type 打标 vs 我们手工滤)
  4. 公式(LaTeX 块)
  5. 阅读顺序
  6. OCR 字符准确度(抽样对照源)
用法: python3 mineru_eval.py <mineru_out_dir>
"""
import sys, os, json, glob, statistics
from collections import Counter

def find(out_dir, suffix):
    hits = glob.glob(os.path.join(out_dir, '**', '*' + suffix), recursive=True)
    return hits[0] if hits else None

def load_json(p):
    if not p: return None
    with open(p, encoding='utf-8') as f: return json.load(f)

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else '/opt/test/mineru_seg2'
    cl = load_json(find(out_dir, '_content_list.json'))
    md_path = find(out_dir, '.md')
    mid = load_json(find(out_dir, '_middle.json'))
    our_lines = load_json('/opt/test/wz1p108_lines.json')
    our_coords = load_json('/opt/test/wz1p108_coords.json')

    print("="*70)
    print("MinerU vs 现有 PaddleOCR-VL spotting — seg2 (p108-128) 对比")
    print("="*70)

    # ---------- MinerU content_list 维度 ----------
    if cl:
        types = Counter(it.get('type','?') for it in cl)
        paras = [it for it in cl if it.get('type')=='text' and not it.get('text_level')]
        titles = [it for it in cl if it.get('type')=='text' and it.get('text_level')]
        eqs = [it for it in cl if it.get('type')=='equation']
        aux = {t:types.get(t,0) for t in ('header','footer','page_number','page_footnote','aside_text')}
        npages = len(set(it.get('page_idx',0) for it in cl))
        print(f"\n[MinerU content_list] {len(cl)} 块 / {npages} 页")
        print(f"  正文段落={len(paras)}  标题={len(titles)}  公式(equation)={len(eqs)}")
        print(f"  辅助块(已打标、不混正文): header={aux['header']} footer={aux['footer']} "
              f"page_number={aux['page_number']} page_footnote={aux['page_footnote']} aside={aux['aside_text']}")
    else:
        print("\n[!] 未找到 content_list.json"); paras=titles=eqs=[]

    # ---------- MinerU middle.json: 行级 bbox → 首行缩进信号 ----------
    print("\n--- 维度2(核心):首行缩进信号可恢复性 ---")
    if mid and isinstance(mid.get('pdf_info'), list):
        first_line_x0 = []   # 每段首行 x0
        all_line_x0 = []
        page_size = None
        for pi in mid['pdf_info']:
            page_size = pi.get('page_size', page_size)
            for pb in pi.get('para_blocks', []):
                lines = pb.get('lines', [])
                if not lines: continue
                x0 = lines[0].get('bbox', [None])[0]
                if x0 is not None:
                    first_line_x0.append(x0)
                for ln in lines:
                    lx = ln.get('bbox', [None])[0]
                    if lx is not None: all_line_x0.append(lx)
        if first_line_x0:
            # 判定坐标制:VLM model.json 是 [0,1],middle 可能像素或归一
            mx = max(first_line_x0)
            if mx <= 1.5:  # 归一化 → 换算到 0-1000 便于读
                first_line_x0 = [v*1000 for v in first_line_x0]
                all_line_x0 = [v*1000 for v in all_line_x0]
                coord = "归一化[0,1]→×1000"
            else:
                coord = f"像素(页宽{page_size[0] if page_size else '?'})"
            # 双峰判定:看首行 x0 是否分两簇(顶格 vs +缩进)
            med = statistics.median(first_line_x0)
            lo = [v for v in first_line_x0 if v <= med*1.3]   # 顶格簇
            hi = [v for v in first_line_x0 if v > med*1.3]    # 缩进簇
            flush_mode = statistics.median(lo) if lo else 0
            indented_med = statistics.median(hi) if hi else 0
            gap = indented_med - flush_mode
            print(f"  MinerU 段首行 x0: {len(first_line_x0)} 段 | 坐标制={coord}")
            print(f"    顶格簇中位 x0={flush_mode:.1f}  缩进簇中位 x0={indented_med:.1f}  间距={gap:.1f}")
            print(f"    顶格段={len(lo)}  缩进段(疑似首行缩进)={len(hi)}  "
                  f"→ {'✓ 有双峰,首行缩进信号可恢复' if gap>5 and len(hi)>0 else '✗ 单峰,无缩进信号'}")
        else:
            print("  [!] middle.json 无 para_blocks 行级 bbox")
    else:
        print("  [!] 未找到 middle.json 或无 pdf_info")

    # ---------- 现有 OCR 对照 ----------
    print("\n--- 现有 PaddleOCR-VL spotting OCR 对照 ---")
    if our_lines:
        body_blocks = 0
        minx = []
        for k, lines in our_lines.items():
            polys = our_coords.get(k, []) if our_coords else []
            for i, ln in enumerate(lines):
                if not ln: continue
                body_blocks += 1
                if i < len(polys) and polys[i]:
                    xs = [p[0] for p in polys[i]] if isinstance(polys[i], list) else []
                    if xs: minx.append(min(xs))
        if minx:
            med = statistics.median(minx)
            print(f"  现有 body 块数={body_blocks} (扫描书整段合并→块少)")
            print(f"  块 min-x 分布: 中位={med:.1f}  min={min(minx):.1f}  max={max(minx):.1f}")
            print(f"    → 单峰(min-x≈续行顶格边)= 第五轮缩进丢失根因")
        # 段落对比
        if cl:
            print(f"\n[段落结构对比] MinerU 段落={len(paras)}  vs  现有合并块={body_blocks}")
            print(f"  → {'MinerU 段落边界更细' if len(paras)>body_blocks*1.3 else '块数接近'}")

    # ---------- 公式样例 ----------
    print("\n--- 维度4:公式(MinerU LaTeX) ---")
    if eqs:
        for e in eqs[:3]:
            t = (e.get('text') or '').replace('\n',' ')[:80]
            print(f"  [{e.get('text_format','?')}] {t}")
        print(f"  共 {len(eqs)} 个公式块(对照:现有流水线靠 escape_body 兜底转 a/b)")

    # ---------- 阅读顺序 + 正文样例 ----------
    print("\n--- 维度5/6:阅读顺序 & 正文样例(MinerU) ---")
    if paras:
        for p in paras[:3]:
            txt = (p.get('text') or '').replace('\n',' ')[:70]
            print(f"  p{p.get('page_idx')}: {txt}")

    # ---------- Markdown 段落(\\n\\n 分段) ----------
    if md_path:
        with open(md_path, encoding='utf-8') as f: md = f.read()
        md_paras = [p for p in md.split('\n\n') if p.strip()]
        print(f"\n[Markdown] {md_path}")
        print(f"  \\n\\n 分段数={len(md_paras)}  字符数={len(md)}")

    print("\n" + "="*70)
    print("核心判定:看上面【维度2】MinerU 段首行 x0 是否双峰 + 【段落结构对比】")
    print("  若双峰存在 → MinerU middle.json 可恢复首行缩进,值得接成抽取前端")
    print("="*70)

if __name__ == '__main__':
    main()
