import json
from collections import Counter

with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
    kg = json.load(f)

# 角色分类统计
type_counts = Counter()
for c in kg["characters"]:
    t = c.get("type", "other")
    type_counts[t] += 1

print("=== 角色类型分布 ===")
type_order = ["god", "goddess", "hero", "mortal", "titan", "nymph", "monster", "creature", "group", "race", "other"]
for t in type_order:
    if t in type_counts:
        print(f"  {t}: {type_counts[t]}")

# 情人关系例子
print("\n=== 情人关系样本 ===")
lovers = [r for r in kg["relationships"] if r["type"] == "lover_of"]
print(f"  总数: {len(lovers)}")
seen = set()
for r in lovers:
    key = (r["source"], r["target"])
    if key not in seen:
        seen.add(key)
        print(f'  {r["source"]} --[情人]--> {r["target"]}  (ch{r.get("chapter","?")} p{r.get("page","?")})')
        if len(seen) >= 8:
            break

# 检查一个具体例子：Zeus的情人和子女
print("\n=== Zeus's lovers and their shared children ===")
zeus_lovers = set()
for r in lovers:
    if r["source"] == "Zeus":
        zeus_lovers.add(r["target"])
    elif r["target"] == "Zeus":
        zeus_lovers.add(r["source"])

for lover in sorted(zeus_lovers):
    children = []
    for r in kg["relationships"]:
        if r["type"] == "parent_of" and r["source"] == "Zeus":
            child = r["target"]
            # 检查这个孩子是否也是该情人的孩子
            for r2 in kg["relationships"]:
                if r2["type"] == "parent_of" and r2["source"] == lover and r2["target"] == child:
                    children.append(child)
                    break
    if children:
        print(f"  {lover} → 子女: {', '.join(children)}")
    else:
        print(f"  {lover} → (无共同子女记录)")
    if len(zeus_lovers) >= 20:
        break
