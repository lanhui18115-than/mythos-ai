"""
Mythos AI — Crossword Generator (06_crossword_generator.py)

Generates interactive crossword puzzles from the knowledge graph.
Answers drawn from: Greek/Roman names, epithets, places, mythological terms.
Every clue is textbook-grounded with references.

Output: output/crossword.html (browser-ready)
"""

import json
import os
import random
from pathlib import Path
from dotenv import load_dotenv

GRAPH_FILE = Path("data/knowledge_graph.json")
OUTPUT_FILE = Path("output/crossword.html")

random.seed(42)
TARGET_WORDS = 10
MAX_GRID_SIZE = 14
NUM_PUZZLES = 10


def load_kg():
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_answer(name):
    """Clean a name to be crossword-friendly: single word, alpha-only"""
    name = name.split("(")[0].strip()
    cleaned = "".join(c for c in name if c.isalpha() or c == " ")
    cleaned = cleaned.strip()
    if not cleaned or len(cleaned) < 3 or " " in cleaned:
        return None
    return cleaned.upper()


def make_crossword_clue(ans, text):
    """Make a crossword-friendly clue: if the answer word appears in the
    clue text, replace it with a blank so the solver must fill it in."""
    if not text:
        return text
    # Check if answer (case-insensitive) appears as a whole word in the text
    import re
    # Build pattern that matches the answer as a whole word
    pattern = r'\b' + re.escape(ans.lower()) + r'\b'
    if re.search(pattern, text.lower()):
        return re.sub(pattern, '____', text, flags=re.IGNORECASE).strip()
    return text


def _build_greek_names(kg):
    """Build a set of known Greek character names (those with roman_name or epithets)."""
    names = set()
    for c in kg["characters"]:
        if c.get("epithets") or (c.get("roman_name") and str(c.get("roman_name", "")).strip()):
            names.add(c["name"].lower())
    return names


def is_non_greek(c, greek_names):
    """Check if a character is non-Greek/Roman (Egyptian, Mesopotamian, Syrian, etc.)"""
    desc = (c.get("description") or "").lower()

    # 1. Nationality keywords in description
    for kw in ["egyptian", "mesopotamian", "persian", "semitic", "babylonian",
               "sumerian", "akkadian", "hittite", "canaanite", "syrian", "phrygian",
               "assyrian", "chaldean"]:
        if kw in desc:
            return True

    # 2. Non-Greek epic/myth names
    for m in c.get("major_myths", []):
        ml = m.lower()
        if "gilgamesh" in ml or "enuma" in ml:
            return True

    # 3. Characters with roman_name or epithets are definitely Greek
    has_roman = bool(c.get("roman_name") and str(c.get("roman_name", "")).strip())
    has_epithets = len(c.get("epithets", [])) > 0
    if has_roman or has_epithets:
        return False

    # 4. Known non-Greek deity names referenced in description
    #    (catches Nergal/Ereshkigal whose descriptions mention each other)
    for ng in ["nergal", "ereshkigal", "apsu", "tiamat", "marduk",
               "gilgamesh", "enkidu", "inanna", "dumuzi",
               "anu", "enlil", "enki",
               "osiris", "isis", "horus", "anubis", "thoth",
               "mithras", "zoroaster", "ahura",
               "hadad", "baal", "anat", "asherah", "dea syria"]:
        if ng in desc:
            return True

    # 5. For "god"/"goddess" type characters in chapters known to contain
    #    non-Greek content (Near East, Mystery Religions, etc.):
    #    flag if they have no Greek markers and reference no known Greek figure.
    if (not c.get("symbols") and not c.get("major_myths")
            and c.get("type") in ("god", "goddess")
            and c.get("primary_chapter") in (4, 9, 12, 16, 21)):
        refs_greek = any(gname in desc for gname in greek_names)
        if not refs_greek:
            return True

    return False


def build_answer_pool(kg):
    """
    Build a pool of (answer_word, clue_text, reference) tuples.
    """
    pool = []
    used_answers = set()
    greek_names = _build_greek_names(kg)

    # 1. Character names (Greek gods with domains make good clues)
    for c in kg["characters"]:
        if is_non_greek(c, greek_names):
            continue
        ans = clean_answer(c["name"])
        if not ans or " " in ans:
            continue
        if ans in used_answers:
            continue
        # Clue: domain-based
        domains = c.get("domains", [])
        type_label = c.get("type", "")
        roman = c.get("roman_name", "")
        if domains:
            clue = f"Greek {'god' if type_label == 'god' else 'goddess'} of {'/'.join(domains[:2])}"
            ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
            pool.append((ans, clue, f"ch.{ref}" if ref else ""))
            used_answers.add(ans)
        elif roman and roman != c["name"]:
            clue = f"Greek name; Roman equivalent is {roman}"
            ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
            pool.append((ans, clue, f"ch.{ref}" if ref else ""))
            used_answers.add(ans)

    # 2. Roman names
    for c in kg["characters"]:
        if is_non_greek(c, greek_names):
            continue
        roman = c.get("roman_name", "")
        if not roman or roman == c["name"]:
            continue
        ans = clean_answer(roman)
        if not ans or " " in ans:
            continue
        if ans in used_answers:
            continue
        greek_name = c.get("name", "")
        clue = f"Roman name for the Greek {greek_name}"
        ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
        pool.append((ans, clue, f"ch.{ref}" if ref else ""))
        used_answers.add(ans)

    # 3. Epithets
    # Strategy:
    #   - 2+ words: use phrase as clue, character name as answer
    #   - 1 word starting with uppercase (proper noun): keep "Epithet of X"
    #   - 1 word starting with lowercase (common adjective): skip
    for c in kg["characters"]:
        if is_non_greek(c, greek_names):
            continue
        for ep in c.get("epithets", []):
            word_count = len(ep.split())
            if word_count >= 2:
                # Descriptive phrase → clue is the phrase, answer is the character
                ans = clean_answer(c["name"])
                if not ans or " " in ans or ans in used_answers or len(ans) < 4:
                    continue
                clue = ep[0].upper() + ep[1:] if ep else ep
                ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
                pool.append((ans, clue, f"ch.{ref}" if ref else ""))
                used_answers.add(ans)
            else:
                # Single-word epithet
                if ep[0].islower():
                    # Common adjective (black, bright, golden) → skip
                    continue
                ans = clean_answer(ep)
                if not ans or " " in ans or ans in used_answers or len(ans) < 4:
                    continue
                clue = f"Epithet of {c['name']}"
                ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
                pool.append((ans, clue, f"ch.{ref}" if ref else ""))
                used_answers.add(ans)

    # 4. Places (skip places without descriptions to avoid vague clues)
    for p in kg["places"]:
        desc = p.get("description", "")
        if not desc.strip():
            continue
        ans = clean_answer(p["name"])
        if not ans or " " in ans:
            continue
        if ans in used_answers or len(ans) < 4:
            continue
        clue = make_crossword_clue(ans, desc)
        ref = p.get("evidence", [{}])[0].get("chapter", "") if p.get("evidence") else ""
        pool.append((ans, clue, f"ch.{ref}" if ref else ""))
        used_answers.add(ans)

    # 5. Concepts (skip concepts without definitions to avoid vague clues)
    for c in kg["concepts"]:
        defn = c.get("definition", "")
        if not defn.strip():
            continue
        ans = clean_answer(c["name"])
        if not ans or " " in ans:
            continue
        if ans in used_answers or len(ans) < 4:
            continue
        clue = make_crossword_clue(ans, defn)
        ref = c.get("evidence", [{}])[0].get("chapter", "") if c.get("evidence") else ""
        pool.append((ans, clue, f"ch.{ref}" if ref else ""))
        used_answers.add(ans)

    # Remove duplicates by answer
    seen = set()
    unique_pool = []
    for item in pool:
        if item[0] not in seen:
            seen.add(item[0])
            unique_pool.append(item)
    return unique_pool


