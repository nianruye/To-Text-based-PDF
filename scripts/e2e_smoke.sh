#!/usr/bin/env bash
# e2e_smoke.sh — 已有 data-dir 的 scan2pdf 端到端冒烟（t215/t226）
# 用法: bash scripts/e2e_smoke.sh --book ghbq --input source_pdf/ghbq.pdf \
#        --data-dir output/ghbq_full/_ocr_ghbq --out /tmp/e2e.pdf [--pages 20-23] [--repeat 2]
# 已知阻断：wz2 6 页在当前工作树（t208 未回退）gate=REJECT 66.7；干净 HEAD PASS 100%。
#           本脚本不掩盖，仍返回非零。
set -u
export PYTHONHASHSEED=0   # 构建确定性（t226）：消除 set/dict 顺序导致的页数/文本漂移
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/usr/bin/python3
BOOK=""; INPUT=""; DATA=""; OUT=""; PAGES=""; REPEAT=2
while [ $# -gt 0 ]; do
  case "$1" in
    --book) BOOK="$2"; shift 2;;
    --input) INPUT="$2"; shift 2;;
    --data-dir) DATA="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --pages) PAGES="$2"; shift 2;;
    --repeat) REPEAT="$2"; shift 2;;
    -h|--help) sed -n '2,8p' "$0"; exit 0;;
    *) echo "[e2e] 未知参数: $1" >&2; exit 2;;
  esac
done
if [ -z "$BOOK" ] || [ -z "$INPUT" ] || [ -z "$DATA" ] || [ -z "$OUT" ]; then
  echo "[e2e] 需要 --book/--input/--data-dir/--out" >&2; exit 2
fi
TMP="$(mktemp -d /tmp/e2e_XXXXXX)"; LOG="$TMP/run.log"; trap 'rm -rf "$TMP"' EXIT
cleanup() { rm -f "$OUT" "$OUT.report.json" "$OUT.gate.json"; rm -rf "$(dirname "$OUT")/_scan2pdf_$BOOK"; }
CMD=("$PY" "$ROOT/src/tools/scan2pdf.py" --input "$INPUT" --book "$BOOK" \
     --data-dir "$DATA" --out "$OUT" --skip-ocr --force)
if [ -n "$PAGES" ]; then CMD+=(--pages "$PAGES"); fi
summary() {
  "$PY" - "$OUT.report.json" "$OUT.gate.json" "$1" <<'PY'
import json,sys
rep,gate,rc=sys.argv[1],sys.argv[2],int(sys.argv[3])
r={}; g={}
try: r=json.load(open(rep,encoding='utf-8'))
except Exception: pass
try: g=json.load(open(gate,encoding='utf-8'))
except Exception: pass
m=g.get('metrics') or {}
verdict=g.get('verdict') or (r.get('gate') or {}).get('verdict')
pitch=m.get('pitch_ok_pct'); pages=m.get('pages')
if pitch is None: pitch=(r.get('gate') or {}).get('pitch_ok_pct')
if pages is None: pages=r.get('pages_out')
ex = r.get('exit')
if ex is None: ex = rc
reasons = ','.join((g.get('reasons') or [])[:2])
if not reasons: reasons = ('scan2pdf_rc=%s' % rc) if rc else '-'
print('exit=%s gate=%s pitch=%s pages=%s reason=%s' % (ex, verdict, pitch, pages, reasons))
PY
}
first=""; i=1
while [ "$i" -le "$REPEAT" ]; do
  cleanup
  "${CMD[@]}" >"$LOG" 2>&1
  rc=$?
  s="$(summary "$rc")"; echo "[e2e] run$i $s"
  if [ "$i" -eq 1 ]; then first="$s"; fi
  if [ "$rc" -ne 0 ]; then
    echo "[e2e] FAIL rc=$rc"
    echo "[e2e] 最后日志:"; tail -20 "$LOG" | sed 's/^/  /'
    echo "[e2e] book=$BOOK out=$OUT exit=$rc $(echo "$s" | sed 's/^exit=[^ ]* //')"
    exit 1
  fi
  i=$((i+1))
done
# 重复性断言：pages/pitch/gate 必须一致（两次独立构建）
if [ "$REPEAT" -gt 1 ]; then
  a_pages="$(echo "$first" | sed -n 's/.*pages=\([^ ]*\).*/\1/p')"
  b_pages="$(echo "$s" | sed -n 's/.*pages=\([^ ]*\).*/\1/p')"
  a_pitch="$(echo "$first" | sed -n 's/.*pitch=\([^ ]*\).*/\1/p')"
  b_pitch="$(echo "$s" | sed -n 's/.*pitch=\([^ ]*\).*/\1/p')"
  a_gate="$(echo "$first" | sed -n 's/.*gate=\([^ ]*\).*/\1/p')"
  b_gate="$(echo "$s" | sed -n 's/.*gate=\([^ ]*\).*/\1/p')"
  if [ "$a_pages" != "$b_pages" ] || [ "$a_pitch" != "$b_pitch" ] || [ "$a_gate" != "$b_gate" ]; then
    echo "[e2e] FAIL 重复性断言: run1 [$first] vs run${REPEAT} [$s]"
    echo "[e2e] 最后日志:"; tail -20 "$LOG" | sed 's/^/  /'
    exit 1
  fi
fi
echo "[e2e] book=$BOOK out=$OUT repeat=$REPEAT $s (repeatable)"
