"""
Mythos AI — Quiz Generator (05_quiz_generator.py)

Generates textbook-grounded quiz questions from the knowledge graph.
All data embedded in a single self-contained HTML file.
"""

import json
import random
from pathlib import Path
from collections import defaultdict

GRAPH_FILE = Path("data/knowledge_graph.json")
OUTPUT_FILE = Path("output/quiz.html")


def load_kg():
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_distractors(correct, pool, count=3, exclude=None):
    if exclude is None:
        exclude = set()
    exclude.add(correct)
    available = [x for x in pool if x not in exclude]
    random.shuffle(available)
    return available[:count]


def gen_mc_roman_equivalent(kg):
    chars = [c for c in kg["characters"] if c.get("roman_name") and c["roman_name"] != c["name"]]
    if len(chars) < 4:
        return None
    c = random.choice(chars)
    correct = c["roman_name"]
    pool = list({ch.get("roman_name") for ch in kg["characters"] if ch.get("roman_name")})
    distractors = pick_distractors(correct, pool, count=3)
    if len(distractors) < 3:
        return None
    options = [correct] + distractors
    random.shuffle(options)
    evidence = c.get("evidence", [])
    ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
    return {"t":"mc","cat":"Roman Equivalent","q":f"Which Roman god/goddess is equivalent to the Greek {c['name']}?","opts":options,"ans":correct,"exp":f"{c['name']} is the Greek name; the Roman equivalent is {c['roman_name']}.","ref":ref}


def gen_mc_domain(kg):
    chars = [c for c in kg["characters"] if len(c.get("domains", [])) > 0 and c.get("type") in ("god", "goddess")]
    if len(chars) < 4:
        return None
    c = random.choice(chars)
    correct = c["domains"][0]
    all_domains = list({d.strip() for ch in kg["characters"] for d in ch.get("domains", []) if d.strip()})
    distractors = pick_distractors(correct, all_domains, count=3)
    if len(distractors) < 3:
        return None
    options = [correct] + distractors
    random.shuffle(options)
    evidence = c.get("evidence", [])
    ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
    return {"t":"mc","cat":"Domain","q":f"{c['name']} is the god/goddess of which domain?","opts":options,"ans":correct,"exp":f"{c['name']} governs: {', '.join(c['domains'])}.","ref":ref}


def gen_mc_parent(kg):
    child_rels = [r for r in kg["relationships"] if r.get("type") == "child_of" and r.get("source") and r.get("target")]
    if len(child_rels) < 4:
        return None
    r = random.choice(child_rels)
    parent_name = r["target"]
    parent_pool = [c["name"] for c in kg["characters"]]
    distractors = pick_distractors(parent_name, parent_pool, count=3)
    if len(distractors) < 3:
        return None
    options = [parent_name] + distractors
    random.shuffle(options)
    ref = f"ch.{r.get('chapter', '?')} p.{r.get('page', '?')}"
    return {"t":"mc","cat":"Parentage","q":f"Who is the parent of {r['source']}?","opts":options,"ans":parent_name,"exp":r.get("description", f"{parent_name} is the parent of {r['source']}."),"ref":ref}


def gen_mc_epithet(kg):
    chars = [c for c in kg["characters"] if len(c.get("epithets", [])) > 0]
    if len(chars) < 4:
        return None
    c = random.choice(chars)
    correct = c["epithets"][0]
    all_epithets = list({ep for ch in kg["characters"] for ep in ch.get("epithets", [])})
    distractors = pick_distractors(correct, all_epithets, count=3)
    if len(distractors) < 3:
        return None
    options = [correct] + distractors
    random.shuffle(options)
    evidence = c.get("evidence", [])
    ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
    return {"t":"mc","cat":"Epithet","q":f"Which of the following is an epithet of {c['name']}?","opts":options,"ans":correct,"exp":f"{c['name']} is known by the epithet '{correct}'.","ref":ref}


def _myth_label(m):
    """Return 'Myth Name (short context)' for clearer questions."""
    s = m.get("summary", "")
    if not s:
        return m["name"]
    if len(s) <= 40:
        return f"{m['name']} ({s})"
    # Truncate at word boundary within 40 chars
    cut = s[:40]
    i = cut.rfind(" ")
    ctx = cut[:i] + "..." if i > 20 else cut + "..."
    return f"{m['name']} ({ctx})"

