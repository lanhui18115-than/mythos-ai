"""
Full diagnostic: what fields exist in KG/index vs what is passed to LLM.
"""
import json
import sys
sys.path.insert(0, "scripts")
from ai_tutor_server import build_context, search_kg, get_relevance
from inspect import getsource

index = json.load(open("data/ai_tutor_index.json", "r", encoding="utf-8"))

print("=" * 60)
print("PART A: Field Completeness Analysis")
print("=" * 60)

zeus = next(c for c in index["characters"] if c["n"] == "Zeus")
themis = next(c for c in index["characters"] if c["n"] == "Themis")

# Read the actual source code of build_context to see what it outputs
src = getsource(build_context)
print("\nbuild_context() source code for character section:")
for line in src.split("\n"):
    if "c['" in line or "c.get(" in line:
        print(f"  {line.strip()}")

print("\nFields present in index but NOT output by build_context():")
for c in [zeus, themis]:
    print(f"\n  {c['n']}:")
    for field, label in [("e", "epithets"), ("d", "domains"), ("sy", "symbols")]:
        if field in c and c[field]:
            print(f"    [{label}] {json.dumps(c[field], ensure_ascii=False)[:80]}")
            print(f"    -> NOT included in build_context output")

# Verify by checking actual output
results = search_kg("Zeus", index)
context = build_context(results)
print("\nCheck if epithets appear in context for Themis:")
themis_results = search_kg("Themis", index)
themis_ctx = build_context(themis_results)
for line in themis_ctx.split("\n"):
    if "Themis" in line:
        print(f"  {line.strip()}")
        if "Right" in line:
            print("    >> 'Right' FOUND in context")
        else:
            print("    >> 'Right' NOT in this line")

print("\n" + "=" * 60)
print("PART B: Search Threshold Problems")
print("=" * 60)

test_cases = [
    ("Short exact name", "Themis", 1),
    ("Medium (3 words)", "epithet of Themis", 3),
    ("Long natural lang", "what is the epithet of Themis", 6),
    ("Chinese mix", "Themis de cheng hao shi shen me", 6),
    ("Domain question", "what does Themis govern", 4),
    ("Roman name query", "what is the roman name of Themis", 7),
]

for label, q, expected_terms in test_cases:
    terms = [w for w in q.lower().split() if len(w) >= 2]
    score = 0
    for c in index["characters"]:
        if c["n"] == "Themis":
            s_name = get_relevance(c["n"], q)
            s_roman = get_relevance(c.get("r", ""), q)
            s_desc = get_relevance(c.get("desc", ""), q)
            s_ep = max([get_relevance(e, q) for e in c.get("e", [])], default=0)
            s_dom = max([get_relevance(d, q) for d in c.get("d", [])], default=0)
            score = max(s_name, s_roman, s_desc, s_ep, s_dom)
            break
    results = search_kg(q, index)
    found = any(x["item"]["n"] == "Themis" for x in results["characters"])
    status = "FOUND" if found else "MISS"
    print(f"  [{status}] score={score:.2f}  threshold=0.50  ({label})")

# Show the scoring breakdown for a specific case
print("\nScoring breakdown for 'what is the epithet of Themis':")
q = "what is the epithet of Themis"
terms = [w for w in q.lower().split() if len(w) >= 2]
print(f"  Query terms: {terms} ({len(terms)} words)")
for c in index["characters"]:
    if c["n"] == "Themis":
        for field, label in [("n", "name"), ("r", "roman_name"), ("desc", "description"),
                              ("e", "epithets"), ("d", "domains")]:
            val = c.get(field, "")
            if isinstance(val, list):
                val = " ".join(val)
            matches = [t for t in terms if t in val.lower()]
            s = get_relevance(val, q)
            print(f"  {label:12s} | val='{str(val)[:40]:40s}' | matches={str(matches):30s} | score={s:.2f}")
        break

print("\n" + "=" * 60)
print("PART C: Issue Summary")
print("=" * 60)

print("""
ISSUE 1: build_context() omits 3 fields
  - epithets (e) -- e.g. Themis has "Right", Zeus has "Olympian"
  - domains (d)  -- e.g. Themis governs "justice, law, order, prophecy"
  - symbols (sy) -- e.g. Themis has "scales"
  These exist in the knowledge graph and the AI index, but build_context()
  never calls c.get("e"), c.get("d"), or c.get("sy").

ISSUE 2: Keyword search fails on natural language questions
  The algorithm splits the query by spaces and counts substring matches.
  A question like "what is the epithet of Themis" has 6 terms, but only
  "themis" matches the Themis entry. Score: 1/6 = 0.17.
  Even exact-match queries fail if they have filler words.

ISSUE 3: No Chinese search support
  Chinese text has no spaces, so the entire Chinese sentence is treated
  as one term and almost never matches any English index field.

ISSUE 4: Evidence format wastes tokens
  format_evidence() lists every individual page number instead of ranges.
  "Ch.4 pp. 82, 83, 86, 91, 92, 93, 94, 95, 96, 97, 98, 99, 102, 104, 105"
  could be "Ch.4 pp. 82-105 (selected pages)".
""")
