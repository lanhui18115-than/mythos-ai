import json
kg = json.load(open("data/knowledge_graph.json", "r", encoding="utf-8"))
# Check which characters have multiple parent_of entries
from collections import Counter
parents = Counter()
for r in kg["relationships"]:
    if r.get("type") == "parent_of":
        parents[r["target"]] += 1
multi = {k: v for k, v in parents.items() if v > 1}
print(f"Characters with >1 parent_of entry: {len(multi)}")
for ch, cnt in list(multi.items())[:10]:
    print(f"  {ch}: {cnt} parents")
    for r in kg["relationships"]:
        if r.get("type") == "parent_of" and r.get("target") == ch:
            print(f"    {r['source']}")
