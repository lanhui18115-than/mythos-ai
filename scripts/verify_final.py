import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

# Check all concepts for stubs
stub_concepts = [c for c in kg["concepts"] if not c.get("definition")]
print(f"Concepts with empty definition (auto-created stubs): {len(stub_concepts)}")
for s in stub_concepts:
    eid = s.get("id", "?")
    print(f"  {s['name']} (id: {eid})")

# Check characters for stubs
stub_chars = [c for c in kg["characters"] if not c.get("description") and not c.get("chapters")]
print(f"\nCharacters with empty description+chapters (auto-created stubs): {len(stub_chars)}")
for s in stub_chars:
    eid = s.get("id", "?")
    print(f"  {s['name']} (id: {eid})")

# Verify 0 dangling
entity_names = set()
for cat in ["characters", "myths", "places", "concepts", "artworks"]:
    for e in kg.get(cat, []):
        name = (e.get("name") or "").strip().lower()
        if name:
            entity_names.add(name)

dangling = 0
for r in kg.get("relationships", []):
    src = r.get("source", "").strip().lower()
    tgt = r.get("target", "").strip().lower()
    if (src and src not in entity_names) or (tgt and tgt not in entity_names):
        dangling += 1

print(f"\nRemaining dangling relationships: {dangling}")
print(f"Total relationships preserved: {len(kg['relationships'])}")