def place_words(words, max_size=MAX_GRID_SIZE):
    """
    Compact crossword placement algorithm.
    Places words on a grid, requiring every word after the first
    to intersect at least one existing word.
    Returns (grid, placed_words) where grid is list of strings
    and placed_words is list of (word, row, col, is_across, clue, ref)
    """
    sorted_words = sorted(words, key=lambda w: -len(w[0]))
    grid = [[" " for _ in range(max_size)] for _ in range(max_size)]
    placed = []
    start_row, start_col = max_size // 2, max_size // 2

    for idx, (word, clue, ref) in enumerate(sorted_words):
        w = word.upper()
        best_pos = None
        best_score = -1

        if idx == 0:
            # First word: place horizontally near center
            r, c = start_row, start_col - len(w) // 2
            if c < 0: c = 0
            if c + len(w) > max_size: c = max_size - len(w)
            if can_place(grid, w, r, c, True, placed, max_size):
                for i, ch in enumerate(w):
                    grid[r][c + i] = ch
                placed.append((w, r, c, True, clue, ref))
            continue

        # Count intersections for a candidate placement
        def count_intersections(r, c, across):
            cnt = 0
            for pi, pch in enumerate(w):
                pr = r + (pi if not across else 0)
                pc = c + (pi if across else 0)
                for ex in placed:
                    exw, exr, exc, exa, _, _ = ex
                    if exa:
                        if pr == exr and exc <= pc < exc + len(exw):
                            if grid[pr][pc] == exw[pc - exc]:
                                cnt += 1
                    else:
                        if pc == exc and exr <= pr < exr + len(exw):
                            if grid[pr][pc] == exw[pr - exr]:
                                cnt += 1
            return cnt

        # Try to intersect with existing words (required for all words after first)
        for existing in placed:
            ew, er, ec, ea, _, _ = existing
            for i, ch in enumerate(w):
                for j, ech in enumerate(ew):
                    if ch == ech:
                        if ea:
                            r, c = er - i, ec + j
                        else:
                            r, c = er + j, ec - i

                        if can_place(grid, w, r, c, not ea, placed, max_size):
                            icnt = count_intersections(r, c, not ea)
                            score = icnt * 20
                            if r >= 1 and c >= 1 and r + len(w) < max_size - 1 and c + len(w) < max_size - 1:
                                score += 5
                            if score > best_score:
                                best_score = score
                                best_pos = (r, c, not ea)

        if best_pos is None and idx <= 2:
            # Only the 2nd/3rd word may fall back to random placement
            for attempt in range(100):
                r = random.randint(2, max_size - 3)
                c = random.randint(2, max_size - 3)
                across = random.choice([True, False])
                if can_place(grid, w, r, c, across, placed, max_size):
                    icnt = count_intersections(r, c, across)
                    if icnt > 0:
                        best_pos = (r, c, across)
                        break

        if best_pos:
            r, c, across = best_pos
            if across:
                for i, ch in enumerate(w):
                    grid[r][c + i] = ch
            else:
                for i, ch in enumerate(w):
                    grid[r + i][c] = ch
            placed.append((w, r, c, across, clue, ref))

    return grid, placed


def can_place(grid, word, row, col, across, placed, max_size):
    """Check if word can be placed at (row, col) in given direction"""
    if across:
        if col < 0 or col + len(word) > max_size:
            return False
        if row < 0 or row >= max_size:
            return False
        for i, ch in enumerate(word):
            r, c = row, col + i
            existing = grid[r][c]
            if existing != " " and existing != ch:
                return False
            # Check neighbors (no adjacent parallel words)
            if existing == " ":
                if r > 0 and grid[r - 1][c] != " ":
                    # Make sure it's at an intersection
                    pass
                if r < max_size - 1 and grid[r + 1][c] != " ":
                    pass
            # Ensure no adjacent same-direction
            if i == 0 and c > 0 and grid[r][c - 1] != " ":
                return False
            if i == len(word) - 1 and c < max_size - 1 and grid[r][c + 1] != " ":
                return False
    else:
        if row < 0 or row + len(word) > max_size:
            return False
        if col < 0 or col >= max_size:
            return False
        for i, ch in enumerate(word):
            r, c = row + i, col
            existing = grid[r][c]
            if existing != " " and existing != ch:
                return False
            if i == 0 and r > 0 and grid[r - 1][c] != " ":
                return False
            if i == len(word) - 1 and r < max_size - 1 and grid[r + 1][c] != " ":
                return False

    return True


