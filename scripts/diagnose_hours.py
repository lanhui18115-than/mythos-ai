"""
Diagnose why AI Tutor fails on "What is the Roman name of Hours?"
"""
import json, sys
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, build_context, load_index, expand_chinese_query, get_relevance, STOP_WORDS

idx = load_index()

# Find all Hours/Horae entries
print("=== Character entries for Hours/Horae ===")
for c in idx["characters"]:
    if "hour" in c["n"].lower() or "horae" in c["n"].lower():
        print(f"  Name: {c['n']}")
        print(f"  Roman: {c.get('r','')}")
        print(f"  Domains: {c.get('d',[])}")
        print(f"  Desc: {c.get('desc','')[:100]}")
        print()

# Search analysis
query = "What is the Roman name of Hours?"
expanded = expand_chinese_query(query)
print(f"Original query: {query}")
print(f"Expanded query: {expanded}")

terms = [w for w in expanded.lower().split() if len(w) >= 2]
sig_terms = [w for w in terms if w not in STOP_WORDS]
print(f"All terms: {terms}")
print(f"Significant terms: {sig_terms}")

# Check the term 'hours' specifically
print(f"\nIs 'hours' in stop words? {'hours' in STOP_WORDS}")
print(f"Is 'hours' >= 2 chars? {len('hours') >= 2}")
print(f"Is 'roman' in stop words? {'roman' in STOP_WORDS}")
print(f"Is 'name' in stop words? {'name' in STOP_WORDS}")

# Score each Hours/Horae entry
print("\n=== Scoring ===")
for c in idx["characters"]:
    if "hour" in c["n"].lower() or "horae" in c["n"].lower():
        texts_to_check = {
            "name": c["n"],
            "roman": c.get("r", ""),
            "desc": c.get("desc", ""),
            "domains": " ".join(c.get("d", [])),
            "epithets": " ".join(c.get("e", [])),
            "myths": " ".join(c.get("myths", [])),
        }
        scores = {}
        for field, text in texts_to_check.items():
            scores[field] = get_relevance(text, expanded, sig_terms)
        final = max(scores.values())
        print(f"  {c['n']}: {scores} -> max={final:.2f}")

# Search results
print("\n=== search_kg results ===")
results = search_kg(expanded, idx)
for k, v in results.items():
    names = [x["item"]["n"] for x in v]
    if names:
        print(f"  {k}: {names}")
    else:
        print(f"  {k}: (empty)")

# Check what the frontend does
print("\n=== Frontend JS analysis ===")
print("The frontend JS also has STOP_WORDS which includes 'name'")
print("'name' is a stop word, so it gets filtered out")
print("Search terms become: ['roman', 'hours']")
print("Hours needs 'hours' or 'roman' to match any of its fields")
