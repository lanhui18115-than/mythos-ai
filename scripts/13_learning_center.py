"""
Mythos AI — Learning Center (13_learning_center.py)

Generates a three-tab learning center:
  Tab 1: Textbook Reader (PDF embed with chapter navigation)
  Tab 2: Chapter Summary (characters, myths, concepts, places)
  Tab 3: Chapter Quiz (3 sets x 10 questions per chapter, MC/TF/SA)

Usage:
    py -3 scripts/13_learning_center.py

Output: output/learning_center.html
"""

import json
import random
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "learning_center.html"
# 按章节拆分的 PDF 文件（data/chapter_pdfs/ch_XX.pdf）
PDF_PATH = "../data/chapter_pdfs/ch_{ch:02d}.pdf"

random.seed(137)


# ─────────────────────────────────────────────
# 1. Load data
# ─────────────────────────────────────────────

def load_chapter(ch):
    path = KNOWLEDGE_DIR / f"chapter_{ch:02d}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)





# Verified chapter start pages (printed book page numbers), extracted from PDF.
# PDF_page = printed_page + 23 for all chapters (Ch1 special: printed=1 → PDF=25).
# Manually verified chapter page ranges (printed book pages).
CHAPTER_STARTS = {
    1: 3, 2: 39, 3: 59, 4: 82, 5: 114, 6: 136, 7: 165, 8: 176, 9: 190,
    10: 223, 11: 247, 12: 281, 13: 300, 14: 334, 15: 355, 16: 384,
    17: 408, 18: 437, 19: 467, 20: 517, 21: 540, 22: 554, 23: 582, 24: 607,
}
CHAPTER_ENDS = {
    1: 38, 2: 58, 3: 81, 4: 113, 5: 135, 6: 164, 7: 175, 8: 189, 9: 222,
    10: 246, 11: 280, 12: 299, 13: 333, 14: 354, 15: 383, 16: 400,
    17: 436, 18: 466, 19: 516, 20: 539, 21: 553, 22: 581, 23: 606, 24: 634,
}


def printed_to_pdf(printed_page):
    """Map printed book page number to PDF internal page number.
    Verified: PDF_page = printed_page + 23 for all content pages.
    """
    if printed_page == 1:
        return 25
    return printed_page + 23


def get_chapter_page_range(ch_data, ch_num):
    """Get (printed_start, printed_end, pdf_start, pdf_end) for a chapter.
    Uses manually verified CHAPTER_STARTS/ENDS instead of evidence-derived ranges.
    """
    printed_start = CHAPTER_STARTS.get(ch_num)
    printed_end = CHAPTER_ENDS.get(ch_num)
    if not printed_start or not printed_end:
        return None, None, None, None
    pdf_start = printed_to_pdf(printed_start)
    pdf_end = printed_to_pdf(printed_end)
    return printed_start, printed_end, pdf_start, pdf_end


def get_printed_page_ref(c):
    """Get single printed page reference from evidence."""
    for ev in c.get("evidence", []):
        pp = ev.get("printed_pages", [])
        if pp:
            return pp[0]
    return None


# ─────────────────────────────────────────────
# 2. Chapter Summary data
# ─────────────────────────────────────────────

def build_chapter_summary(ch_data, ch_num):
    """Extract structured summary for one chapter."""
    chars = ch_data.get("characters", [])
    rels = ch_data.get("relationships", [])
    myths_raw = ch_data.get("myths", [])
    places = ch_data.get("places", [])
    concepts = ch_data.get("concepts", [])
    artworks_raw = ch_data.get("artworks", [])

    # Characters: name, roman, type, epithets, domains
    char_list = []
    for c in chars:
        entry = {
            "n": c.get("name", ""),
            "r": c.get("roman_name", ""),
            "tl": c.get("type", ""),
            "e": c.get("epithets", []),
            "d": c.get("domains", []),
            "de": c.get("description", ""),
        }
        char_list.append(entry)

    # Myths: name + brief summary + page refs
    myth_list = []
    for m in myths_raw:
        myth_list.append({
            "n": m.get("name", ""),
            "s": m.get("summary", "") or "",
            "p": m.get("mentioned_pages", []),
        })

    # Places
    place_list = [p.get("name", "") for p in places]

    # Concepts
    concept_list = []
    for co in concepts:
        concept_list.append({
            "n": co.get("name", ""),
            "de": co.get("description", ""),
            "p": co.get("mentioned_pages", []),
        })

    # Artworks
    art_list = []
    for a in artworks_raw:
        art_list.append({
            "n": a.get("name", ""),
            "de": a.get("description", ""),
            "p": a.get("mentioned_pages", []),
        })

    return {
        "characters": char_list,
        "myths": myth_list,
        "places": place_list,
        "concepts": concept_list,
        "artworks": art_list,
    }


