# wz10 p1 竖排封面自动降级（t350）

## 判据

```
vertical_text >= 2
且 (image >= 1 或 该页 OCR 最长行 <= 10 字)
→ orientation_mismatch，整页贴源图 + 文本 3Tr
```

## wz10 60 页命中清单

扫描全部 layout：
- p1: vt=2, img=0, maxline=4 → 命中
- p3: vt=2, img=1, maxline=6 → 命中（原 image 判据已命中）
- 其余 58 页：vt<2 → 不命中

构建 fallback.json：
```
[{"page":1,"reason":"orientation_mismatch(vt=2,img=0,maxline=4)"},
 {"page":3,"reason":"orientation_mismatch(vt=2,img=1,maxline=6)"}]
```

## 验收

- wz10 60 页；p1 **1 图 + 12 字隐形文本层**；p3 1 图。
- p1 源/产物裁片 `/tmp/wz10_src_p1.png`、`/tmp/wz10_prod_p1.png`。
- 8 本已有书扫描：wz9 p5(vt2,img1)、wz8 p3(vt2,img1) 原已命中；其余无 vt>=2 页 → 降级集合不变。页数按原构建不变。
- 产物 output/uploaded/wz10_cov.pdf（60页）。

未改 gold/punct_eval；未 push/commit。
