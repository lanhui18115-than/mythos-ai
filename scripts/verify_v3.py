import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

targets = [
    "Ajax (son of Telamon)", "Neoptolemus", "Argus (shipwright)",
    "Thoas (king of Lemnos)", "Thoas (son of Jason)",
    "Lycurgus (king of Nemea)", "Lycus (king of Mariandyni)",
    "Ajax the Locrian (son of O?leus)",
]

print("=== Previously missing evidence characters ===")
for c in kg["characters"]:
    if c["name"] in targets:
        ev = c.get("evidence", [])
        print(f'  {c["name"]} (id: {c.get("id","")}): evidence={len(ev)}')

# Verify no original character (non-fixup) lacks evidence
orig_no_ev = [
    c for c in kg["characters"]
    if not c.get("evidence")
    and c.get("chapters")  # has chapters = original, not fixup
]
print(f"\nOriginal characters still missing evidence: {len(orig_no_ev)}")

# Count entities with/without IDs
with_ids = sum(1 for c in kg["characters"] if c.get("id"))
print(f"\nCharacters with IDs: {with_ids}/{len(kg['characters'])}")
with_pc = sum(1 for c in kg["characters"] if c.get("primary_chapter"))
print(f"Characters with primary_chapter: {with_pc}/{len(kg['characters'])}")

# Count relationships with IDs
with_src_id = sum(1 for r in kg["relationships"] if r.get("source_id"))
with_tgt_id = sum(1 for r in kg["relationships"] if r.get("target_id"))
print(f"Relationships with source_id: {with_src_id}/{len(kg['relationships'])}")
print(f"Relationships with target_id: {with_tgt_id}/{len(kg['relationships'])}")
