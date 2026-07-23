"""
Analyze dangling references in the knowledge graph.
"""
import json
from collections import defaultdict

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

entity_names = set()
for cat in ["characters", "myths", "places", "concepts", "artworks"]:
    for e in kg.get(cat, []):
        name = e.get("name", "").strip().lower()
        if name:
            entity_names.add(name)

bad_refs = defaultdict(list)
for r in kg.get("relationships", []):
    src = r.get("source", "").strip().lower()
    tgt = r.get("target", "").strip().lower()
    if tgt and tgt not in entity_names:
        bad_refs[r["target"]].append(
            f'{r["source"]} --[{r["type"]}]--> {r["target"]}  |  {r.get("description", "")}'
        )
    if src and src not in entity_names:
        bad_refs[r["source"]].append(
            f'{r["source"]} --[{r["type"]}]--> {r["target"]}  |  {r.get("description", "")}'
        )

sorted_refs = sorted(bad_refs.items(), key=lambda x: -len(x[1]))

with open("data/dangling_report.txt", "w", encoding="utf-8") as out:
    out.write(f"Total dangling reference strings: {len(sorted_refs)}\n\n")
    for name, contexts in sorted_refs:
        out.write(f'"{name}" ({len(contexts)} occurrences)\n')
        for ctx in contexts[:5]:
            out.write(f"  {ctx}\n")
        if len(contexts) > 5:
            out.write(f"  ... and {len(contexts)-5} more\n")
        out.write("\n")

print(f"Done. Check data/dangling_report.txt")
