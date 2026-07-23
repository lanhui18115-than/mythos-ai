import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

# Check Medea's Children entity exists
children = [c for c in kg["characters"] if c["name"] == "Medea's Children"]
print(f"=== Medea's Children entity ===")
if children:
    print(f"  EXISTS: {json.dumps(children[0], indent=2, ensure_ascii=False)}")
else:
    print("  NOT FOUND")

# Check Medea's relationships now point correctly
print(f"\n=== Medea's relationships involving children ===")
for r in kg["relationships"]:
    if r["source"] == "Medea" and "children" in r.get("target", "").lower():
        print(f'  {r["source"]} --[{r["type"]}]--> {r["target"]}')

# Check Minerva entity
minerva = [c for c in kg["characters"] if c["name"] == "Minerva"]
print(f"\n=== Minerva entity ===")
if minerva:
    print(f"  EXISTS: {minerva[0]}")
else:
    print("  NOT FOUND")

# Check Minerva relationship to Athena
print(f"\n=== Minerva relationships ===")
for r in kg["relationships"]:
    if r["source"] == "Minerva":
        print(f'  {r["source"]} --[{r["type"]}]--> {r["target"]}')

# Count all Roman entities created
roman_entities = [c for c in kg["characters"] if c.get("description", "").startswith("Roman equivalent")]
print(f"\n=== Total Roman entities created: {len(roman_entities)} ===")

# Count fixup entities
fixup_entities = []
for c in kg["characters"]:
    if c.get("evidence") == [] and c.get("chapters") == [] and c.get("mentioned_pages") == [] and c.get("roman_name") == "" and not c.get("description", "").startswith("Roman equivalent"):
        fixup_entities.append(c["name"])
print(f"Fixup entities in characters: {len(fixup_entities)}")
for f in sorted(fixup_entities):
    print(f"  {f}")
