#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从目录页 OCR 提取标题级别规则。

用法:
  python3 src/tools/extract_toc_rules.py <lines.json> <coords.json> [--out rules.json] [--max-scan 40]
产出: rules.json
  {"levels": [{"pattern": "^[一二三四五六七八九十]+[、．.]", "level": "part", "count": N},
              {"pattern": "^\\d+[.、．]", "level": "section", "count": N}],
   "toc_pages": [12, 13]}
级别: part(章/一) > title(二级) > section(节/1.) > sub(三级)
"""
import sys, os, json, re

# 候选编号模式(按级别从高到低)
PATTERNS = [
    ("part",    re.compile(r'^[一二三四五六七八九十百]+[、．.]')),
    ("section", re.compile(r'^\d{1,2}[\.、．]')),
    ("sub",     re.compile(r'^[（(][一二三四五六七八九十]+[)）]')),
    ("title",   re.compile(r'^第[一二三四五六七八九十百]+[章节部篇]')),
]

def find_toc_pages(sl, max_scan=40):
    """找目录页: 页含'目录'字样, 或短行(≤14字)占比高且多数带编号"""
    toc = []
    for pk in sorted(sl.keys(), key=int)[:max_scan]:
        lines = [t.strip() for t in sl[pk] if t.strip()]
        if not lines: continue
        joined = "".join(lines)
        short = [t for t in lines if len(t) <= 14]
        numbered = [t for t in short if any(p[1].match(t) for p in PATTERNS)]
        if "目录" in joined[:100] and len(short) >= 10:
            toc.append(int(pk))
        elif len(short) >= 15 and len(numbered) >= 10:
            toc.append(int(pk))
    return toc

def main():
    lines_f, coords_f = sys.argv[1], sys.argv[2]
    out = "toc_rules.json"
    max_scan = 40
    for a in sys.argv[3:]:
        if a.startswith("--out"): out = a.split("=")[1]
        if a.startswith("--max-scan"): max_scan = int(a.split("=")[1])

    sl = json.load(open(lines_f))
    toc_pages = find_toc_pages(sl, max_scan)
    print(f"目录页: {toc_pages}")

    # 统计目录页里的编号格式出现次数
    counts = {name: 0 for name, _ in PATTERNS}
    for pk in toc_pages:
        for t in sl.get(str(pk), []):
            t = t.strip()
            if not t: continue
            for name, pat in PATTERNS:
                if pat.match(t):
                    counts[name] += 1
                    break

    # 目录页之外(正文)的同格式出现次数 — 用于验证规则通用性
    body_counts = {name: 0 for name, _ in PATTERNS}
    for pk in sl:
        if int(pk) in toc_pages: continue
        for t in sl[pk]:
            t = t.strip()
            if not t: continue
            for name, pat in PATTERNS:
                if pat.match(t) and len(t) <= 24:
                    body_counts[name] += 1
                    break

    levels = []
    for name, pat in PATTERNS:
        if counts[name] >= 3:   # 目录页出现 ≥3 次才算有效层级
            levels.append({"pattern": pat.pattern, "level": name, "count": counts[name],
                           "body_count": body_counts[name]})
            print(f"  {name:8s} 目录{counts[name]:4d}次  正文{body_counts[name]:4d}次  {pat.pattern}")

    if not levels:
        print("[警告] 未提取到有效层级规则")
    rules = {"levels": levels, "toc_pages": toc_pages}
    json.dump(rules, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"\n规则 → {out}")

if __name__ == "__main__":
    main()
