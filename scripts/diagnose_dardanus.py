"""Diagnose Dardanus parent issue."""
import json, sys
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, build_context, load_index, get_relevance

idx = load_index()

# 1. Find Dardanus in index
print("=== Dardanus in index ===")
for c in idx["characters"]:
    if "dardanus" in c["n"].lower():
        print(json.dumps(c, ensure_ascii=False, indent=2))
        break
else:
    print("Dardanus NOT FOUND in characters")

# 2. Check relationships in knowledge_graph.json
print("\n=== Dardanus relationships in KG ===")
kg = json.load(open("data/knowledge_graph.json", "r", encoding="utf-8"))
for r in kg["relationships"]:
    if "dardanus" in r["source"].lower() or "dardanus" in r["target"].lower():
        print(json.dumps(r, ensure_ascii=False, indent=2))

# 3. Check if there's a Dardanus entry in KG characters
print("\n=== Dardanus in knowledge_graph.json characters ===")
for c in kg["characters"]:
    if "dardanus" in c["name"].lower():
        print(json.dumps(c, ensure_ascii=False, indent=2))
        break
else:
    print("Dardanus NOT FOUND in KG characters")

# 4. Trace the search
query = "Who is the parent of Dardanus"
expanded = query  # no Chinese
print(f"\n=== Search trace for: {query} ===")
results = search_kg(expanded, idx)

dardanus_found = any(x["item"]["n"].lower() == "dardanus" for x in results["characters"])
print(f"Dardanus found: {dardanus_found}")

print("Character results:")
for r in results["characters"][:10]:
    print(f"  {r['item']['n']} (score={r['score']:.2f}) - desc: {r['item'].get('desc','')[:60]}")

# 5. Show context that would be sent to LLM
print("\n=== Context sent to LLM ===")
ctx = build_context(results)
print(ctx[:1500])

# 6. Check if parent_of relationships from Dardanus are in the data
print("\n=== All relationships involving Dardanus or parent_of ===")
# First find Dardanus ID
dard_id = None
for c in kg["characters"]:
    if c["name"].lower() == "dardanus":
        dard_id = c["id"]
        break

if dard_id:
    for r in kg["relationships"]:
        if r.get("source_id") == dard_id or r.get("target_id") == dard_id:
            print(f"  {json.dumps(r, ensure_ascii=False)}")
else:
    print("  No Dardanus ID found")