# ─────────────────────────────────────────────
# 3. Quiz question generator (per chapter)
# ─────────────────────────────────────────────

# Track used (entity, question_type) combos per chapter to avoid duplicates
used_seeds = defaultdict(set)

# Global pools (loaded from full knowledge graph) for distractor fallback
GLOBAL_POOLS = {
    "roman_names": [],
    "epithets": [],
    "domains": [],
    "symbols": [],
    "names": [],
    "types": [],
}


def init_global_pools(kg):
    """Load global distractor pools from the full knowledge graph."""
    chars = kg.get("characters", [])
    names_seen = set()
    roman_seen = set()
    for c in chars:
        n = c.get("name", "")
        if n and n not in names_seen:
            GLOBAL_POOLS["names"].append(n)
            names_seen.add(n)
        rn = c.get("roman_name", "")
        if rn and rn != n and rn not in roman_seen:
            GLOBAL_POOLS["roman_names"].append(rn)
            roman_seen.add(rn)
        for ep in c.get("epithets", []):
            if ep.strip():
                GLOBAL_POOLS["epithets"].append(ep.strip())
        for d in c.get("domains", []):
            if d.strip():
                GLOBAL_POOLS["domains"].append(d.strip())
        for sy in c.get("symbols", []):
            if sy.strip():
                GLOBAL_POOLS["symbols"].append(sy.strip())
        t = c.get("type", "")
        if t:
            GLOBAL_POOLS["types"].append(t)


def _mark_used(ch, key):
    used_seeds[ch].add(key)


def _is_used(ch, key):
    return key in used_seeds[ch]


def pick_distractors(correct, pool, count=3, exclude=None, supplement=None):
    """Pick distractors from pool; if not enough, supplement from global pool."""
    if exclude is None:
        exclude = set()
    exclude.add(correct)
    available = [x for x in pool if x not in exclude]
    random.shuffle(available)
    if len(available) < count and supplement:
        extra = [x for x in supplement if x not in exclude and x not in available]
        random.shuffle(extra)
        available.extend(extra)
    return available[:count]


def local_pool(ch_data, key):
    """Extract a set of values from chapter characters by key."""
    vals = set()
    for c in ch_data.get("characters", []):
        for v in c.get(key, []):
            if v.strip():
                vals.add(v.strip())
    return list(vals)


def gen_mc_roman(ch_data, ch_num):
    """MC: Which Roman name is equivalent to Greek X?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("roman_name") and c["roman_name"] != c["name"]]
    if len(chars) < 4:
        return None
    c = random.choice(chars)
    key = f"mc_roman_{c['name']}"
    if _is_used(ch_num, key):
        return None
    correct = c["roman_name"]
    pool = list({ch.get("roman_name") for ch in ch_data.get("characters", [])
                 if ch.get("roman_name") and ch["roman_name"] != correct})
    distractors = pick_distractors(correct, pool, count=3, supplement=GLOBAL_POOLS["roman_names"])
    if len(distractors) < 3:
        return None
    options = [correct] + distractors
    random.shuffle(options)
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    exp = f"{c['name']} (Greek) → {c['roman_name']} (Roman)."
    q = f"Which Roman god/goddess is equivalent to the Greek {c['name']}?"

    # Validate: answer NOT in question
    if correct.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "mc", "cat": "Roman Equivalent", "q": q,
            "opts": options, "ans": correct, "exp": exp, "ref": ref}


def gen_mc_epithet(ch_data, ch_num):
    """MC: Which is an epithet of X?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("epithets") and len(c["epithets"]) > 0]
    if len(chars) < 2:
        return None
    c = random.choice(chars)
    epithet = random.choice(c["epithets"])
    key = f"mc_ep_{c['name']}_{epithet}"
    if _is_used(ch_num, key):
        return None
    # Build distractor pool from other characters' epithets in same chapter
    all_epithets = local_pool(ch_data, "epithets")
    distractors = pick_distractors(epithet, all_epithets, count=3, supplement=GLOBAL_POOLS["epithets"])
    if len(distractors) < 3:
        return None
    options = [epithet] + distractors
    random.shuffle(options)
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    exp = f"{c['name']} is known by the epithet '{epithet}'."
    q = f"Which of the following is an epithet of {c['name']}?"

    if epithet.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "mc", "cat": "Epithet", "q": q,
            "opts": options, "ans": epithet, "exp": exp, "ref": ref}


