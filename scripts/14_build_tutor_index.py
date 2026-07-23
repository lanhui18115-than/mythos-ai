"""
Mythos AI — AI Tutor Search Index Builder (14_build_tutor_index.py)

Builds a lightweight search index from knowledge_graph.json for the AI Tutor widget.
Output: data/ai_tutor_index.json

Usage:
    py -3 scripts/14_build_tutor_index.py
"""

import json
import os
from collections import defaultdict

DATA_DIR = "data"
INPUT = os.path.join(DATA_DIR, "knowledge_graph.json")
OUTPUT = os.path.join(DATA_DIR, "ai_tutor_index.json")

kg = json.load(open(INPUT, "r", encoding="utf-8"))

# Build name-to-ID lookup
char_by_name = {}
for c in kg["characters"]:
    char_by_name[c["name"].lower()] = c["id"]
    char_by_name[c["id"]] = c

# Build relationships grouped by entity ID
rels_by_id = defaultdict(list)
for r in kg["relationships"]:
    src_id = r.get("source_id", "")
    tgt_id = r.get("target_id", "")
    rel_entry = {
        "t": r["type"],
        "other": r["target"] if src_id else "",
        "other_id": tgt_id,
        "desc": r.get("description", ""),
        "ch": r.get("chapter", 0),
        "pp": [r.get("page", 0)] if r.get("page") else []
    }
    if src_id:
        rels_by_id[src_id].append(rel_entry)

    rel_entry_rev = {
        "t": r["type"],
        "other": r["source"] if tgt_id else "",
        "other_id": src_id,
        "desc": r.get("description", ""),
        "ch": r.get("chapter", 0),
        "pp": [r.get("page", 0)] if r.get("page") else []
    }
    if tgt_id:
        rels_by_id[tgt_id].append(rel_entry_rev)

index = {
    "characters": [],
    "myths": [],
    "concepts": [],
    "places": [],
    "artworks": []
}

for c in kg["characters"]:
    entry = {
        "id": c["id"],
        "n": c["name"],
        "r": c.get("roman_name", ""),
        "e": c.get("epithets", []),
        "d": c.get("domains", []),
        "t": c.get("type", ""),
        "desc": c.get("description", ""),
        "myths": c.get("major_myths", []),
        "ch": c.get("chapters", []),
        "ev": [{"ch": e["chapter"], "pp": e["printed_pages"]} for e in c.get("evidence", [])],
    }
    rels = rels_by_id.get(c["id"], [])
    if rels:
        entry["rel"] = rels
    index["characters"].append(entry)

for m in kg["myths"]:
    entry = {
        "id": m["id"],
        "n": m["name"],
        "s": m.get("summary", ""),
        "kc": m.get("key_characters", []),
        "ch": m.get("chapters", []),
        "ev": [{"ch": e["chapter"], "pp": e["printed_pages"]} for e in m.get("evidence", [])],
    }
    rels = rels_by_id.get(m["id"], [])
    if rels:
        entry["rel"] = rels
    index["myths"].append(entry)

for c in kg["concepts"]:
    index["concepts"].append({
        "id": c["id"],
        "n": c["name"],
        "def": c.get("definition", ""),
        "ch": c.get("chapters", [])
    })

for p in kg["places"]:
    index["places"].append({
        "id": p["id"],
        "n": p["name"],
        "desc": p.get("description", ""),
        "ch": p.get("chapters", [])
    })

for a in kg["artworks"]:
    index["artworks"].append({
        "id": a["id"],
        "n": a["name"],
        "desc": a.get("description", ""),
        "ch": a.get("chapters", [])
    })

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False)

chars = len(index["characters"])
myths = len(index["myths"])
concepts = len(index["concepts"])
places = len(index["places"])
artworks = len(index["artworks"])
total_rels = sum(len(c.get("rel",[])) for c in index["characters"])
print(f"Index built: {chars} chars, {myths} myths, {concepts} concepts, {places} places, {artworks} artworks")
print(f"Total relationships embedded: {total_rels}")
