"""Diagnose Sardis/Croesus query failure."""
import json, sys, string
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, build_context, load_index, get_relevance, STOP_WORDS, clean_term

idx = load_index()

# 1. Check if Sardis exists in places
print("=== Checking 'Sardis' in data ===")
for p in idx["places"]:
    if "sard" in p["n"].lower():
        print(f"  Place: {json.dumps(p, ensure_ascii=False)}")

# 2. Check if Croesus exists in characters
print("\n=== Checking 'Croesus' in data ===")
for c in idx["characters"]:
    if "croesus" in c["n"].lower():
        print(f"  Char: {json.dumps(c, ensure_ascii=False)}")

# Also check full KG
kg = json.load(open("data/knowledge_graph.json", "r", encoding="utf-8"))
for c in kg["characters"]:
    if "croesus" in c["name"].lower() or "sardis" in c["name"].lower():
        print(f"  KG char: {json.dumps(c, ensure_ascii=False)[:200]}")

for p in kg["places"]:
    if "sardis" in p["name"].lower() or "lydia" in p["name"].lower():
        print(f"  KG place: {json.dumps(p, ensure_ascii=False)[:200]}")

# 3. Trace the search
query = "Ancient Lydian capital where King Croesus reigned"
print(f"\n=== Search trace ===")
terms = [clean_term(w) for w in query.lower().split() if len(clean_term(w)) >= 2]
sig_terms = [w for w in terms if w not in STOP_WORDS]
print(f"Raw terms: {[w for w in query.lower().split()]}")
print(f"Cleaned: {terms}")
print(f"Significant: {sig_terms}")

# Score against Sardis (if it exists)
for p in idx["places"]:
    if "sardis" in p["n"].lower():
        s = get_relevance(p["n"], query, sig_terms)
        s_desc = get_relevance(p.get("desc",""), query, sig_terms)
        print(f"\n  Sardis score: name={s:.2f}, desc={s_desc:.2f}")
        print(f"  Term matches in 'Sardis': ", end="")
        for t in sig_terms:
            print(f"{t} in Sardis? {t in 'sardis'}", end=" | ")
        print()
        print(f"  Term matches in desc '{p.get('desc','')[:80]}': ", end="")
        for t in sig_terms:
            print(f"{t} in desc? {t in p.get('desc','').lower()}", end=" | ")
        print()

# Score against Croesus (if it exists)
for c in idx["characters"]:
    if "croesus" in c["n"].lower():
        s = get_relevance(c["n"], query, sig_terms)
        s_desc = get_relevance(c.get("desc",""), query, sig_terms)
        print(f"\n  Croesus score: name={s:.2f}, desc={s_desc:.2f}")

# 4. Overall search results
results = search_kg(query, idx)
print(f"\n=== Search results ===")
total = sum(len(v) for v in results.values())
print(f"Total results: {total}")
for k, v in results.items():
    names = [x["item"]["n"] for x in v]
    if names:
        print(f"  {k}: {names}")
