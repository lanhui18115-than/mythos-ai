import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

# Check IDs
print("=== ID samples ===")
for c in kg["characters"][:3]:
    eid = c.get("id", "MISSING")
    print(f'  {eid}: {c["name"]}')

# Check primary_chapter
zeus = [c for c in kg["characters"] if c["name"] == "Zeus"][0]
print(f'\n=== Zeus primary_chapter: {zeus.get("primary_chapter","MISSING")} ===')
print(f'  evidence count: {len(zeus.get("evidence",[]))}')

# Check relationship IDs
rels_with_ids = sum(1 for r in kg["relationships"] if "source_id" in r or "target_id" in r)
print(f'\n=== Relationships with ID refs: {rels_with_ids}/{len(kg["relationships"])} ===')
if kg["relationships"]:
    r = kg["relationships"][0]
    src_id = r.get("source_id", "noid")
    tgt_id = r.get("target_id", "noid")
    print(f'  Sample: {r.get("source","")} ({src_id}) --[{r["type"]}]--> {r.get("target","")} ({tgt_id})')

# Check the 8 previously missing evidence characters
missing_evidence = [c for c in kg["characters"] if not c.get("evidence")]
print(f'\n=== Characters still missing evidence: {len(missing_evidence)} ===')
for c in missing_evidence:
    print(f'  {c["name"]} (id: {c.get("id","?")})')

# Check Medea's Children (name has apostrophe, match by ID prefix)
char_list = kg["characters"]
mc_list = [c for c in char_list if "Medea" in c["name"] and "Children" in c["name"]]
if mc_list:
    mc = mc_list[0]
    mc_name = mc["name"]
    print(f'\n=== {mc_name} ===')
    print(f'  id: {mc.get("id","?")}')
    for r in kg["relationships"]:
        if r.get("source_id") == mc["id"] or r.get("target_id") == mc["id"]:
            print(f'  {r.get("source_id","")} ({r.get("source","")}) --[{r["type"]}]--> {r.get("target_id","")} ({r.get("target","")})')
