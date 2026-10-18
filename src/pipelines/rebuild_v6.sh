#!/bin/bash
# 全书重建 + verify（C/C2 标点幻觉清理后的数据）
# expect-low = 影印页 ∪ OCR字数<50 的页（自动生成，不手工拼）
set -u
cd /opt/test || exit 1

TMP=/tmp/vert_wz7_v6_run
OUT=output/wz7_full/wz7_full_v6.pdf
LINES=data/wz7_full/wz7_full_spotting_lines_patched.json
COORDS=data/wz7_full/wz7_full_spotting_coords.json
SRC=source_pdf/wz7.pdf

echo "=== 1) 备份旧产物 ==="
[ -f output/wz7_full/wz7_full.pdf ] && cp -n output/wz7_full/wz7_full.pdf output/wz7_full/wz7_full_v5_prev.pdf && echo "旧版 -> wz7_full_v5_prev.pdf"
date '+%H:%M:%S'

echo "=== 2) 全书构建 $(date '+%H:%M:%S') ==="
VERT_BOLD=0.5 VERT_TOC_RESCUE_OK=1 VERT_TMP=$TMP \
  /usr/bin/python3 src/pipelines/build_vert.py "$LINES" "$COORDS" "$OUT" "$SRC" \
  > /tmp/build_v6.log 2>&1
BUILD_EXIT=$?
echo "BUILD_EXIT=$BUILD_EXIT $(date '+%H:%M:%S')"
[ $BUILD_EXIT -ne 0 ] && { echo "构建失败，尾部日志:"; tail -20 /tmp/build_v6.log; exit 1; }

echo "=== 3) 生成 expect-low ==="
/usr/bin/python3 - "$TMP/fax_pages.json" "$LINES" > /tmp/v6_expect_low.txt <<'PYEOF'
import json, sys
fax = set()
try:
    fax = set(json.load(open(sys.argv[1], encoding='utf-8'))['pages'])
except Exception:
    pass
LI = json.load(open(sys.argv[2], encoding='utf-8'))
low = set()
for k, rows in LI.items():
    n = len(''.join(str(t) for t in (rows or [])).replace('\n', ''))
    if n < 50:
        low.add(int(k) + 1)
allp = sorted(fax | low)
print(','.join(str(p) for p in allp))
sys.stderr.write('fax=%d low=%d 合计=%d\n' % (len(fax), len(low), len(allp)))
PYEOF
echo "expect-low 页数: $(tr ',' '\n' < /tmp/v6_expect_low.txt | wc -l)"

echo "=== 4) verify $(date '+%H:%M:%S') ==="
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py \
  "$OUT" "$COORDS" "$LINES" --src-pdf "$SRC" \
  --expect-low "$(cat /tmp/v6_expect_low.txt)" > /tmp/verify_v6.log 2>&1
VERIFY_EXIT=$?
echo "VERIFY_EXIT=$VERIFY_EXIT"
tail -30 /tmp/verify_v6.log

echo "=== 完成 $(date '+%H:%M:%S') ==="
ls -la "$OUT"