def gen_mc_domain(ch_data, ch_num):
    """MC: X is the god/goddess of which domain?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("domains") and len(c["domains"]) > 0]
    if len(chars) < 2:
        return None
    c = random.choice(chars)
    domain = random.choice(c["domains"])
    key = f"mc_dom_{c['name']}_{domain}"
    if _is_used(ch_num, key):
        return None
    all_domains = local_pool(ch_data, "domains")
    distractors = pick_distractors(domain, all_domains, count=3, supplement=GLOBAL_POOLS["domains"])
    if len(distractors) < 3:
        return None
    options = [domain] + distractors
    random.shuffle(options)
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    exp = f"{c['name']} governs: {', '.join(c['domains'])}."
    q = f"{c['name']} is the god/goddess of which domain?"

    if domain.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "mc", "cat": "Domain", "q": q,
            "opts": options, "ans": domain, "exp": exp, "ref": ref}


def gen_mc_parent(ch_data, ch_num):
    """MC: Who is the parent of X?"""
    rels = ch_data.get("relationships", [])
    parent_rels = [r for r in rels if r.get("type") in ("parent_of",)]
    if len(parent_rels) < 4:
        return None
    r = random.choice(parent_rels)
    child = r.get("target", "")
    parent = r.get("source", "")
    key = f"mc_par_{child}_{parent}"
    if _is_used(ch_num, key) or not child or not parent:
        return None
    all_chars = [c["name"] for c in ch_data.get("characters", [])]
    pool = [x for x in all_chars if x != parent]
    if len(pool) < 3:
        return None
    distractors = pick_distractors(parent, pool, count=3)
    if len(distractors) < 3:
        return None
    options = [parent] + distractors
    random.shuffle(options)
    ref = f"ch.{ch_num} p.{r.get('page', '?')}"
    desc = r.get("description", "")
    exp = desc if desc else f"{parent} is the parent of {child}."
    q = f"Who is the parent of {child}?"

    if parent.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "mc", "cat": "Parentage", "q": q,
            "opts": options, "ans": parent, "exp": exp, "ref": ref}


def gen_tf_domain(ch_data, ch_num):
    """TF: X is the god/goddess of Y?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("domains") and len(c["domains"]) > 0]
    if len(chars) < 3:
        return None
    c = random.choice(chars)
    is_true = random.random() < 0.5
    if is_true:
        domain = random.choice(c["domains"])
        key = f"tf_dom_true_{c['name']}_{domain}"
        if _is_used(ch_num, key):
            return None
        q = f"{c['name']} is the god/goddess of {domain}."
        correct = True
        exp = f"Correct. {c['name']} governs: {', '.join(c['domains'])}."
    else:
        others = [x for x in chars if x["name"] != c["name"]]
        if not others:
            return None
        swap = random.choice(others)
        domain = random.choice(swap["domains"])
        key = f"tf_dom_false_{c['name']}_{domain}"
        if _is_used(ch_num, key):
            return None
        q = f"{c['name']} is the god/goddess of {domain}."
        correct = False
        exp = f"No. {c['name']} governs: {', '.join(c['domains'])}, not {domain}."

    # Validate: answer not in question (for TF, ans is bool, no issue)
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")

    _mark_used(ch_num, key)
    return {"t": "tf", "cat": "Divine Domains", "q": q,
            "ans": correct, "exp": exp, "ref": ref}


def gen_tf_relation(ch_data, ch_num):
    """TF: X is the parent/spouse/child of Y?"""
    rels = ch_data.get("relationships", [])
    tf_types = {"parent_of": "parent of", "child_of": "child of",
                "spouse_of": "spouse of", "lover_of": "lover of"}
    candidates = []
    for r in rels:
        rt = r.get("type")
        if rt in tf_types:
            src = r.get("source", "")
            tgt = r.get("target", "")
            if src and tgt:
                candidates.append((r, src, tgt, rt))
    if len(candidates) < 4:
        return None
    r, src, tgt, rt = random.choice(candidates)
    label = tf_types[rt]
    is_true = random.random() < 0.5
    if is_true:
        key = f"tf_rel_true_{src}_{tgt}_{rt}"
        if _is_used(ch_num, key):
            return None
        q = f"{src} is the {label} {tgt}."
        correct = True
        desc = r.get("description", "")
        exp = desc if desc else f"Yes, {src} is the {label} {tgt}."
    else:
        # Pick a wrong src from same chapter
        all_chars = [c["name"] for c in ch_data.get("characters", []) if c["name"] != src and c["name"] != tgt]
        if not all_chars:
            return None
        wrong = random.choice(all_chars)
        key = f"tf_rel_false_{wrong}_{tgt}_{rt}"
        if _is_used(ch_num, key):
            return None
        q = f"{wrong} is the {label} {tgt}."
        correct = False
        exp = f"No. {src} (not {wrong}) is the {label} {tgt}."

    ref = f"ch.{ch_num} p.{r.get('page', '?')}"

    _mark_used(ch_num, key)
    return {"t": "tf", "cat": "Myth Relationships", "q": q,
            "ans": correct, "exp": exp, "ref": ref}


