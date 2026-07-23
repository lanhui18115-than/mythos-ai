import json
from collections import Counter

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

rel_types = Counter(r["type"] for r in kg["relationships"])
print("=== All relationship type counts ===")
for rt, count in rel_types.most_common():
    print(f"  {rt}: {count}")

fam = [r for r in kg["relationships"] if r["type"] in ("parent_of","child_of","spouse_of")]
print(f"\n=== Family relationship totals ===")
print(f"  parent_of: {len([r for r in fam if r['type']=='parent_of'])}")
print(f"  child_of: {len([r for r in fam if r['type']=='child_of'])}")
print(f"  spouse_of: {len([r for r in fam if r['type']=='spouse_of'])}")

# Check if entities have 'id' and 'type' fields
c = kg["characters"][0]
print(f"\n=== Sample character fields ===")
for k, v in c.items():
    print(f"  {k}: {v}")
