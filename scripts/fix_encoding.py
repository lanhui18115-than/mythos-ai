"""Fix corrupted characters in knowledge_graph.json from PowerShell pipeline"""
import json, glob

# Load chapter files to get correct names
correct = set()
for fname in sorted(glob.glob("data/knowledge/chapter_*.json")):
    with open(fname, "r", encoding="utf-8") as f:
        ch = json.load(f)
        for c in ch.get("characters", []):
            correct.add(c["name"])
        for r in ch.get("relationships", []):
            correct.add(r["source"])
            correct.add(r["target"])

# Load corrupted merged file
with open("data/knowledge_graph.json", "r", encoding="utf-8-sig") as f:
    kg = json.load(f)

# Check merged names for corruption
merged_names = {c["name"] for c in kg["characters"]}
for r in kg["relationships"]:
    merged_names.add(r["source"])
    merged_names.add(r["target"])

# Build mapping from corrupted to correct
fix_map = {}
for mn in merged_names:
    if any(ord(ch) > 0x4E00 for ch in mn):
        # Find matching name in chapter data
        for cn in correct:
            if len(cn) == len(mn):
                # Check if they differ only in non-ASCII chars
                diffs = [(i, mn[i], cn[i]) for i in range(len(cn)) if mn[i] != cn[i]]
                if all(ord(d[1]) > 0x4E00 and ord(d[2]) <= 0xFF for d in diffs):
                    fix_map[mn] = cn
                    break
        if mn not in fix_map:
            print(f"WARNING: cannot fix '{mn}'")

print(f"Corrupted names to fix: {len(fix_map)}")
for old, new in sorted(fix_map.items()):
    print(f"  {old} -> {new}")

# Apply fixes
def fix_name(n):
    return fix_map.get(n, n)

for c in kg["characters"]:
    c["name"] = fix_name(c["name"])
for r in kg["relationships"]:
    r["source"] = fix_name(r["source"])
    r["target"] = fix_name(r["target"])

with open("data/knowledge_graph.json", "w", encoding="utf-8") as f:
    json.dump(kg, f, ensure_ascii=False, indent=2)

print("Saved.")