def trim_grid(grid, placed):
    """Remove empty rows/columns from grid"""
    if not placed:
        return grid, placed

    min_r, max_r = MAX_GRID_SIZE, 0
    min_c, max_c = MAX_GRID_SIZE, 0
    for w, r, c, across, clue, ref in placed:
        if across:
            min_r = min(min_r, r)
            max_r = max(max_r, r)
            min_c = min(min_c, c)
            max_c = max(max_c, c + len(w) - 1)
        else:
            min_r = min(min_r, r)
            max_r = max(max_r, r + len(w) - 1)
            min_c = min(min_c, c)
            max_c = max(max_c, c)

    # Add padding
    min_r = max(0, min_r - 1)
    min_c = max(0, min_c - 1)
    max_r = min(MAX_GRID_SIZE - 1, max_r + 1)
    max_c = min(MAX_GRID_SIZE - 1, max_c + 1)

    trimmed = []
    for r in range(min_r, max_r + 1):
        row = grid[r][min_c:max_c + 1]
        trimmed.append(row)

    # Adjust placed positions
    adjusted = []
    for w, r, c, across, clue, ref in placed:
        adjusted.append((w, r - min_r, c - min_c, across, clue, ref))

    return trimmed, adjusted


def build_crossword_index(placed, trimmed):
    """
    Build index of across/down clues with numbered positions.
    Returns (grid_numbers, clues) where grid_numbers is 2D array with numbers or 0,
    and clues is {across: [(num, clue, answer, ref)], down: [...]}
    """
    height = len(trimmed)
    width = len(trimmed[0]) if height > 0 else 0
    numbers = [[0 for _ in range(width)] for _ in range(height)]

    across_clues = []
    down_clues = []
    cell_to_num = {}
    next_num = 1

    # Give numbers to cells that start a word
    for w, r, c, across, clue, ref in placed:
        key = (r, c)
        if key not in cell_to_num:
            cell_to_num[key] = next_num
            numbers[r][c] = next_num
            next_num += 1
        num = cell_to_num[key]
        if across:
            across_clues.append((num, clue, w, ref))
        else:
            down_clues.append((num, clue, w, ref))

    across_clues.sort(key=lambda x: x[0])
    down_clues.sort(key=lambda x: x[0])

    return numbers, {"across": across_clues, "down": down_clues}


def _find_kg_context(word, kg):
    """Find background description for a given answer word across KG categories."""
    word_lower = word.lower()
    for c in kg["characters"]:
        if c["name"].lower() == word_lower:
            return c.get("description") or ""
    for c in kg["characters"]:
        roman = c.get("roman_name", "")
        if roman and roman.lower() == word_lower:
            return c.get("description") or ""
    for p in kg.get("places", []):
        if p["name"].lower() == word_lower:
            return p.get("description") or ""
    for c in kg.get("concepts", []):
        if c["name"].lower() == word_lower:
            return c.get("definition") or ""
    return ""


def _get_chapter(word, kg):
    """Get primary chapter for any answer word (character/place/concept/epithet)."""
    wl = word.lower()
    for c in kg["characters"]:
        if c["name"].lower() == wl:
            pc = c.get("primary_chapter")
            if pc is not None: return str(pc)
    for c in kg["characters"]:
        roman = c.get("roman_name", "")
        if roman and roman.lower() == wl:
            pc = c.get("primary_chapter")
            if pc is not None: return str(pc)
    for p in kg.get("places", []):
        if p["name"].lower() == wl:
            pc = p.get("primary_chapter")
            if pc is not None: return str(pc)
            ev = p.get("evidence", [{}])
            if ev: return str(ev[0].get("chapter", "?"))
    for c in kg.get("concepts", []):
        if c["name"].lower() == wl:
            pc = c.get("primary_chapter")
            if pc is not None: return str(pc)
            ev = c.get("evidence", [{}])
            if ev: return str(ev[0].get("chapter", "?"))
    return "?"


def build_pool_by_chapter(pool, kg):
    """Group answer pool by chapter number.
    Returns dict: {chapter: [(ans, clue, ref), ...]}
    """
    by_ch = {}
    for ans, clue, ref in pool:
        ch = _get_chapter(ans, kg)
        if ch not in by_ch:
            by_ch[ch] = []
        by_ch[ch].append((ans, clue, ref))
    return by_ch


def generate_puzzles(pool, target=TARGET_WORDS, max_puzzles=NUM_PUZZLES,
                     max_size=MAX_GRID_SIZE, attempts_mult=5):
    """Generate a set of crossword puzzles from a given answer pool.
    Returns list of dicts with trimmed/numbers/clues/placed keys.
    """
    pool = [p for p in pool if 4 <= len(p[0]) <= max_size]
    result = []
    for _ in range(max_puzzles * attempts_mult):
        if len(result) >= max_puzzles:
            break
        random.shuffle(pool)
        selected = pool[:target + 3]
        grid, placed = place_words(selected, max_size)
        if not placed:
            continue
        across = sum(1 for _, _, _, a, _, _ in placed if a)
        down = len(placed) - across
        if len(placed) < target - 3 or across < 3 or down < 3:
            continue
        trimmed, adjusted = trim_grid(grid, placed)
        numbers, clues = build_crossword_index(adjusted, trimmed)
        ans_set = frozenset(w for w, _, _, _, _, _ in adjusted)
        if any(ans_set == frozenset(w for w, _, _, _, _, _ in p['placed']) for p in result):
            continue
        if len(trimmed) > max_size or len(trimmed[0]) > max_size:
            continue
        result.append({
            'trimmed': trimmed,
            'numbers': numbers,
            'clues': clues,
            'placed': adjusted,
        })
    return result


