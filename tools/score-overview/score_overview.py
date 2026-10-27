#!/usr/bin/env python3
"""
score_overview.py — genera un'immagine PNG con tutte le pagine di una partitura
affiancate in griglia (contact sheet), da mostrare nella tab "Info" di ogni work.

Requisiti: pdftoppm (poppler) e Pillow.
    macOS:  brew install poppler && pip3 install Pillow

Uso singolo:
    python3 tools/score-overview/score_overview.py partitura.pdf --slug h-he
        -> assets/img/scores/h-he.png  e aggiunge `score_overview:` al .md del work

Uso batch (una cartella di PDF chiamati <slug>.pdf, es. h-he.pdf, calanchi.pdf):
    python3 tools/score-overview/score_overview.py --batch ~/Scores/pdf

Uso con mappa (consigliato): tools/score-overview/scores.json associa ogni slug
al suo PDF nel catalogo (ed eventuali pagine da includere):
    python3 tools/score-overview/score_overview.py --map
    python3 tools/score-overview/score_overview.py --map --only h-he

Più partiture per un lavoro (in scores.json):
    "pdf": ["versione-a.pdf", "versione-b.pdf"],
    "labels": ["Version 2022", "Version 2026"],   # facoltativo: titolo sopra ogni immagine
    "pages": [null, "1-4"],                        # facoltativo: pagine per ciascun PDF
    "merge": true                                  # facoltativo: un'unica griglia invece di due immagini

Opzioni per singolo lavoro in scores.json: "max_cell", "cols", "aspect", "width"
    es. "max_cell": 800 per un brano di una sola pagina (immagine più grande e nitida)

Opzioni utili:
    --cols N         numero di colonne (default: scelto per avvicinarsi a --aspect)
    --aspect 1.6     proporzione larghezza/altezza desiderata per la griglia
    --width 2400     larghezza finale in px (2400 = nitido su schermi retina a 800px)
    --gap 24         spazio tra le pagine (px, riferito a --width)
    --pages 1,3-18   solo queste pagine (es. per saltare pagine bianche)
    --max-cell 360   larghezza massima di ogni pagina in px: tiene la partitura
                     non leggibile anche per brani di poche pagine
    --no-md          non toccare i file .md
"""
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assets" / "img" / "scores"
WORKS_JSON = ROOT / "works" / "works.json"
DATA_DIR = ROOT / "data"


def repair_pdf(pdf: Path, tmp: Path) -> Path:
    """Alcuni PDF esportati da macOS/Anteprima hanno annotazioni malformate che
    impediscono il rendering. Prova a ripararli (pikepdf o Ghostscript)."""
    fixed = tmp / "repaired.pdf"
    try:
        import pikepdf
        with pikepdf.open(pdf) as doc:
            for page in doc.pages:
                if "/Annots" in page.obj:
                    del page.obj["/Annots"]
            doc.save(fixed)
        return fixed
    except ImportError:
        subprocess.run(["gs", "-q", "-o", str(fixed), "-sDEVICE=pdfwrite", str(pdf)], check=True)
        return fixed


def render_pages(pdf: Path, dpi: int, tmp: Path):
    cmd = lambda src: ["pdftoppm", "-r", str(dpi), "-gray", "-png", str(src), str(tmp / "p")]
    res = subprocess.run(cmd(pdf), capture_output=True, text=True)
    if res.returncode != 0 or "Failed to create page" in res.stderr:
        print(f"  … {pdf.name}: PDF danneggiato, provo a ripararlo")
        for f in tmp.glob("p-*.png"):
            f.unlink()
        subprocess.run(cmd(repair_pdf(pdf, tmp)), check=True, capture_output=True)
    files = sorted(tmp.glob("p-*.png"), key=lambda f: int(re.findall(r"\d+", f.stem)[-1]))
    if not files:
        sys.exit(f"Nessuna pagina renderizzata da {pdf}")
    return [Image.open(f).convert("L") for f in files]


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    idx = []
    for part in str(spec).split(","):
        a, _, b = part.strip().partition("-")
        lo, hi = int(a), int(b or a)
        idx.extend(range(lo - 1, min(hi, n)))
    return [i for i in idx if 0 <= i < n]


