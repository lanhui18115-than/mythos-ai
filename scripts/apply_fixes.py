"""Re-apply data fixes after merge"""
import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

before = len(kg["relationships"])

# 1. Remove Hera parent_of Heracles
kg["relationships"] = [
    r for r in kg["relationships"]
    if not (r.get("source") == "Hera" and r.get("target") == "Heracles" and r.get("type") == "parent_of")
]
after = len(kg["relationships"])
print(f"Removed Hera->Heracles parent_of: {before} -> {after}")

# 2. Add Zeus lover_of Alcmena
kg["relationships"].append({
    "source": "Zeus", "target": "Alcmena", "type": "lover_of",
    "description": "Zeus slept with Alcmena, fathering Heracles.",
    "chapter": 22, "page": 555, "evidence_level": "explicit",
    "source_id": "CHAR_0005", "target_id": "CHAR_0179"
})
print(f"Added Zeus->Alcmena lover_of: {len(kg['relationships'])}")

with open("data/knowledge_graph.json", "w", encoding="utf-8") as f:
    json.dump(kg, f, ensure_ascii=False, indent=2)
print("Saved.")