def _apply_llm(puzzles, kg, enhancer, explanations):
    """Apply LLM clue enhancement and explanation generation to all puzzles."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Collect unique (word, clue, context) tuples
    unique = {}
    for p in puzzles:
        for w, _, _, _, clue, _ in p['placed']:
            if w not in unique:
                unique[w] = (w, clue, _find_kg_context(w, kg))

    # Step A: Enhance clues (parallel)
    print(f"[LLM] 正在优化 {len(unique)} 条线索...")
    enhancements = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut = {ex.submit(enhancer.enhance_clue, w, cl, ctx): w for w, cl, ctx in unique.values()}
        for f in as_completed(fut):
            w = fut[f]
            try:
                new_clue = f.result()
                if new_clue != unique[w][1]:
                    enhancements[w] = new_clue
            except Exception as e:
                print(f"  [LLM] enhance_clue failed for {w}: {e}")

    # Apply enhancements to all puzzle instances
    for w, new_clue in enhancements.items():
        for p in puzzles:
            p['placed'] = [(ww, r, c, a, new_clue if ww == w else cl, ref)
                           for ww, r, c, a, cl, ref in p['placed']]
            for dir_key in ['across', 'down']:
                p['clues'][dir_key] = [(num, new_clue if ans == w else cl, ans, ref)
                                       for num, cl, ans, ref in p['clues'][dir_key]]
    print(f"[LLM] 已优化 {len(enhancements)}/{len(unique)} 条线索")

    # Step B: Generate explanations (parallel)
    print(f"[LLM] 正在生成 {len(unique)} 条解析...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut = {}
        for w, cl, ctx in unique.values():
            fut[ex.submit(enhancer.generate_explanation, w, cl, ctx)] = w
        for f in as_completed(fut):
            w = fut[f]
            try:
                exp = f.result()
                if exp:
                    explanations[w] = exp
            except Exception as e:
                print(f"  [LLM] generate_explanation failed for {w}: {e}")
    print(f"[LLM] 已生成 {len(explanations)} 条解析")


def generate_html(random_puzzles, chapter_puzzles, explanations=None):
    """Generate HTML with both random and per-chapter puzzles embedded."""
    first = random_puzzles[0]

    def build_grid_html(trimmed, numbers):
        h, w = len(trimmed), len(trimmed[0]) if trimmed else 0
        rows = []
        for r in range(h):
            cells = []
            for c in range(w):
                ch = trimmed[r][c]
                num = numbers[r][c]
                if ch == " ":
                    cells.append('<td class="b"></td>')
                else:
                    n_h = f'<span class="num">{num}</span>' if num else ""
                    cells.append(f'<td class="cell" data-r="{r}" data-c="{c}">{n_h}<span class="l" id="l-{r}-{c}"></span></td>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(rows)

    def build_clues_html(clues):
        across = "".join(
            f"<div class='clue'><span class='cn'>{num}.</span> {clue}</div>"
            for num, clue, ans, ref in clues["across"]
        )
        down = "".join(
            f"<div class='clue'><span class='cn'>{num}.</span> {clue}</div>"
            for num, clue, ans, ref in clues["down"]
        )
        return across, down

    grid_html = build_grid_html(first["trimmed"], first["numbers"])
    across_html, down_html = build_clues_html(first["clues"])

    # Build JS puzzle arrays for both modes
    def _fmt_puzzle(p):
        return {
            "solution": p["trimmed"],
            "clueData": p["clues"],
            "numData": p["numbers"],
            "height": len(p["trimmed"]),
            "width": len(p["trimmed"][0]) if p["trimmed"] else 0,
        }

    random_js = [_fmt_puzzle(p) for p in random_puzzles]
    chapter_js = {}
    for ch in sorted(chapter_puzzles.keys(), key=lambda x: int(x) if x.isdigit() and x != '?' else 999):
        chapter_js[ch] = [_fmt_puzzle(p) for p in chapter_puzzles[ch]]

    # Build chapter options for the <select>
    chapter_options = ""
    for ch in sorted(chapter_puzzles.keys(), key=lambda x: int(x) if x.isdigit() and x != '?' else 999):
        label = "其他" if ch == "?" else f"第 {ch} 章"
        chapter_options += f'<option value="{ch}">{label}</option>\n    '

    random_json = json.dumps(random_js, ensure_ascii=False)
    chapter_json = json.dumps(chapter_js, ensure_ascii=False)
    explanations_json = json.dumps(explanations or {}, ensure_ascii=False) if explanations else "{}"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mythos AI — 填字游戏</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',sans-serif; background:#0a0a1a; color:#eee; padding:20px; }}
  .container {{ max-width:1100px; margin:0 auto; }}
  h1 {{ color:#F5D742; font-size:24px; margin-bottom:4px; }}
  .subtitle {{ color:#666; font-size:13px; margin-bottom:20px; }}
  .layout {{ display:flex; gap:24px; flex-wrap:wrap; }}
  .grid-wrap {{ flex-shrink:0; }}
  table {{ border-collapse:collapse; }}
  td {{ width:32px; height:32px; text-align:center; vertical-align:middle; font-size:16px; position:relative; }}
  td.cell {{ border:1px solid #2a2a4a; background:#111128; cursor:pointer; }}
  td.cell.focused {{ background:#1a1a4e; border-color:#F5D742; }}
  td.cell.filled {{ background:#1a1a3e; }}
  td.cell.correct {{ background:rgba(46,204,113,0.2); border-color:#2ecc71; }}
  td.cell.wrong {{ background:rgba(231,76,60,0.2); border-color:#e74c3c; }}
  td.b {{ background:#0a0a1a; border:none; }}
  .num {{ position:absolute; top:1px; left:2px; font-size:9px; color:#888; line-height:1; }}
  .l {{ font-weight:bold; color:#eee; font-size:16px; }}
  td.correct .l {{ color:#2ecc71; }}
  td.wrong .l {{ color:#e74c3c; }}
  .clues {{ flex:1; min-width:300px; }}
  .clues h3 {{ color:#F5D742; font-size:16px; margin:12px 0 8px; }}
  .clue {{ padding:4px 0; font-size:13px; color:#bbb; display:block; word-wrap:break-word; overflow-wrap:break-word; }}
  .clue .cn {{ color:#F5D742; font-weight:bold; min-width:24px; display:inline; }}
  .clue.done {{ color:#555; text-decoration:line-through; }}
  .controls {{ margin-bottom:16px; display:flex; gap:8px; flex-wrap:wrap; }}
  .controls button {{ padding:8px 16px; border:1px solid #333; background:#111128; color:#ccc; border-radius:6px; cursor:pointer; font-size:13px; }}
  .controls button:hover {{ background:#F5D742; color:#111; }}
  .controls button.primary {{ background:#F5D742; color:#111; font-weight:bold; }}
  .status {{ font-size:13px; color:#888; margin-bottom:12px; }}
  .mode-bar {{ display:flex; gap:10px; align-items:center; margin-bottom:12px; }}
  .mode-bar .mode-btn {{ padding:6px 14px; border:1px solid #333; background:#111128; color:#888; border-radius:6px; cursor:pointer; font-size:12px; }}
  .mode-bar .mode-btn:hover {{ border-color:#F5D742; color:#F5D742; }}
  .mode-bar .mode-btn.active {{ background:#F5D742; color:#111; font-weight:bold; border-color:#F5D742; }}
  .mode-bar select {{ padding:5px 10px; border:1px solid #333; background:#111128; color:#ccc; border-radius:6px; font-size:12px; cursor:pointer; }}
  .mode-bar select:focus {{ outline:none; border-color:#F5D742; }}
  .current-clue {{ background:#111128; border:1px solid #2a2a4a; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:14px; min-height:44px; display:flex; align-items:center; gap:10px; }}
  .current-clue .dir-badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold; }}
  .current-clue .dir-badge.across {{ background:rgba(52,152,219,0.2); color:#3498db; border:1px solid rgba(52,152,219,0.3); }}
  .current-clue .dir-badge.down {{ background:rgba(231,76,60,0.2); color:#e74c3c; border:1px solid rgba(231,76,60,0.3); }}
  .current-clue .clue-num {{ color:#F5D742; font-weight:bold; }}
  .current-clue .clue-text {{ color:#ddd; word-wrap:break-word; overflow-wrap:break-word; flex:1; }}
  .current-clue .clue-ref {{ color:#555; font-size:11px; margin-left:auto; white-space:nowrap; }}
  .explanation {{ background:#0d0d2a; border:1px solid #2a2a5a; border-radius:6px; padding:8px 12px; margin-top:8px; font-size:13px; color:#aaa; line-height:1.6; }}
  .explanation .exp-toggle {{ color:#F5D742; cursor:pointer; font-size:12px; user-select:none; }}
  .explanation .exp-toggle:hover {{ text-decoration:underline; }}
  .explanation .exp-text {{ margin-top:4px; display:none; }}
  .explanation .exp-text.visible {{ display:block; }}
  td.cell.highlight {{ background:#1a1a5e; border-color:#4a4a8a; }}
  td.cell.highlight-across {{ background:rgba(52,152,219,0.15); border-color:rgba(52,152,219,0.4); }}
  td.cell.highlight-down {{ background:rgba(231,76,60,0.15); border-color:rgba(231,76,60,0.4); }}
  .help-section {{ margin-top:16px; background:#111128; border:1px solid #2a2a4a; border-radius:8px; overflow:hidden; }}
  .help-toggle {{ padding:8px 14px; cursor:pointer; font-size:12px; color:#888; display:flex; align-items:center; gap:6px; user-select:none; }}
  .help-toggle:hover {{ color:#F5D742; }}
  .help-toggle .arrow {{ display:inline-block; transition:transform 0.2s; }}
  .help-toggle .arrow.open {{ transform:rotate(90deg); }}
  .help-body {{ display:none; padding:8px 14px 14px; border-top:1px solid #2a2a4a; font-size:12px; color:#999; line-height:1.8; }}
  .help-body.open {{ display:block; }}
  .help-body kbd {{ display:inline-block; padding:1px 6px; background:#1a1a3e; border:1px solid #333; border-radius:3px; font-size:11px; color:#ddd; font-family:inherit; }}
  .help-body .row {{ display:flex; gap:16px; flex-wrap:wrap; }}
  .help-body .col {{ flex:1; min-width:200px; }}
  .help-body .col h4 {{ color:#F5D742; font-size:13px; margin:6px 0 4px; }}
  .puzzle-counter {{ font-size:12px; color:#555; margin-left:auto; }}
</style>
</head>
<body>
<div class="container">
  <h1>Mythos AI — 填字游戏</h1>
  <div class="subtitle">所有线索均基于教材《Classical Mythology》生成</div>
  <div class="mode-bar">
    <button class="mode-btn active" onclick="switchMode('random')" id="mode-random">随机模式</button>
    <button class="mode-btn" onclick="switchMode('chapter')" id="mode-chapter">章节模式</button>
    <select id="chapter-select" style="display:none" onchange="switchChapter(this.value)">
      {chapter_options}
    </select>
  </div>
  <div class="controls">
    <button class="primary" onclick="checkAnswers()">检查答案</button>
    <button onclick="revealAnswer()">显示一格</button>
    <button onclick="revealAll()">显示全部</button>
    <button onclick="resetPuzzle()">重新开始</button>
    <button onclick="newPuzzle()">新题目</button>
  </div>
  <div class="current-clue" id="current-clue">点击格子开始填词 — 按 <kbd>Tab</kbd> 切换方向</div>
  <div class="explanation" id="explanation">
    <span class="exp-toggle" onclick="toggleExplanation()">📖 查看神话解析</span>
    <div class="exp-text" id="exp-text"></div>
  </div>
  <div class="status" id="status">已填: 0 / 0 <span class="puzzle-counter" id="puzzle-counter" style="float:right"></span></div>
  <div class="layout">
    <div class="grid-wrap">
      <table id="grid">
        {grid_html}
      </table>
    </div>
    <div class="clues">
      <h3>横向 Across</h3>
      <div id="across">{across_html}</div>
      <h3>竖向 Down</h3>
      <div id="down">{down_html}</div>
    </div>
  </div>
  <div class="help-section">
    <div class="help-toggle" onclick="this.querySelector('.arrow').classList.toggle('open');this.nextElementSibling.classList.toggle('open')">
      <span class="arrow">&#9654;</span> 操作说明 &amp; 按键指南
    </div>
    <div class="help-body">
      <div class="row">
        <div class="col">
          <h4>游戏规则</h4>
          <div>根据线索提示，在网格中填入正确的字母，组成神话相关的单词。</div>
          <div>所有线索均基于教材《Classical Mythology》生成，可追溯具体章节。</div>
          <div>填写完成后点击"检查答案"验证是否正确。</div>
        </div>
        <div class="col">
          <h4>按键操作</h4>
          <div><kbd>Tab</kbd> 切换横向/竖向方向</div>
          <div><kbd>&larr;</kbd> <kbd>&rarr;</kbd> <kbd>&uarr;</kbd> <kbd>&darr;</kbd> 移动焦点</div>
          <div><kbd>A</kbd>-<kbd>Z</kbd> 输入字母</div>
          <div><kbd>Backspace</kbd> <kbd>Delete</kbd> 删除字母</div>
          <div><kbd>Enter</kbd> 跳转到下一单词开头</div>
        </div>
        <div class="col">
          <h4>按钮功能</h4>
          <div><strong>检查答案</strong> — 标记正确/错误格子</div>
          <div><strong>显示一格</strong> — 揭示当前格答案</div>
          <div><strong>显示全部</strong> — 揭示所有答案</div>
          <div><strong>重新开始</strong> — 清空所有填写</div>
          <div><strong>新题目</strong> — 加载新填字游戏</div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
var randomPuzzles = {random_json};
var chapterPuzzles = {chapter_json};
var puzzles = randomPuzzles;
var explanations = {explanations_json};
var puzzleIndex = 0;
var puzzle = puzzles[0];
var SOLUTION = puzzle.solution;
var clueData = puzzle.clueData;
var numData = puzzle.numData;
var height = puzzle.height;
var width = puzzle.width;

var direction = 'across';
var userGrid = {{}};
var focusR = -1, focusC = -1;
var revealed = {{}};

function rebuildGrid(p) {{
  var html = '';
  for (var r = 0; r < p.height; r++) {{
    html += '<tr>';
    for (var c = 0; c < p.width; c++) {{
      var ch = p.solution[r][c];
      var num = p.numData[r][c];
      if (ch === ' ') {{
        html += '<td class="b"></td>';
      }} else {{
        var nHtml = num ? '<span class="num">' + num + '</span>' : '';
        html += '<td class="cell" data-r="' + r + '" data-c="' + c + '">' + nHtml + '<span class="l" id="l-' + r + '-' + c + '"></span></td>';
      }}
    }}
    html += '</tr>';
  }}
  document.getElementById('grid').innerHTML = html;
}}

function rebuildClues(p) {{
  var ah = '', dh = '';
  for (var i = 0; i < p.clueData.across.length; i++) {{
    var c = p.clueData.across[i];
    ah += '<div class="clue"><span class="cn">' + c[0] + '.</span> ' + c[1] + '</div>';
  }}
  document.getElementById('across').innerHTML = ah;
  for (var i = 0; i < p.clueData.down.length; i++) {{
    var c = p.clueData.down[i];
    dh += '<div class="clue"><span class="cn">' + c[0] + '.</span> ' + c[1] + '</div>';
  }}
  document.getElementById('down').innerHTML = dh;
}}

function loadPuzzle(idx) {{
  puzzleIndex = idx;
  puzzle = puzzles[idx];
  SOLUTION = puzzle.solution;
  clueData = puzzle.clueData;
  numData = puzzle.numData;
  height = puzzle.height;
  width = puzzle.width;
  rebuildGrid(puzzle);
  rebuildClues(puzzle);
  userGrid = {{}};
  revealed = {{}};
  focusR = -1;
  focusC = -1;
  direction = 'across';
  document.getElementById('status').textContent = '已填: 0 / 0 | 方向: 横向';
  document.getElementById('current-clue').innerHTML = '点击格子开始填词 — 按 <kbd>Tab</kbd> 切换方向';
  document.getElementById('exp-text').classList.remove('visible');
  document.getElementById('exp-text').textContent = '';
  updatePuzzleCounter();
  init();
}}

function getWordCells(r, c, dir) {{
  var cells = [];
  if (dir === 'across') {{
    var start = c;
    while (start > 0 && SOLUTION[r][start - 1] !== ' ') start--;
    var end = c;
    while (end < width - 1 && SOLUTION[r][end + 1] !== ' ') end++;
    for (var cc = start; cc <= end; cc++) cells.push({{ r: r, c: cc }});
  }} else {{
    var start = r;
    while (start > 0 && SOLUTION[start - 1][c] !== ' ') start--;
    var end = r;
    while (end < height - 1 && SOLUTION[end + 1][c] !== ' ') end++;
    for (var rr = start; rr <= end; rr++) cells.push({{ r: rr, c: c }});
  }}
  return cells;
}}

function findClue(num, dir) {{
  var clues = clueData[dir];
  for (var i = 0; i < clues.length; i++) {{
    if (clues[i][0] === num) return clues[i];
  }}
  return null;
}}

function getClueNumber(r, c, dir) {{
  if (dir === 'across') {{
    var start = c;
    while (start > 0 && SOLUTION[r][start - 1] !== ' ') start--;
    var num = numData[r][start];
    return (num && findClue(num, 'across')) ? num : 0;
  }} else {{
    var rr = r;
    while (rr >= 0 && SOLUTION[rr][c] !== ' ') {{
      var num = numData[rr][c];
      if (num && findClue(num, 'down')) return num;
      rr--;
    }}
    return 0;
  }}
}}

function updateCurrentClue() {{
  var el = document.getElementById('current-clue');
  if (focusR < 0 || focusC < 0) {{
    el.innerHTML = '点击格子开始填词 — 按 <kbd>Tab</kbd> 切换方向';
    return;
  }}
  var dirs = [direction, direction === 'across' ? 'down' : 'across'];
  for (var di = 0; di < dirs.length; di++) {{
    var d = dirs[di];
    var num = getClueNumber(focusR, focusC, d);
    if (!num) continue;
    var clue = findClue(num, d);
    if (!clue) continue;
    var dirLabel = d === 'across' ? '横向' : '竖向';
    var numRef = clue[3] ? '<span class="clue-ref">' + clue[3] + '</span>' : '';
    var ansHint = '';
    var ans = clue[2];
    if (ans) {{
      var dots = '';
      for (var bi = 0; bi < ans.length; bi++) dots += '\u00B7 ';
      ansHint = ' <span style="color:#555;font-size:12px">(' + ans.length + ' \u5B57\u6BCD: ' + dots.trim() + ')</span>';
    }}
    el.innerHTML = '<span class="dir-badge ' + d + '">' + dirLabel + '</span> <span class="clue-num">' + clue[0] + '.</span> <span class="clue-text">' + clue[1] + '</span>' + ansHint + ' ' + numRef;
    if (d !== direction) {{ direction = d; }}
    updateExplanation();
    return;
  }}
      el.innerHTML = '<span style="color:#666;font-size:13px">此格无对应线索</span>';
  updateExplanation();
}}

function updatePuzzleCounter() {{
  var total = puzzles.length;
  var el = document.getElementById('puzzle-counter');
  if (el) el.textContent = '第 ' + (puzzleIndex + 1) + '/' + total + ' 题';
}}

function toggleDirection() {{
  direction = direction === 'across' ? 'down' : 'across';
  updateCurrentClue();
  render();
}}

var currentExplanationAns = '';
var currentExplanationRaw = '';

function toggleExplanation() {{
  var el = document.getElementById('exp-text');
  if (el.classList.contains('visible')) {{
    el.classList.remove('visible');
  }} else {{
    if (currentExplanationAns) {{
      el.textContent = '答案: ' + currentExplanationAns + '\\n' + currentExplanationRaw;
    }}
    el.classList.add('visible');
  }}
}}

function updateExplanation() {{
  var expText = document.getElementById('exp-text');
  if (focusR < 0 || focusC < 0) {{ expText.classList.remove('visible'); return; }}
  var dirs = [direction, direction === 'across' ? 'down' : 'across'];
  for (var di = 0; di < dirs.length; di++) {{
    var d = dirs[di];
    var num = getClueNumber(focusR, focusC, d);
    if (!num) continue;
    var clue = findClue(num, d);
    if (!clue) continue;
    var ans = clue[2];
    var exp = explanations[ans];
    if (exp) {{
      currentExplanationAns = ans;
      currentExplanationRaw = exp;
      expText.textContent = exp;
      return;
    }}
  }}
  currentExplanationAns = '';
  currentExplanationRaw = '';
  expText.classList.remove('visible');
}}

function init() {{
  for (var r = 0; r < height; r++) {{
    for (var c = 0; c < width; c++) {{
      var ch = SOLUTION[r][c];
      if (ch !== " ") {{
        userGrid[r + "," + c] = "";
      }}
    }}
  }}
  render();
}}

function render() {{
  var highlightCells = {{}};
  var hlType = '';
  if (focusR >= 0 && focusC >= 0) {{
    var wordCells = getWordCells(focusR, focusC, direction);
    hlType = 'highlight-' + direction;
    wordCells.forEach(function (p) {{ highlightCells[p.r + ',' + p.c] = true; }});
  }}
  var cells = document.querySelectorAll('td.cell');
  cells.forEach(function (td) {{
    var r = parseInt(td.getAttribute('data-r'));
    var c = parseInt(td.getAttribute('data-c'));
    var key = r + ',' + c;
    var span = td.querySelector('.l');
    var val = userGrid[key] || '';
    span.textContent = revealed[key] ? SOLUTION[r][c] : val;
    td.classList.remove('focused', 'filled', 'correct', 'wrong', 'highlight', 'highlight-across', 'highlight-down');
    if (r === focusR && c === focusC) td.classList.add('focused');
    if (highlightCells[key]) td.classList.add('highlight', hlType);
    if (val) td.classList.add('filled');
  }});
  updateStatus();
  updateCurrentClue();
}}

function updateStatus() {{
  var total = Object.keys(userGrid).length;
  var filled = Object.values(userGrid).filter(function (v) {{ return v; }}).length;
  document.getElementById('status').textContent = '已填: ' + filled + ' / ' + total + ' | 方向: ' + (direction === 'across' ? '横向' : '竖向');
}}

function moveFocus(r, c) {{
  if (r >= 0 && r < height && c >= 0 && c < width && SOLUTION[r][c] !== " ") {{
    focusR = r;
    focusC = c;
    render();
    var el = document.getElementById('l-' + r + '-' + c);
    if (el) el.focus && el.focus();
  }}
}}

document.addEventListener('keydown', function (e) {{
  if (focusR < 0 || focusC < 0) return;
  var key = e.key;
  if (key === 'Tab') {{
    e.preventDefault();
    toggleDirection();
    return;
  }}
  if (key === 'Enter') {{
    e.preventDefault();
    toggleDirection();
    var num = getClueNumber(focusR, focusC, direction);
    if (num) {{
      var clue = findClue(num, direction);
      if (clue) {{
        var ans = clue[2];
        if (direction === 'across') {{
          var start = focusC;
          while (start > 0 && SOLUTION[focusR][start - 1] !== ' ') start--;
          for (var cc = start; cc < start + ans.length; cc++) {{
            if (!userGrid[focusR + ',' + cc]) {{ moveFocus(focusR, cc); break; }}
          }}
        }} else {{
          var start = focusR;
          while (start > 0 && SOLUTION[start - 1][focusC] !== ' ') start--;
          for (var rr = start; rr < start + ans.length; rr++) {{
            if (!userGrid[rr + ',' + focusC]) {{ moveFocus(rr, focusC); break; }}
          }}
        }}
      }}
    }}
    return;
  }}
  var uk = e.key.toUpperCase();
  if (uk === 'ARROWUP') {{ e.preventDefault(); moveFocus(focusR - 1, focusC); return; }}
  if (uk === 'ARROWDOWN') {{ e.preventDefault(); moveFocus(focusR + 1, focusC); return; }}
  if (uk === 'ARROWLEFT') {{ e.preventDefault(); moveFocus(focusR, focusC - 1); return; }}
  if (uk === 'ARROWRIGHT') {{ e.preventDefault(); moveFocus(focusR, focusC + 1); return; }}
  if (e.ctrlKey || e.metaKey) return;
  if (uk.length === 1 && uk >= 'A' && uk <= 'Z') {{
    var key2 = focusR + ',' + focusC;
    if (SOLUTION[focusR][focusC] !== " ") {{
      userGrid[key2] = uk;
      if (direction === 'across') {{
        var nc = focusC + 1;
        while (nc < width && SOLUTION[focusR][nc] === " ") nc++;
        if (nc < width) moveFocus(focusR, nc);
      }} else {{
        var nr = focusR + 1;
        while (nr < height && SOLUTION[nr][focusC] === " ") nr++;
        if (nr < height) moveFocus(nr, focusC);
      }}
      render();
    }}
  }}
  if (uk === 'BACKSPACE' || uk === 'DELETE') {{
    var key2 = focusR + ',' + focusC;
    userGrid[key2] = '';
    if (direction === 'across') {{
      var pc = focusC - 1;
      while (pc >= 0 && SOLUTION[focusR][pc] === " ") pc--;
      if (pc >= 0) moveFocus(focusR, pc); else render();
    }} else {{
      var pr = focusR - 1;
      while (pr >= 0 && SOLUTION[pr][focusC] === " ") pr--;
      if (pr >= 0) moveFocus(pr, focusC); else render();
    }}
  }}
}});

document.getElementById('grid').addEventListener('click', function (e) {{
  var td = e.target.closest('td.cell');
  if (!td) return;
  var r = parseInt(td.getAttribute('data-r'));
  var c = parseInt(td.getAttribute('data-c'));
  if (r === focusR && c === focusC) {{
    toggleDirection();
  }} else {{
    var hasAcross = getClueNumber(r, c, 'across') && findClue(getClueNumber(r, c, 'across'), 'across');
    var hasDown = getClueNumber(r, c, 'down') && findClue(getClueNumber(r, c, 'down'), 'down');
    if (hasAcross && !hasDown) direction = 'across';
    else if (hasDown && !hasAcross) direction = 'down';
    moveFocus(r, c);
  }}
}});

function checkAnswers() {{
  var cells = document.querySelectorAll('td.cell');
  var allCorrect = true;
  cells.forEach(function (td) {{
    var r = parseInt(td.getAttribute('data-r'));
    var c = parseInt(td.getAttribute('data-c'));
    var key = r + ',' + c;
    var userVal = (userGrid[key] || '').toUpperCase();
    var solVal = SOLUTION[r][c];
    td.classList.remove('correct', 'wrong');
    if (userVal) {{
      if (userVal === solVal) {{
        td.classList.add('correct');
      }} else {{
        td.classList.add('wrong');
        allCorrect = false;
      }}
    }}
  }});
  if (allCorrect) {{
    document.getElementById('status').textContent = '🎉 全部正确！';
  }}
}}

function revealAnswer() {{
  if (focusR < 0 || focusC < 0) return;
  var key = focusR + ',' + focusC;
  revealed[key] = true;
  render();
}}

function revealAll() {{
  for (var r = 0; r < height; r++) {{
    for (var c = 0; c < width; c++) {{
      if (SOLUTION[r][c] !== " ") {{
        revealed[r + ',' + c] = true;
      }}
    }}
  }}
  render();
}}

function resetPuzzle() {{
  for (var key in userGrid) userGrid[key] = '';
  revealed = {{}};
  var cells = document.querySelectorAll('td.cell');
  cells.forEach(function (td) {{ td.classList.remove('correct', 'wrong', 'filled'); }});
  render();
}}

function newPuzzle() {{
  loadPuzzle((puzzleIndex + 1) % puzzles.length);
}}

var mode = 'random';

function switchMode(newMode) {{
  if (newMode === mode) return;
  mode = newMode;
  document.getElementById('mode-random').classList.toggle('active', mode === 'random');
  document.getElementById('mode-chapter').classList.toggle('active', mode === 'chapter');
  var chSel = document.getElementById('chapter-select');
  if (mode === 'random') {{
    puzzles = randomPuzzles;
    chSel.style.display = 'none';
  }} else {{
    chSel.style.display = 'inline-block';
    var ch = chSel.value || '1';
    puzzles = chapterPuzzles[ch] || randomPuzzles;
  }}
  puzzleIndex = 0;
  loadPuzzle(0);
}}

function switchChapter(ch) {{
  if (mode === 'chapter' && chapterPuzzles[ch]) {{
    puzzles = chapterPuzzles[ch];
    puzzleIndex = 0;
    loadPuzzle(0);
  }}
}}

loadPuzzle(0);
</script>
</body>
</html>"""
    return html


