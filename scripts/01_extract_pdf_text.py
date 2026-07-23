"""
程序 1/3：从 PDF 提取文字并按章节拆分

工作原理：
  1. 检测每一页的印刷页码（PDF页码 - 印刷页码 = 偏移量）
  2. 根据偏移量和目录中的印刷页码范围，将每页分配到对应章节
  3. 每章保存为一个 .txt 文件，附带每页的页码标记

输出：data/chapter_texts/chapter_XX.txt
"""

import re
import json
from pathlib import Path
from collections import Counter
import fitz


PDF_PATH = Path(__file__).parent.parent / "textbook" / "classical_myth.pdf"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "chapter_texts"
MAPPING_FILE = Path(__file__).parent.parent / "data" / "page_mapping.json"

# 章节信息： (章节号, 标题, 起始印刷页码, 结束印刷页码)
CHAPTERS = [
    ( 1, "Interpretation and Definition of Classical Mythology",       3,    38),
    ( 2, "Historical Background of Greek Mythology",                  39,    58),
    ( 3, "Myths of Creation",                                         59,    81),
    ( 4, "Zeus' Rise to Power: The Creation of Mortals",              82,   113),
    ( 5, "The Twelve Olympians: Zeus, Hera, and Their Children",      114,  135),
    ( 6, "The Nature of the Gods and Greek Religion",                 136,  164),
    ( 7, "Poseidon, Sea Deities, Group Divinities, and Monsters",     165,  175),
    ( 8, "Athena",                                                    176,  189),
    ( 9, "Aphrodite and Eros",                                        190,  222),
    (10, "Artemis",                                                   223,  246),
    (11, "Apollo",                                                    247,  280),
    (12, "Hermes",                                                    281,  299),
    (13, "Dionysus, Pan, Echo, and Narcissus",                        300,  333),
    (14, "Demeter and the Eleusinian Mysteries",                      334,  354),
    (15, "Views of the Afterlife: The Realm of Hades",                355,  383),
    (16, "Orpheus and Orphism: Mystery Religions in Roman Times",     384,  402),
    (17, "The Theban Saga",                                           403,  436),
    (18, "The Mycenaean Saga",                                        437,  466),
    (19, "The Trojan Saga and the Iliad",                             467,  516),
    (20, "The Returns and the Odyssey",                               517,  539),
    (21, "Perseus and the Legends of Argos",                          540,  553),
    (22, "Heracles",                                                  554,  581),
    (23, "Theseus and the Legends of Attica",                         582,  606),
    (24, "Jason, Medea, and the Argonauts",                           607,  630),
]


def detect_printed_page(text: str) -> int | None:
    """从页面文字中检测印刷页码"""
    lines = text.strip().split("\n")
    lines = [l.strip() for l in lines if l.strip()]
    if not lines:
        return None

    for line in lines[:5]:
        if re.match(r"^\d{1,4}$", line):
            n = int(line)
            if 1 <= n <= 750:
                return n
        m = re.match(r"^(\d{1,4})\s{2,}", line)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 750:
                return n
        m = re.search(r"\s{2,}(\d{1,4})\s*$", line)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 750:
                return n

    for line in lines[-3:]:
        if re.match(r"^\d{1,4}$", line):
            n = int(line)
            if 1 <= n <= 750:
                return n

    return None


def build_page_mapping(doc) -> dict:
    """为所有 PDF 页面检测印刷页码"""
    mapping = {}
    print("Detecting printed page numbers...")
    for i in range(len(doc)):
        text = doc[i].get_text("text")
        printed = detect_printed_page(text)
        mapping[i + 1] = printed
    return mapping


def find_offset(mapping: dict) -> int:
    """计算 PDF 页码与印刷页码的偏移量"""
    offsets = []
    for pdf_pg, printed_pg in mapping.items():
        if printed_pg is not None:
            offsets.append(pdf_pg - printed_pg)

    if not offsets:
        return 23

    counter = Counter(offsets)
    most_common = counter.most_common(1)[0][0]
    print(f"Offset detected: PDF page - printed page = {most_common}")
    return most_common


def run():
    print("=" * 60)
    print("Mythos AI -- Textbook Text Extractor")
    print("=" * 60)

    if not PDF_PATH.exists():
        print(f"\n[ERROR] PDF file not found at: {PDF_PATH}")
        print("Please place the textbook PDF in the textbook/ folder.")
        return

    print(f"\nOpening: {PDF_PATH.name}")
    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    print(f"Total PDF pages: {total_pages}")

    # Step 1: Detect printed page numbers and find offset
    mapping = build_page_mapping(doc)
    offset = find_offset(mapping)

    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_FILE.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Step 2: Assign each PDF page to a chapter using offset + ToC ranges
    page_chapter = {}
    for pdf_pg in range(1, total_pages + 1):
        printed_est = pdf_pg - offset
        assigned = None
        for ch_num, title, start, end in CHAPTERS:
            if start <= printed_est <= end:
                assigned = ch_num
                break
        page_chapter[pdf_pg] = assigned  # None means not in any chapter

    # Step 3: Extract text and save per chapter
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapter_texts = {}
    chapter_page_count = {}

    for pdf_pg in range(1, total_pages + 1):
        ch = page_chapter.get(pdf_pg)
        if ch is None:
            continue

        text = doc[pdf_pg - 1].get_text("text").strip()
        if not text:
            continue

        printed_pg = mapping.get(pdf_pg) or (pdf_pg - offset)
        marked = f"[PDF_PAGE {pdf_pg}] [PRINTED_PAGE {printed_pg}]\n{text}"

        if ch not in chapter_texts:
            chapter_texts[ch] = []
            chapter_page_count[ch] = 0
        chapter_texts[ch].append(marked)
        chapter_page_count[ch] += 1

    # Step 4: Save chapter files
    saved = 0
    for ch_num, title, start, end in CHAPTERS:
        texts = chapter_texts.get(ch_num, [])
        if not texts:
            print(f"  [WARN] Chapter {ch_num} has no text")
            continue

        full_text = "\n\n".join(texts)
        filename = f"chapter_{ch_num:02d}.txt"
        filepath = OUTPUT_DIR / filename
        filepath.write_text(full_text, encoding="utf-8")

        pg_count = chapter_page_count.get(ch_num, 0)
        print(f"  Saved: {filename} ({pg_count} pages, printed pp.{start}-{end})")
        saved += 1

    doc.close()
    print(f"\nDone! {saved} chapter files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    run()
