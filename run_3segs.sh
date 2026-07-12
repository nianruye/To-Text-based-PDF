#!/usr/bin/env bash
# 三段 wz1 切片各跑全流程: OCR -> titles -> page_numbers -> build
# 每段独立, 一段失败不中断其他段. 日志打印明确段落标记.
set -u
cd /opt/test
LOG=/tmp/wz1_segs.log
: > "$LOG"

run_seg () {
  local seg="$1" lines="$2" coords="$3" labels="$4" titles="$5" pagenum="$6" outpdf="$7" name="$8"
  echo "==================== [$name] 开始: $seg ====================" | tee -a "$LOG"
  echo "[$name] 1/4 OCR..." | tee -a "$LOG"
  if ! python3 run_spotting_ocr.py "$seg" "$lines" "$coords" >>"$LOG" 2>&1; then
    echo "[$name] !! OCR 失败, 跳过本段" | tee -a "$LOG"; return 1
  fi
  echo "[$name] 2/4 titles..." | tee -a "$LOG"
  if ! python3 extract_titles.py "$lines" "$labels" "$titles" >>"$LOG" 2>&1; then
    echo "[$name] !! titles 失败" | tee -a "$LOG"; return 1
  fi
  echo "[$name] 3/4 page_numbers..." | tee -a "$LOG"
  if ! python3 extract_page_numbers.py "$seg" "$pagenum" --lines="$lines" --coords="$coords" >>"$LOG" 2>&1; then
    echo "[$name] !! page_numbers 失败(非致命, 继续 build)" | tee -a "$LOG"
  fi
  echo "[$name] 4/4 build..." | tee -a "$LOG"
  if ! python3 build_pdf_v13.py "$seg" "$outpdf" "$lines" "$coords" "$titles" "" "$pagenum" >>"$LOG" 2>&1; then
    echo "[$name] !! build 失败" | tee -a "$LOG"; return 1
  fi
  if [ -f "$outpdf" ]; then
    local pg; pg=$(python3 -c "import fitz;print(fitz.open('$outpdf').page_count)")
    echo "[$name] ✓ 完成: $outpdf ($pg 页)" | tee -a "$LOG"
  else
    echo "[$name] !! build 未产出 PDF" | tee -a "$LOG"; return 1
  fi
}

run_seg wz1_part1_p1-20.pdf    wz1p1_lines.json   wz1p1_coords.json   wz1p1_lines_labels.json   wz1p1_titles.json   wz1p1_pagenum.json   成果_wz1p1.pdf   "SEG1 p1-20"
run_seg wz1_part2_p108-128.pdf wz1p108_lines.json wz1p108_coords.json wz1p108_lines_labels.json wz1p108_titles.json wz1p108_pagenum.json 成果_wz1p108.pdf "SEG2 p108-128"
run_seg wz1_part3_p199-219.pdf wz1p199_lines.json wz1p199_coords.json wz1p199_lines_labels.json wz1p199_titles.json wz1p199_pagenum.json 成果_wz1p199.pdf "SEG3 p199-219"

echo "==================== 全部段落结束 ====================" | tee -a "$LOG"
echo "--- 成果 PDF ---" | tee -a "$LOG"
ls -la /opt/test/成果_wz1p1.pdf /opt/test/成果_wz1p108.pdf /opt/test/成果_wz1p199.pdf 2>&1 | tee -a "$LOG"
echo "ALL_DONE" | tee -a "$LOG"
