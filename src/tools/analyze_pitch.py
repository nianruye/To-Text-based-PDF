import json, statistics as st

def load(book):
    lines = json.load(open(f'{book}_spotting_lines.json'))
    coords = json.load(open(f'{book}_spotting_coords.json'))
    return lines, coords

def poly_metrics(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    ymin, ymax = min(ys), max(ys)
    xmin, xmax = min(xs), max(xs)
    return dict(ycenter=(ymin+ymax)/2, h=ymax-ymin, w=xmax-xmin,
                ymin=ymin, ymax=ymax, xmin=xmin, xmax=xmax)

def cv(vals):
    if len(vals) < 2: return None
    m = st.mean(vals)
    return st.pstdev(vals)/m if m else None

def analyze(book):
    lines, coords = load(book)
    page_pitches = {}       # page -> median pitch of body lines
    all_pitches = []        # every adjacent body pitch (whole book)
    bimodal_pages = 0
    eligible_pages = 0
    # for derivation comparison
    deriv_errors = []       # (measured_median, derived_area_over_n, derived_area_charcount)

    for pk in coords:
        polys = coords[pk]; txts = lines.get(pk, [])
        if len(polys) < 4:   # too few lines to judge
            continue
        rows = []
        for i, poly in enumerate(polys):
            m = poly_metrics(poly)
            m['text'] = txts[i] if i < len(txts) else ''
            m['nchar'] = len(m['text'])
            rows.append(m)
        heights = [r['h'] for r in rows]
        hmed = st.median(heights)
        # page vertical extent to detect header/footer
        ycs = sorted(r['ycenter'] for r in rows)
        ytop, ybot = ycs[0], ycs[-1]
        span = ybot - ytop
        body = []
        for r in rows:
            # height near median (0.6x..1.6x): exclude tiny/huge
            if not (0.6*hmed <= r['h'] <= 1.6*hmed):
                continue
            # exclude header (top 6% band) and footer (bottom 5% band) if isolated
            body.append(r)
        # header/footer removal by y-band: drop lines far above/below main cluster
        if len(body) >= 5:
            bys = sorted(r['ycenter'] for r in body)
            # trim a top line if gap to next is > 2.2x median gap
            def gaps(seq): return [seq[i+1]-seq[i] for i in range(len(seq)-1)]
            g = gaps(bys)
            gmed = st.median(g) if g else 0
            # remove leading line if first gap unusually large (header)
            keep = body[:]
            if g and gmed>0:
                # sort body by ycenter
                bs = sorted(body, key=lambda r:r['ycenter'])
                # drop top outlier
                if bs and (bs[1]['ycenter']-bs[0]['ycenter']) > 2.0*gmed:
                    bs = bs[1:]
                # drop bottom outlier (page number)
                if len(bs)>=2 and (bs[-1]['ycenter']-bs[-2]['ycenter']) > 2.0*gmed:
                    bs = bs[:-1]
                keep = bs
            body = keep
        if len(body) < 4:
            continue
        eligible_pages += 1
        bs = sorted(body, key=lambda r: r['ycenter'])
        pitches = [bs[i+1]['ycenter']-bs[i]['ycenter'] for i in range(len(bs)-1)]
        pitches = [p for p in pitches if p > 0]
        if len(pitches) < 3:
            continue
        pmed = st.median(pitches)
        page_pitches[pk] = pmed
        all_pitches.extend(pitches)

        # bimodal detection on this page: any pitch > 1.6x page median => second (bigger) peak
        big = [p for p in pitches if p > 1.6*pmed]
        if len(big) >= 1 and len(big) <= len(pitches)*0.5:
            bimodal_pages += 1

        # DERIVATION method: area / nlines, area = body region height span / (n-1) is basically pitch;
        # but the "naive" derivation: total body vertical extent / number of lines
        bmin = min(r['ymin'] for r in body); bmax = max(r['ymax'] for r in body)
        body_h = bmax - bmin
        n = len(body)
        derived_area_over_n = body_h / n          # area(1D height) / rows
        # area+charcount variant: use avg glyph area to back out line height
        # approx: assume square-ish glyphs, glyph_w ~ h; row width * h ~ nchar*h^2 -> not needed
        # Instead: total body area / total chars gives glyph area; line pitch ~ sqrt? we approximate
        total_chars = sum(r['nchar'] for r in body) or 1
        body_w = max(r['xmax'] for r in body) - min(r['xmin'] for r in body)
        body_area = body_h * body_w
        glyph_area = body_area / total_chars
        derived_area_char = glyph_area ** 0.5 * 1.0  # rough glyph size -> not a real pitch
        deriv_errors.append((pmed, derived_area_over_n, derived_area_char))

    return dict(book=book,
                eligible_pages=eligible_pages,
                page_median_pitches=list(page_pitches.values()),
                all_pitches=all_pitches,
                bimodal_pages=bimodal_pages,
                deriv=deriv_errors)

def report(res):
    b = res['book']
    ap = res['all_pitches']
    pm = res['page_median_pitches']
    print(f"\n===== {b} =====")
    print(f"eligible pages: {res['eligible_pages']}")
    print(f"total adjacent body pitches: {len(ap)}")
    print(f"whole-book pitch: median={st.median(ap):.2f} mean={st.mean(ap):.2f} "
          f"stdev={st.pstdev(ap):.2f} CV={cv(ap):.3f}")
    print(f"pitch p5={sorted(ap)[int(len(ap)*0.05)]:.2f} p95={sorted(ap)[int(len(ap)*0.95)]:.2f}")
    # per-page median pitch consistency (this is the STABLE signal)
    print(f"per-page median pitch: median={st.median(pm):.2f} "
          f"stdev={st.pstdev(pm):.2f} CV={cv(pm):.3f}")
    print(f"bimodal pages (has >=1 pitch >1.6x page-median): {res['bimodal_pages']}/{res['eligible_pages']} "
          f"= {100*res['bimodal_pages']/res['eligible_pages']:.1f}%")
    # derivation error
    d = res['deriv']
    e1 = [abs(dm - da)/dm for dm, da, dc in d if dm>0]
    e2 = [abs(dm - dc)/dm for dm, da, dc in d if dm>0]
    print(f"DERIV area/nlines vs measured: median rel-err={100*st.median(e1):.1f}% mean={100*st.mean(e1):.1f}%")
    print(f"DERIV sqrt(glyph-area) vs measured: median rel-err={100*st.median(e2):.1f}% mean={100*st.mean(e2):.1f}%")
    # robust book-level pitch = median of per-page medians
    return st.median(pm), cv(pm), 100*res['bimodal_pages']/res['eligible_pages'], 100*st.median(e1)

for book in ['wz1','wz2']:
    r = analyze(book)
    report(r)
