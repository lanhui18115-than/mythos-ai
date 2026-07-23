import json

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

# 查雅典娜的亲子关系
print("=== Athena's parent/child relationships ===")
for r in kg["relationships"]:
    if r["type"] in ("parent_of", "child_of") and \
       ("Athena" in r["source"] or "Athena" in r["target"]):
        print(f'  {r["source"]} --[{r["type"]}]--> {r["target"]}  (page {r.get("page","?")}, ch{r.get("chapter","?")})')

# 统计 parent_of 的性别分布（通过角色type字段推断）
print("\n=== Parent_of: parent character types ===")
parent_types = {}
for r in kg["relationships"]:
    if r["type"] == "parent_of":
        parent_name = r["source"]
        # 在characters里找这个parent的type
        for c in kg["characters"]:
            if c["name"] == parent_name:
                t = c.get("type", "unknown")
                parent_types[t] = parent_types.get(t, 0) + 1
                break
for t, n in sorted(parent_types.items(), key=lambda x: -x[1]):
    print(f"  {t}: {n}")

# 检查关系中有没有 chapter 和 page
sample_rel = [r for r in kg["relationships"] if r["type"] == "parent_of"][0]
print(f"\n=== Sample parent_of relationship fields ===")
for k, v in sample_rel.items():
    print(f"  {k}: {v}")