def gen_tf_symbol(ch_data, ch_num):
    """TF: X's symbol is Y?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("symbols") and len(c["symbols"]) > 0]
    if len(chars) < 2:
        return None
    c = random.choice(chars)
    is_true = random.random() < 0.5
    if is_true:
        symbol = random.choice(c["symbols"])
        key = f"tf_sym_true_{c['name']}_{symbol}"
        if _is_used(ch_num, key):
            return None
        q = f"The symbol of {c['name']} is {symbol}."
        correct = True
        exp = f"Yes. Symbols of {c['name']}: {', '.join(c['symbols'])}."
    else:
        others = [x for x in chars if x["name"] != c["name"]]
        if not others:
            return None
        swap = random.choice(others)
        symbol = random.choice(swap["symbols"])
        key = f"tf_sym_false_{c['name']}_{symbol}"
        if _is_used(ch_num, key):
            return None
        q = f"The symbol of {c['name']} is {symbol}."
        correct = False
        exp = f"No. Symbols of {c['name']}: {', '.join(c['symbols'])}, not {symbol}."

    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")

    _mark_used(ch_num, key)
    return {"t": "tf", "cat": "Symbols", "q": q,
            "ans": correct, "exp": exp, "ref": ref}


def gen_sa_roman(ch_data, ch_num):
    """SA: What is the Roman name of X?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("roman_name") and c["roman_name"] != c["name"]]
    if not chars:
        return None
    c = random.choice(chars)
    key = f"sa_roman_{c['name']}"
    if _is_used(ch_num, key):
        return None
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    ans = c["roman_name"]
    q = f"What is the Roman name of {c['name']}?"
    exp = f"The Roman equivalent of {c['name']} is {ans}."

    if ans.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "sa", "cat": "Roman Equivalents", "q": q,
            "ans": ans, "exp": exp, "ref": ref}


def gen_sa_parent(ch_data, ch_num):
    """SA: Who is the parent of X?"""
    rels = ch_data.get("relationships", [])
    parent_rels = [r for r in rels if r.get("type") in ("parent_of",)]
    if not parent_rels:
        return None
    r = random.choice(parent_rels)
    child = r.get("target", "")
    parent = r.get("source", "")
    key = f"sa_par_{child}_{parent}"
    if _is_used(ch_num, key) or not child or not parent:
        return None
    ref = f"ch.{ch_num} p.{r.get('page', '?')}"
    desc = r.get("description", "")
    exp = desc if desc else f"{parent} is the parent of {child}."
    q = f"Who is the parent of {child}?"

    if parent.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "sa", "cat": "Parentage", "q": q,
            "ans": parent, "exp": exp, "ref": ref}


