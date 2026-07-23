"""
Mythos AI — Extract Artwork Images from Textbook PDF (v2)

Uses caption/title text-block matching: only extracts images from pages
where the artwork name appears as a caption, title, or heading (strong match),
not as a passing mention in a paragraph.
"""

import json
import re
from pathlib import Path

import fitz

KG_PATH = Path("data/knowledge_graph.json")
MAPPING_PATH = Path("data/page_mapping.json")
PDF_PATH = Path("textbook/classical_myth.pdf")
OUTPUT_DIR = Path("data/artwork_images")
MAP_OUTPUT = Path("data/artwork_image_map.json")

MIN_IMAGE_DIM = 150


def save_pixmap(pix, path_stem, output_dir):
    jpg = output_dir / f"{path_stem}.jpg"
    png = output_dir / f"{path_stem}.png"
    try:
        pix.save(str(jpg))
        return str(jpg)
    except Exception:
        pass
    try:
        rgb = fitz.Pixmap(fitz.csRGB, pix)
        try:
            rgb.save(str(jpg))
            return str(jpg)
        except Exception:
            rgb.save(str(png))
            return str(png)
    except Exception:
        pass
    try:
        pix.save(str(png))
        return str(png)
    except Exception:
        return None


_STOP_WORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "for",
               "with", "by", "and", "or", "his", "her", "its", "their",
               "one", "two", "from", "this", "that"}


def _significant_words(text):
    """Extract significant (non-stop) words from text, lowercased."""
    words = re.findall(r"[a-zA-Z\u00C0-\u024F]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _word_seq_match(text_words, name_words, min_ratio=0.6):
    """Check if name_words appear in order within text_words, allowing gaps
    of up to 2 extra words between name words."""
    ti = 0
    matched = 0
    for nw in name_words:
        while ti < len(text_words) and text_words[ti] != nw:
            ti += 1
        if ti >= len(text_words):
            break
        matched += 1
        ti += 1  # move past this word
    return matched / max(len(name_words), 1) >= min_ratio


def is_caption_match(text, artwork_name):
    """Check if a text block is a caption/title/heading for this artwork.
    
    Returns True if the text block is clearly a figure caption or section
    title (not a passing mention in a running paragraph).
    """
    t = text.strip()
    if not t:
        return False

    lt = t.lower()
    lname = artwork_name.lower().strip()

    # Direct match: text block IS the artwork name (common for figure captions
    # that start with the artwork name, possibly with "Figure X.Y" prefix)
    if lt.startswith(lname):
        return True

    # The artwork name appears early in the block (within first 60 chars)
    idx = lt.find(lname)
    if idx != -1 and idx < 60:
        return True

    # For short blocks (< 400 chars), try fuzzy word-sequence matching
    if len(t) < 400:
        # Check exact substring match first
        if lname in lt:
            return True
        # Fuzzy match: check if significant words appear in sequence
        name_words = _significant_words(artwork_name)
        text_words = _significant_words(t)
        if len(name_words) >= 2 and _word_seq_match(text_words, name_words):
            return True

    return False


def page_has_caption_for(page_text_blocks, artwork_name):
    """Check if any text block on the page is a caption/title for this artwork."""
    for b in page_text_blocks:
        if is_caption_match(b[4], artwork_name):
            return True
    return False


def main():
    print("=" * 60)
    print("Mythos AI — Artwork Image Extractor (v2 — caption matching)")
    print("=" * 60)

    if not PDF_PATH.exists():
        print(f"[ERROR] PDF not found: {PDF_PATH}")
        return

    kg = json.loads(KG_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    printed_to_pdf = {}
    for pdf_pg, printed_pg in mapping.items():
        if printed_pg is not None:
            printed_to_pdf.setdefault(printed_pg, []).append(int(pdf_pg))

    artworks = kg.get("artworks", [])
    print(f"Artworks in KG: {len(artworks)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF_PATH))

    # Pre-compute text blocks for every PDF page
    print("Reading PDF text...")
    page_text_blocks = {}
    for pdf_pg in range(1, len(doc) + 1):
        page = doc[pdf_pg - 1]
        blocks = page.get_text("blocks")
        page_text_blocks[pdf_pg] = [b for b in blocks if b[6] == 0]

    image_map = {}
    total_files = 0
    skip_no_page = 0
    skip_no_match = 0
    skip_no_image = 0
    errors = []

    for artwork in artworks:
        aid = artwork.get("id", "")
        name = artwork.get("name", "")
        pages = artwork.get("mentioned_pages", [])

        if not pages:
            skip_no_page += 1
            continue

        # Determine which PDF pages have a caption/title match for this artwork
        valid_pdf_pages = set()
        for printed_pg in pages:
            for pdf_pg in printed_to_pdf.get(printed_pg, []):
                if pdf_pg < 1 or pdf_pg > len(doc):
                    continue
                blocks = page_text_blocks.get(pdf_pg, [])
                if page_has_caption_for(blocks, name):
                    valid_pdf_pages.add(pdf_pg)

        if not valid_pdf_pages:
            skip_no_match += 1
            continue

        # Extract images from pages that have a caption match
        seen = set()
        saved = []
        seq = 0

        for pdf_pg in sorted(valid_pdf_pages):
            page = doc[pdf_pg - 1]
            for img in page.get_images(full=True):
                xref = img[0]
                key = (pdf_pg, xref)
                if key in seen:
                    continue
                seen.add(key)

                base = fitz.Pixmap(doc, xref)
                if base.width < MIN_IMAGE_DIM or base.height < MIN_IMAGE_DIM:
                    base = None
                    continue

                stem = f"{aid}_{seq}"
                path = save_pixmap(base, stem, OUTPUT_DIR)
                base = None

                if path:
                    saved.append(path)
                    seq += 1
                    total_files += 1
                else:
                    errors.append(f"{stem}: could not save")

        if seq == 0:
            skip_no_image += 1
        else:
            image_map[aid] = saved

    doc.close()

    MAP_OUTPUT.write_text(
        json.dumps(image_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nDone:")
    print(f"  With images: {len(image_map)} artworks")
    print(f"  Total files: {total_files}")
    print(f"  No page ref: {skip_no_page}")
    print(f"  No caption match: {skip_no_match}")
    print(f"  No images:   {skip_no_image}")
    if errors:
        print(f"  Errors:      {len(errors)}")
        for e in errors[:5]:
            print(f"    {e}")
    print(f"  Dir:         {OUTPUT_DIR.resolve()}")
    print(f"  Map:         {MAP_OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