def _killer_victim(r):
    """Return (killer, victim) from a killed_by relationship, handling passive descriptions.
    Returns None if the description doesn't actually describe a killing."""
    desc = r.get("description", "").lower()
    kill_indicators = ["kill", "murder", "slay", "slew", "slain", "death of", "die", "dead",
                       "contrived the death", "sent poisoned", "poisoned gifts",
                       "shot", "stabbed", "strangled", "beheaded", "drowned", "hung"]
    if not any(k in desc for k in kill_indicators):
        return None
    if "was killed by" in desc or "was murdered by" in desc or "was slain by" in desc:
        return r["target"], r["source"]
    return r["source"], r["target"]

def gen_mc_myth_detail(kg):
    """Generate myth detail questions using relationships within a single myth."""
    detail_types = ["killed_by","parent_of","spouse_of","lover_of",
                    "transformed_into","opponent_of","fought_against","resides_in"]

    # Find myths with good detail relationships (both chars in myth)
    candidates = []
    for m in kg["myths"]:
        chars = set(m.get("key_characters", []))
        if len(chars) < 2:
            continue
        summary = m.get("summary", "")
        if len(summary) < 30:
            continue
        for r in kg["relationships"]:
            rt = r.get("type")
            if rt not in detail_types:
                continue
            src = r.get("source", "")
            tgt = r.get("target", "")
            if src not in chars or tgt not in chars:
                continue
            if rt == "killed_by":
                kv = _killer_victim(r)
                if kv is None:
                    continue
                killer, victim = kv
                candidates.append((m, r, victim, killer, rt))
            elif rt == "parent_of":
                candidates.append((m, r, tgt, src, rt))      # target is child, source is parent
            elif rt == "transformed_into":
                candidates.append((m, r, src, tgt, rt))      # source was transformed into target
            elif rt in ("spouse_of", "lover_of"):
                candidates.append((m, r, src, tgt, rt))
            elif rt in ("opponent_of", "fought_against"):
                candidates.append((m, r, src, tgt, rt))
            elif rt == "resides_in":
                candidates.append((m, r, src, tgt, rt))

    if not candidates:
        return None

    m, r, char1, char2, rt = random.choice(candidates)

    ml = _myth_label(m)
    question_templates = {
        "killed_by": f"In the myth of {ml}, who killed {char1}?",
        "parent_of": f"In the myth of {ml}, who is the parent of {char1}?",
        "spouse_of": f"In the myth of {ml}, who was {char1} married to?",
        "lover_of": f"In the myth of {ml}, who was {char1} in love with?",
        "transformed_into": f"In the myth of {ml}, what was {char1} transformed into?",
        "opponent_of": f"In the myth of {ml}, who opposed {char1}?",
        "fought_against": f"In the myth of {ml}, who did {char1} fight against?",
        "resides_in": f"In the myth of {ml}, where does {char1} reside?",
    }

    correct = char2
    question = question_templates.get(rt)
    if not question:
        return None

    # Build distractor pool (handle multiple-parent issue for parent_of)
    pool_map = {
        "killed_by": [c["name"] for c in kg["characters"]],
        "parent_of": [c["name"] for c in kg["characters"]],
        "spouse_of": [c["name"] for c in kg["characters"]],
        "lover_of": [c["name"] for c in kg["characters"]],
        "transformed_into": [c["name"] for c in kg["characters"] if c.get("type") in ("creature","monster","plant","object")],
        "opponent_of": [c["name"] for c in kg["characters"]],
        "fought_against": [c["name"] for c in kg["characters"]],
        "resides_in": [p["name"] for p in kg["places"]],
    }

    pool = pool_map.get(rt, [c["name"] for c in kg["characters"]])
    # For parent_of, exclude other known parents of the same child
    if rt == "parent_of":
        child = char1
        other_parents = {r2["source"] for r2 in kg["relationships"]
                         if r2.get("type") == "parent_of" and r2.get("target") == child
                         and r2["source"] != correct}
        pool = [p for p in pool if p not in other_parents]
    distractors = pick_distractors(correct, pool, count=3)
    if len(distractors) < 3:
        return None

    options = [correct] + distractors
    random.shuffle(options)
    pages = m.get("mentioned_pages", [])
    ref = f"ch.{pages[0]}" if pages else ""
    exp = r.get("description", "") or m.get("summary", "")
    if len(exp) > 150:
        i = exp[:150].rfind(" ")
        exp = exp[:i] + "..." if i > 60 else exp[:150] + "..."
    return {"t":"mc","cat":"Myth Details","q":question,"opts":options,"ans":correct,"exp":exp,"ref":ref}