def gen_sa_epithet(ch_data, ch_num):
    """SA: What is an epithet of X?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("epithets") and len(c["epithets"]) > 0]
    if not chars:
        return None
    c = random.choice(chars)
    epithet = random.choice(c["epithets"])
    key = f"sa_ep_{c['name']}_{epithet}"
    if _is_used(ch_num, key):
        return None
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    q = f"What is an epithet of {c['name']}?"
    ans = epithet
    exp = f"{c['name']} is known by the epithet '{epithet}'."

    if ans.lower() in q.lower():
        return None

    _mark_used(ch_num, key)
    return {"t": "sa", "cat": "Epithet", "q": q,
            "ans": ans, "exp": exp, "ref": ref}


# ─────────────────────────────────────────────
# 4. Generate 3 sets per chapter
# ─────────────────────────────────────────────

ALL_GENS = [
    gen_mc_roman, gen_mc_epithet, gen_mc_domain, gen_mc_parent,
    gen_tf_domain, gen_tf_relation, gen_tf_symbol,
    gen_sa_roman, gen_sa_parent, gen_sa_epithet,
]


def gen_tf_type(ch_data, ch_num):
    """Fallback TF: X is a (type)? Uses character type field."""
    chars = ch_data.get("characters", [])
    valid = [c for c in chars if c.get("type") in ("god", "goddess", "mortal", "hero", "monster", "titan")]
    if len(valid) < 3:
        return None
    c = random.choice(valid)
    is_true = random.random() < 0.5
    t = c.get("type", "")
    label_map = {"god": "a god", "goddess": "a goddess", "mortal": "a mortal",
                 "hero": "a hero", "monster": "a monster", "titan": "a titan"}
    label = label_map.get(t, t)
    if is_true:
        key = f"tf_type_true_{c['name']}_{t}"
        if _is_used(ch_num, key): return None
        q = f"{c['name']} is {label}."
        correct = True
        exp = f"Yes, {c['name']} is {label} in Greek mythology."
    else:
        others = [x for x in valid if x.get("type") != t and x["name"] != c["name"]]
        if not others: return None
        swap = random.choice(others)
        st = swap.get("type", "")
        sl = label_map.get(st, st)
        key = f"tf_type_false_{c['name']}_{st}"
        if _is_used(ch_num, key): return None
        q = f"{c['name']} is {sl}."
        correct = False
        exp = f"No, {c['name']} is {label}, not {sl}."
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    _mark_used(ch_num, key)
    return {"t": "tf", "cat": "Character Type", "q": q, "ans": correct, "exp": exp, "ref": ref}


def gen_sa_type(ch_data, ch_num):
    """Fallback SA: What type of being is X?"""
    chars = [c for c in ch_data.get("characters", [])
             if c.get("type") in ("god", "goddess", "mortal", "hero", "monster", "titan")]
    if not chars:
        return None
    c = random.choice(chars)
    key = f"sa_type_{c['name']}"
    if _is_used(ch_num, key): return None
    t = c.get("type", "")
    label_map = {"god": "a god", "goddess": "a goddess", "mortal": "a mortal",
                 "hero": "a hero", "monster": "a monster", "titan": "a titan"}
    ans = label_map.get(t, t)
    # Use full word, not article
    ans_word = t if t else ans
    q = f"What type of being is {c['name']}?"
    exp = f"{c['name']} is {ans} in Greek mythology."
    ref_page = get_printed_page_ref(c)
    ref = f"ch.{ch_num}" + (f" p.{ref_page}" if ref_page else "")
    _mark_used(ch_num, key)
    return {"t": "sa", "cat": "Character Type", "q": q, "ans": ans_word, "exp": exp, "ref": ref}


FALLBACK_GENS = [gen_tf_type, gen_sa_type]


def generate_one_set(ch_data, ch_num):
    """Generate one set of 10 questions using any available generators."""
    questions = []
    # Collect all viable questions from all generators
    all_candidates = []
    random.shuffle(ALL_GENS)
    for gen in ALL_GENS + FALLBACK_GENS:
        for _ in range(40):
            q = gen(ch_data, ch_num)
            if q:
                all_candidates.append(q)
                break
    random.shuffle(all_candidates)

    # Ensure at least 1 of each major type if possible
    has_mc = False
    has_tf = False
    has_sa = False
    final = []
    for q in all_candidates:
        if q["t"] == "mc" and not has_mc:
            final.append(q); has_mc = True
        elif q["t"] == "tf" and not has_tf:
            final.append(q); has_tf = True
        elif q["t"] == "sa" and not has_sa:
            final.append(q); has_sa = True
        if has_mc and has_tf and has_sa:
            break
    # Fill remaining from all candidates
    for q in all_candidates:
        if len(final) >= 10:
            break
        if q not in final:
            final.append(q)

    if len(final) < 10:
        # Try broader fallback: second pass without dedup restriction
        used_seeds.clear()
        for gen in FALLBACK_GENS:
            for _ in range(40):
                q = gen(ch_data, ch_num)
                if q:
                    final.append(q)
                    break
            if len(final) >= 10:
                break

    if len(final) >= 10:
        random.shuffle(final)
        return final[:10]
    return None


def generate_chapter_quizzes(ch_data, ch_num):
    """Generate 3 sets of 10 questions for one chapter."""
    global used_seeds
    sets = []
    for s in range(3):
        used_seeds.clear()
        s_data = generate_one_set(ch_data, ch_num)
        if s_data and len(s_data) == 10:
            sets.append(s_data)
        else:
            used_seeds.clear()
            s_data = generate_one_set(ch_data, ch_num)
            if s_data and len(s_data) == 10:
                sets.append(s_data)
            else:
                # If still fails, make a third attempt with only fallbacks
                used_seeds.clear()
                fallback = []
                for gen in FALLBACK_GENS:
                    for _ in range(100):
                        q = gen(ch_data, ch_num)
                        if q:
                            fallback.append(q)
                            if len(fallback) >= 10:
                                break
                    if len(fallback) >= 10:
                        break
                if len(fallback) >= 10:
                    sets.append(fallback[:10])
                else:
                    print(f"    [WARN] Ch{ch_num} Set{s+1}: only {len(fallback)} questions generated")
                    sets.append([])
    return sets


# ─────────────────────────────────────────────
# 5. Final validation
# ─────────────────────────────────────────────

def validate_question(q, ch_num, set_idx):
    """Validate a single question for quality issues. Returns (ok, error_msg)."""
    t = q.get("t")
    if t not in ("mc", "tf", "sa"):
        return False, f"unknown type: {t}"
    if not q.get("q"):
        return False, "empty question"
    if t == "mc":
        if not q.get("opts") or len(q["opts"]) < 2:
            return False, "MC needs >=2 options"
        if q["ans"] not in q["opts"]:
            return False, "MC answer not in options"
    ans_str = str(q.get("ans", "")).lower() if t != "tf" else ""
    q_text = q.get("q", "").lower()
    if ans_str and ans_str in q_text and len(ans_str) > 2:
        return False, f"answer '{q['ans']}' found in question"
    if not q.get("exp"):
        return False, "missing explanation"
    if not q.get("ref"):
        return False, "missing reference"
    return True, "ok"


# ─────────────────────────────────────────────
# 6. HTML generation
# ─────────────────────────────────────────────

def generate_html():
    """Generate the full HTML for the Learning Center."""

    # Build per-chapter data (1-indexed; null at [0] so CH_RANGES[ch] works)
    ch_summaries = [None]
    ch_ranges = [None]
    ch_quizzes = [None]

    # Load global knowledge graph for distractor pools
    with open(DATA_DIR / "knowledge_graph.json", "r", encoding="utf-8") as f:
        kg = json.load(f)
    init_global_pools(kg)

    for ch in range(1, 25):
        ch_data = load_chapter(ch)
        if ch_data is None:
            ch_summaries.append(None)
            ch_ranges.append(None)
            ch_quizzes.append(None)
            continue

        summary = build_chapter_summary(ch_data, ch)
        ch_summaries.append(summary)

        p_start, p_end, pdf_start, pdf_end = get_chapter_page_range(ch_data, ch)
        ch_ranges.append({
            "ch": ch,
            "printed_start": p_start,
            "printed_end": p_end,
            "pdf_start": pdf_start,
            "pdf_end": pdf_end,
        })

        print(f"  Ch {ch}: generating quiz sets...")
        quiz_sets = generate_chapter_quizzes(ch_data, ch)
        # Validate all questions
        for si, s in enumerate(quiz_sets):
            for qi, q in enumerate(s):
                ok, err = validate_question(q, ch, si)
                if not ok:
                    print(f"    [WARN] Ch{ch} Set{si+1} Q{qi+1}: {err}")
        ch_quizzes.append(quiz_sets)
        if len(quiz_sets) > 0 and quiz_sets[0]:
            print(f"    {len(quiz_sets)} sets x {len(quiz_sets[0])} questions")

    # Serialize to JSON
    summary_json = json.dumps(ch_summaries, ensure_ascii=False)
    range_json = json.dumps(ch_ranges, ensure_ascii=False)
    quiz_json = json.dumps(ch_quizzes, ensure_ascii=False)

    # Load HTML template
    template = (Path(__file__).parent / "learning_center_template.html").read_text(encoding="utf-8")
    html = template.replace("{SUMMARY_JSON}", summary_json)
    html = html.replace("{RANGE_JSON}", range_json)
    html = html.replace("{QUIZ_JSON}", quiz_json)
    html = html.replace("{PDF_PATH}", "../data/chapter_pdfs/ch_XX.pdf")

    return html


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Mythos AI — Learning Center Generator")
    print("=" * 60)

    print("\nGenerating chapter data and quizzes...")
    html = generate_html()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n[OK] Learning Center saved: {OUTPUT_FILE.resolve()} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