def best_cols(n, page_ratio, target_aspect):
    """page_ratio = w/h della cella. Sceglie le colonne con proporzione più vicina al target."""
    best, best_err = 1, float("inf")
    for c in range(1, n + 1):
        r = math.ceil(n / c)
        aspect = (c * page_ratio) / r
        err = abs(math.log(aspect / target_aspect))
        if err < best_err:
            best, best_err = c, err
    return best


def build_sheet(pages, cols, width, gap, margin, bg, border, max_cell):
    n = len(pages)
    # cella uniforme basata sulla proporzione più "larga" fra le pagine
    cell_ratio = max(p.width / p.height for p in pages)
    rows = math.ceil(n / cols)
    cell_w = (width - 2 * margin - (cols - 1) * gap) / cols
    if max_cell and cell_w > max_cell:
        cell_w = max_cell
        width = round(2 * margin + cols * cell_w + (cols - 1) * gap)
    cell_h = cell_w / cell_ratio
    height = round(2 * margin + rows * cell_h + (rows - 1) * gap)

    sheet = Image.new("L", (width, height), bg)
    draw = ImageDraw.Draw(sheet)
    for i, page in enumerate(pages):
        r, c = divmod(i, cols)
        # ultima riga: allinea a sinistra (come un libro aperto)
        x0 = margin + c * (cell_w + gap)
        y0 = margin + r * (cell_h + gap)
        scale = min(cell_w / page.width, cell_h / page.height)
        pw, ph = max(1, round(page.width * scale)), max(1, round(page.height * scale))
        thumb = page.resize((pw, ph), Image.LANCZOS)
        thumb = ImageOps.autocontrast(thumb, cutoff=0.2)
        px = round(x0 + (cell_w - pw) / 2)
        py = round(y0 + (cell_h - ph) / 2)
        sheet.paste(thumb, (px, py))
        if border is not None:
            draw.rectangle([px - 1, py - 1, px + pw, py + ph], outline=border)
    return sheet


AUTHOR = "Alessandro Massobrio"
SITE = "https://alessandromassobrio.com"


def png_metadata(title: str, year=None):
    """Metadati di copyright: chunk tEXt standard PNG + XMP (Photoshop, Lightroom, Google Immagini)."""
    from datetime import date
    from html import escape
    from PIL.PngImagePlugin import PngInfo
    yr = year or date.today().year
    copyright_ = f"© {yr} {AUTHOR}. All rights reserved. Score available on request."
    desc = f"{title} — overview of all score pages"
    info = PngInfo()
    for k, v in [("Title", f"{title} — score overview"), ("Author", AUTHOR),
                 ("Copyright", copyright_), ("Description", desc), ("Source", SITE)]:
        info.add_itxt(k, v)
    e = lambda x: escape(str(x))
    xmp = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"
 xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
 xmlns:Iptc4xmpCore="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"
 xmlns:plus="http://ns.useplus.org/ldf/xmp/1.0/">
 <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{e(title)} — score overview</rdf:li></rdf:Alt></dc:title>
 <dc:creator><rdf:Seq><rdf:li>{e(AUTHOR)}</rdf:li></rdf:Seq></dc:creator>
 <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{e(desc)}</rdf:li></rdf:Alt></dc:description>
 <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{e(copyright_)}</rdf:li></rdf:Alt></dc:rights>
 <xmpRights:Marked>True</xmpRights:Marked>
 <xmpRights:WebStatement>{SITE}</xmpRights:WebStatement>
 <photoshop:Credit>{e(AUTHOR)}</photoshop:Credit>
 <Iptc4xmpCore:CreatorContactInfo rdf:parseType="Resource"><Iptc4xmpCore:CiUrlWork>{SITE}</Iptc4xmpCore:CiUrlWork></Iptc4xmpCore:CreatorContactInfo>
 <plus:Licensor><rdf:Seq><rdf:li rdf:parseType="Resource"><plus:LicensorName>{e(AUTHOR)}</plus:LicensorName><plus:LicensorURL>{SITE}</plus:LicensorURL></rdf:li></rdf:Seq></plus:Licensor>