def gen_tf_myth_detail(kg):
    """Generate myth-anchored true/false questions about character relationships."""
    tf_types = ["killed_by","parent_of","child_of","spouse_of","lover_of",
                "opponent_of","fought_against"]
    label_map = {
        "killed_by": "killer", "parent_of": "parent", "child_of": "child",
        "spouse_of": "spouse", "lover_of": "lover",
        "opponent_of": "opponent", "fought_against": "opponent"
    }

    candidates = []
    for m in kg["myths"]:
        chars = set(m.get("key_characters", []))
        if len(chars) < 3:
            continue
        summary = m.get("summary", "")
        if len(summary) < 30:
            continue
        for r in kg["relationships"]:
            rt = r.get("type")
            if rt not in tf_types:
                continue
            src = r.get("source", "")
            tgt = r.get("target", "")
            if src not in chars or tgt not in chars:
                continue
            if rt == "killed_by":
                kv = _killer_victim(r)
                if kv is None:
                    continue
                killer, victim = kv
                candidates.append((m, r, killer, victim, rt, list(chars)))
            else:
                candidates.append((m, r, src, tgt, rt, list(chars)))

    if len(candidates) < 4:
        return None

    m, r, src, tgt, rt, chars = random.choice(candidates)
    ml = _myth_label(m)
    label = label_map.get(rt, rt)
    is_true = random.random() < 0.5

    if is_true:
        statement = f"In the myth of {ml}, {src} was the {label} of {tgt}."
        correct = True
        explanation = r.get("description", "") or m.get("summary", "")[:200]
    else:
        pool = [c for c in chars if c != src and c != tgt]
        if not pool:
            return None
        wrong = random.choice(pool)
        statement = f"In the myth of {ml}, {wrong} was the {label} of {tgt}."
        correct = False
        desc = r.get("description", "")
        explanation = f"Incorrect. In the myth of {ml}, {desc or f'{src} was the {label} of {tgt}'}"

    ref = f"ch.{r.get('chapter', '?')} p.{r.get('page', '?')}"
    return {"t":"tf","cat":"Myth Relationships","q":statement,"ans":correct,"exp":explanation,"ref":ref}


def gen_tf_domain(kg):
    chars = [c for c in kg["characters"] if len(c.get("domains", [])) > 0]
    if len(chars) < 4:
        return None
    c = random.choice(chars)
    is_true = random.random() < 0.5
    if is_true:
        domain = random.choice(c["domains"])
        statement = f"{c['name']} is the god/goddess of {domain}."
        correct = True
    else:
        others = [x for x in kg["characters"] if x["name"] != c["name"] and len(x.get("domains", [])) > 0]
        if not others:
            return None
        domain = random.choice(others)["domains"][0]
        statement = f"{c['name']} is the god/goddess of {domain}."
        correct = False
    evidence = c.get("evidence", [])
    ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
    exp = f"{c['name']} governs: {', '.join(c['domains'])}." if correct else f"No, {c['name']} governs {', '.join(c['domains'])}, not {domain}."
    return {"t":"tf","cat":"Divine Domains","q":statement,"ans":correct,"exp":exp,"ref":ref}


def gen_match_greek_roman(kg):
    # Validate roman_name against relationship data to ensure correct direction
    # roman_equivalent: source=Greek, target=Roman
    roman_eq = {(r["source"], r["target"]) for r in kg["relationships"] if r.get("type") == "roman_equivalent"}
    # greek_equivalent: source=Roman, target=Greek
    greek_eq = {(r["source"], r["target"]) for r in kg["relationships"] if r.get("type") == "greek_equivalent"}
    pairs = []
    for c in kg["characters"]:
        rn = c.get("roman_name", "")
        if not rn or rn == c["name"]:
            continue
        name = c["name"]
        if (name, rn) in roman_eq:
            pairs.append((name, rn))
        elif (rn, name) in greek_eq:
            # rn is Roman, name is Greek → (Greek, Roman) correct
            pairs.append((name, rn))
        elif (name, rn) in greek_eq:
            # name is Roman, rn is Greek → swap to (Greek, Roman)
            pairs.append((rn, name))
    if len(pairs) < 4:
        return None
    selected = random.sample(pairs, min(6, len(pairs)))
    left = [p[0] for p in selected]
    right = [p[1] for p in selected]
    random.shuffle(right)
    return {"t":"match","cat":"Greek Roman Names","q":"Match each Greek name to its Roman equivalent:","left":left,"right":right,"ans":{p[0]:p[1] for p in selected},"exp":"Standard Greek and Roman name equivalences from the textbook.","ref":""}