def main():
    load_dotenv()
    print("=" * 60)
    print("Mythos AI — 填字游戏生成器")
    print("=" * 60)

    kg = load_kg()
    print(f"知识图谱加载: {kg['metadata']['total_characters']} 人物")

    pool = build_answer_pool(kg)
    print(f"候选答案池: {len(pool)} 个")

    pool = [p for p in pool if 4 <= len(p[0]) <= 10]

    # --- Mode 1: Random puzzles (existing behavior) ---
    print("\n--- 随机模式 ---")
    random_puzzles = generate_puzzles(pool, target=TARGET_WORDS, max_puzzles=NUM_PUZZLES)
    if not random_puzzles:
        print("[错误] 无法生成任何随机填字游戏，请调整参数")
        return

    print(f"成功生成 {len(random_puzzles)} 个随机填字游戏")
    for i, p in enumerate(random_puzzles):
        ac = sum(1 for _, _, _, a, _, _ in p['placed'] if a)
        dn = len(p['placed']) - ac
        sz = f"{len(p['trimmed'])}x{len(p['trimmed'][0])}"
        print(f"  #{i+1}: {len(p['placed'])}题 ({ac}横+{dn}竖) 网格{sz}")

    # --- Mode 2: Per-chapter puzzles ---
    print("\n--- 章节模式 ---")
    pool_by_ch = build_pool_by_chapter(pool, kg)
    chapter_puzzles = {}
    for ch in sorted(pool_by_ch.keys(), key=lambda x: int(x) if x.isdigit() and x != '?' else 999):
        ch_pool = [p for p in pool_by_ch[ch] if 4 <= len(p[0]) <= 10]
        if len(ch_pool) < 10:
            print(f"  章节 {ch}: 跳过 (仅 {len(ch_pool)} 个答案)")
            continue
        # Adjust target and count based on pool size
        if len(ch_pool) < 15:
            target = 7
        elif len(ch_pool) < 20:
            target = 8
        else:
            target = TARGET_WORDS
        max_p = max(1, min(5, len(ch_pool) // max(target, 1)))
        ch_result = generate_puzzles(ch_pool, target=target, max_puzzles=max_p, attempts_mult=3)
        if ch_result:
            chapter_puzzles[ch] = ch_result
            sz_info = [f"{len(p['trimmed'])}x{len(p['trimmed'][0])}" for p in ch_result]
            ac = ch_result[0]['clues']['across']
            dn = ch_result[0]['clues']['down']
            print(f"  章节 {ch}: {[len(p['placed']) for p in ch_result]}题 网格{', '.join(sz_info)}  (池{len(ch_pool)})")

    # --- LLM integration ---
    llm_enabled = os.getenv("LLM_ENABLED", "").lower() in ("1", "true", "yes")
    explanations = {}

    if llm_enabled:
        print("\n[LLM] 正在初始化增强器...")
        try:
            from llm_enhancer import LLMEnhancer
            enhancer = LLMEnhancer()
            print(f"[LLM] 模型: {enhancer.model}, 缓存: {len(enhancer.cache)} 条")

            # Collect all puzzles from both modes
            all_puzzles = list(random_puzzles)
            for ch in chapter_puzzles:
                all_puzzles.extend(chapter_puzzles[ch])

            _apply_llm(all_puzzles, kg, enhancer, explanations)

        except Exception as e:
            print(f"[LLM] 初始化失败: {e}，将使用原始线索")
            llm_enabled = False

    html = generate_html(random_puzzles, chapter_puzzles, explanations if llm_enabled else None)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\n[OK] 填字游戏已生成: {OUTPUT_FILE.resolve()}")
    total_all = len(random_puzzles) + sum(len(v) for v in chapter_puzzles.values())
    print(f"总计: {len(random_puzzles)} 随机 + {total_all - len(random_puzzles)} 章节 = {total_all} 题")


if __name__ == "__main__":
    main()