</rdf:Description></rdf:RDF></x:xmpmeta>
<?xpacket end="w"?>"""
    info.add_itxt("XML:com.adobe.xmp", xmp)
    return info


def work_info(slug: str):
    try:
        works = json.loads(WORKS_JSON.read_text())
        w = next((w for w in works if w["slug"] == slug), None)
        if w:
            return w["title"], w.get("year")
    except Exception:
        pass
    return slug, None


FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def credit_font(size):
    from PIL import ImageFont
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def add_credit(img, text, bg=255, color=120, display_width=800, display_px=11):
    """Aggiunge sotto la griglia una riga piccola con il ©, allineata a destra.
    La dimensione è calcolata perché sul sito appaia ~11px (le immagini sono mostrate a max 800px)."""
    img = img.convert("L")
    w = img.width
    size = max(display_px, round(display_px * w / display_width))
    font = credit_font(size)
    pad = round(size * 0.9)
    out = Image.new("L", (w, img.height + pad + size + round(size * 0.3)), bg)
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    tw = d.textlength(text, font=font)
    d.text((w - tw, img.height + pad), text, fill=color, font=font)
    return out


def credit_text(slug):
    title, year = work_info(slug)
    from datetime import date
    return f"© {year or date.today().year} {AUTHOR}"


def save_png(img, out: Path, levels: int, slug: str = None):
    out.parent.mkdir(parents=True, exist_ok=True)
    title, year = work_info(slug or out.stem)
    # partiture = bianco/nero: pochi livelli di grigio bastano e il file diventa leggero
    img.quantize(colors=levels, dither=Image.Dither.NONE).save(
        out, optimize=True, pnginfo=png_metadata(title, year))


def update_md(slug: str, value: str, key: str = "score_overview"):
    """Imposta `key: value` nel front matter del work (value=None rimuove la riga)."""
    works = json.loads(WORKS_JSON.read_text())
    work = next((w for w in works if w["slug"] == slug), None)
    if not work:
        print(f"  ! slug '{slug}' non trovato in works.json — .md non aggiornato")
        return
    md = DATA_DIR / f"{work['id']}.md"
    text = md.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        print(f"  ! {md.name}: front matter non trovato")
        return
    fm = m.group(1)
    pat = rf"^{re.escape(key)}:.*$"
    if value is None:
        fm2 = re.sub(pat + r"\n?", "", fm, flags=re.M).rstrip("\n")
    elif re.search(pat, fm, re.M):
        fm2 = re.sub(pat, f"{key}: {value}", fm, flags=re.M)
    else:
        fm2 = fm + f"\n{key}: {value}"
    if fm2 != fm:
        md.write_text(text.replace(fm, fm2, 1))
        print(f"  ✓ {md.relative_to(ROOT)}: {key} aggiornato")


FILE_PREFIX = "A.Massobrio"


def safe_name(text: str) -> str:
    """'Non v'è cosa' → 'Non-ve-cosa', 'Studi fenomenologici:legno' → 'Studi-fenomenologici-legno'."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    t = re.sub(r"[’'`\"]", "", t)
    t = re.sub(r"[^A-Za-z0-9+]+", "-", t)
    return t.strip("-.") or "score"


def md_title(slug: str):
    """Titolo dal front matter del .md (più curato di works.json), altrimenti da works.json."""
    title, year = work_info(slug)
    try:
        works = json.loads(WORKS_JSON.read_text())
        w = next(w for w in works if w["slug"] == slug)
        fm = (DATA_DIR / f"{w['id']}.md").read_text().split("---")[1]
        for line in fm.splitlines():
            k, _, v = line.partition(":")
            if k.strip() == "title" and v.strip():
                title = v.strip()
            if k.strip() == "year" and v.strip():
                year = v.strip()
    except Exception:
        pass
    return title, year


def image_name(slug: str, part: str = None) -> str:
    """A.Massobrio_<Titolo>_<anno>[_<parte>].png"""
    title, year = md_title(slug)
    name = f"{FILE_PREFIX}_{safe_name(title)}"
    if year:
        name += f"_{safe_name(year)}"
    if part:
        name += f"_{safe_name(part)}"
    return name + ".png"


def current_images(slug: str):
    """Immagini attualmente collegate al work (dal front matter), per poterle sostituire."""
    try:
        works = json.loads(WORKS_JSON.read_text())
        w = next(w for w in works if w["slug"] == slug)
        fm = (DATA_DIR / f"{w['id']}.md").read_text().split("---")[1]
        m = re.search(r"^score_overview:(.*)$", fm, re.M)
        if m:
            return [OUT_DIR / Path(u.strip().split("?")[0]).name for u in m.group(1).split("|") if u.strip()]
    except Exception:
        pass
    return []


def pdf_page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def load_pages(pdf: Path, pages_spec, args):
    with tempfile.TemporaryDirectory() as t:
        pages = render_pages(pdf, args.dpi, Path(t))
    pages = [pages[i] for i in parse_pages(pages_spec or args.pages, len(pages))]
    return pages[: args.max_pages] if args.max_pages else pages


def make_image(pages, out: Path, slug: str, args, label: str):
    ratio = max(p.width / p.height for p in pages)
    cols = args.cols or best_cols(len(pages), ratio, args.aspect)
    sheet = build_sheet(
        pages, cols, args.width, args.gap, args.margin,
        bg=args.bg, border=None if args.no_border else args.border,
        max_cell=args.max_cell,
    )
    if not args.no_credit:
        sheet = add_credit(sheet, credit_text(slug), bg=args.bg)
    save_png(sheet, out, args.levels, slug)
    kb = out.stat().st_size / 1024
    print(f"✓ {label}: {len(pages)} pagine, {cols} colonne → {out.relative_to(ROOT)} "
          f"({sheet.width}×{sheet.height}px, {kb:.0f} KB)")
    # ?v=<hash> cambia quando cambia l'immagine: il browser non usa la copia in cache
    import hashlib
    v = hashlib.md5(out.read_bytes()).hexdigest()[:8]
    return f"/assets/img/scores/{out.name}?v={v}"


def process(pdfs, slug: str, args, pages_specs=None, labels=None, merge=False):
    """pdfs: un Path o una lista di Path.
    - un PDF               → assets/img/scores/<slug>.png
    - più PDF, merge=True  → un'unica griglia con le pagine di tutti i PDF in sequenza
    - più PDF, merge=False → <slug>-1.png, <slug>-2.png… mostrate una sotto l'altra"""
    if isinstance(pdfs, (str, Path)):
        pdfs = [Path(pdfs)]
    specs = pages_specs if isinstance(pages_specs, list) else [pages_specs] * len(pdfs)
    specs = (specs + [None] * len(pdfs))[: len(pdfs)]
    loaded = [load_pages(pdf, spec, args) for pdf, spec in zip(pdfs, specs)]

    def remove(f):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            print(f"  ! non riesco a cancellare {f.name}: eliminalo a mano")

    previous = set(current_images(slug)) | {OUT_DIR / f"{slug}.png"} | set(OUT_DIR.glob(f"{slug}-[0-9]*.png"))
    if len(pdfs) == 1 or merge:
        all_pages = [pg for pages in loaded for pg in pages]
        outs = [OUT_DIR / image_name(slug)]
        urls = [make_image(all_pages, outs[0], slug, args, " + ".join(p.name for p in pdfs))]
        labels = None
    else:
        outs, urls = [], []
        for i, (pdf, pages) in enumerate(zip(pdfs, loaded), 1):
            part = labels[i - 1] if labels and i <= len(labels) and labels[i - 1] else str(i)
            out = OUT_DIR / image_name(slug, part)
            outs.append(out)
            urls.append(make_image(pages, out, slug, args, pdf.name))
    for f in previous - set(outs):
        if f.exists():
            remove(f)

    if not args.no_md:
        # numero di pagine della partitura (tutto il PDF, anche le pagine escluse dall'immagine)
        counts = [pdf_page_count(pdf) or len(pages) for pdf, pages in zip(pdfs, loaded)]
        if merge:
            counts = [sum(counts)]
        update_md(slug, " | ".join(map(str, counts)), key="score_pages")
        update_md(slug, " | ".join(urls))
        update_md(slug, " | ".join(labels) if labels else None, key="score_overview_labels")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="?", type=Path)
    ap.add_argument("--slug", help="slug del work (default: nome del file PDF)")
    ap.add_argument("--batch", type=Path, help="cartella di PDF chiamati <slug>.pdf")
    ap.add_argument("--cols", type=int)
    ap.add_argument("--aspect", type=float, default=1.6)
    ap.add_argument("--width", type=int, default=2400)
    ap.add_argument("--gap", type=int, default=24)
    ap.add_argument("--margin", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=100, help="risoluzione di rendering prima del ridimensionamento")
    ap.add_argument("--bg", type=int, default=255, help="grigio di sfondo 0–255")
    ap.add_argument("--border", type=int, default=210, help="grigio del bordo pagina 0–255")
    ap.add_argument("--no-border", action="store_true")
    ap.add_argument("--levels", type=int, default=32, help="livelli di grigio nel PNG")
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--no-credit", action="store_true", help="non aggiungere la riga © sotto l'immagine")
    ap.add_argument("--pages", help="pagine da includere, es. 1,3-18")
    ap.add_argument("--max-cell", type=int, default=360)
    ap.add_argument("--map", nargs="?", const=Path(__file__).with_name("scores.json"), type=Path,
                    help="file JSON slug → {pdf, pages}")
    ap.add_argument("--catalog", type=Path, help="sovrascrive la cartella 'catalog' di scores.json")
    ap.add_argument("--only", nargs="*", help="con --map: elabora solo questi slug")
    ap.add_argument("--no-md", action="store_true", help="non aggiornare i .md")
    args = ap.parse_args()

    if args.map:
        cfg = json.loads(Path(args.map).read_text())
        base = args.catalog or Path(cfg.get("catalog", ".")).expanduser()
        for slug, entry in cfg["works"].items():
            if args.only and slug not in args.only:
                continue
            if not entry or not entry.get("pdf"):
                continue
            paths = entry["pdf"] if isinstance(entry["pdf"], list) else [entry["pdf"]]
            # percorso assoluto o con ~ → ignora "catalog"
            pdfs = [base / Path(x).expanduser() for x in paths]
            missing = [x for x in pdfs if not x.exists()]
            if missing:
                for x in missing:
                    print(f"  ! {slug}: PDF non trovato → {x}")
                continue
            try:
                # opzioni per singolo lavoro (es. "max_cell": 800) sovrascrivono quelle da riga di comando
                wargs = argparse.Namespace(**vars(args))
                for k in ("max_cell", "cols", "aspect", "width"):
                    if k in entry:
                        setattr(wargs, k, entry[k])
                process(pdfs, slug, wargs, entry.get("pages"), entry.get("labels"), entry.get("merge", False))
            except subprocess.CalledProcessError:
                print(f"  ! {slug}: errore nel rendering")
    elif args.batch:
        pdfs = sorted(args.batch.glob("*.pdf"))
        if not pdfs:
            sys.exit(f"Nessun PDF in {args.batch}")
        for pdf in pdfs:
            process(pdf, pdf.stem, args)
    elif args.pdf:
        process(args.pdf, args.slug or args.pdf.stem, args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