def gen_match_domain(kg):
    chars = [c for c in kg["characters"] if len(c.get("domains", [])) > 0 and c.get("type") in ("god","goddess")]
    if len(chars) < 4:
        return None
    selected = random.sample(chars, min(6, len(chars)))
    left = [c["name"] for c in selected]
    right = [c["domains"][0] for c in selected]
    random.shuffle(right)
    return {"t":"match","cat":"Gods Domains","q":"Match each god/goddess to their domain:","left":left,"right":right,"ans":{c["name"]:c["domains"][0] for c in selected},"exp":"Each god/goddess governs specific domains in Greek mythology.","ref":""}


def gen_sa_roman(kg):
    chars = [c for c in kg["characters"] if c.get("roman_name") and c["roman_name"] != c["name"]]
    if not chars:
        return None
    c = random.choice(chars)
    evidence = c.get("evidence", [])
    ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
    return {"t":"sa","cat":"Roman Equivalents","q":f"What is the Roman name of {c['name']}?","ans":c["roman_name"],"exp":f"The Roman equivalent of {c['name']} is {c['roman_name']}.","ref":ref}


def gen_sa_parent(kg):
    child_rels = [r for r in kg["relationships"] if r.get("type") == "child_of"]
    if len(child_rels) < 4:
        return None
    r = random.choice(child_rels)
    ref = f"ch.{r.get('chapter', '?')} p.{r.get('page', '?')}"
    return {"t":"sa","cat":"Parentage","q":f"Who is the parent of {r['source']}?","ans":r["target"],"exp":r.get("description", f"{r['target']} is the parent of {r['source']}."),"ref":ref}


def generate_all(kg, mc_count=25, tf_count=15, match_count=5, sa_count=10):
    gens_mc = [gen_mc_roman_equivalent, gen_mc_domain, gen_mc_parent, gen_mc_epithet, gen_mc_myth_detail]
    gens_tf = [gen_tf_myth_detail, gen_tf_domain]
    gens_match = [gen_match_greek_roman, gen_match_domain]
    gens_sa = [gen_sa_roman, gen_sa_parent]
    questions = []
    for _ in range(mc_count * 4):
        if len([q for q in questions if q["t"] == "mc"]) >= mc_count:
            break
        q = random.choice(gens_mc)(kg)
        if q:
            questions.append(q)
    for _ in range(tf_count * 4):
        if len([q for q in questions if q["t"] == "tf"]) >= tf_count:
            break
        q = random.choice(gens_tf)(kg)
        if q:
            questions.append(q)
    for _ in range(match_count * 4):
        if len([q for q in questions if q["t"] == "match"]) >= match_count:
            break
        q = random.choice(gens_match)(kg)
        if q:
            questions.append(q)
    for _ in range(sa_count * 4):
        if len([q for q in questions if q["t"] == "sa"]) >= sa_count:
            break
        q = random.choice(gens_sa)(kg)
        if q:
            questions.append(q)
    random.shuffle(questions)
    # Strip any LLM enhancement markers for clean generation
    for q in questions:
        q.pop("enhanced", None)
    return questions


def main():
    print("=" * 60)
    print("Mythos AI - Quiz Generator")
    print("=" * 60)

    kg = load_kg()
    print(f"Loaded: {kg['metadata']['total_characters']} characters, {kg['metadata']['total_relationships']} relationships")

    seeds = list(range(42, 142))
    all_sets = []
    for seed in seeds:
        random.seed(seed)
        questions = generate_all(kg, mc_count=6, tf_count=4, match_count=2, sa_count=3)
        all_sets.append(questions)

    first = all_sets[0]
    mc = sum(1 for q in first if q["t"] == "mc")
    tf = sum(1 for q in first if q["t"] == "tf")
    mt = sum(1 for q in first if q["t"] == "match")
    sa = sum(1 for q in first if q["t"] == "sa")
    print(f"Generated: {len(first)} questions x{len(all_sets)} sets")
    print(f"  MC: {mc}, TF: {tf}, Match: {mt}, SA: {sa}")

    data_json = json.dumps(all_sets, ensure_ascii=False)

    template_path = Path(__file__).parent / "quiz_template.html"
    if not template_path.exists():
        print("[ERROR] quiz_template.html not found!")
        return

    html = template_path.read_text(encoding="utf-8")
    html = html.replace("/* ALL_SETS */", data_json)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[OK] Saved: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
