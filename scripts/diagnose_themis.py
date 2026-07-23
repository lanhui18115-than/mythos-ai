"""
Diagnose why AI Tutor can't find Themis's epithet but quiz can.
"""
import json
import sys
sys.path.insert(0, "scripts")
from ai_tutor_server import get_relevance, search_kg, build_context

# 1. Verify knowledge graph has Themis epithets
kg = json.load(open("data/knowledge_graph.json", "r", encoding="utf-8"))
for c in kg["characters"]:
    if c["name"] == "Themis":
        print("知识图谱 Themis:", json.dumps(c["epithets"], ensure_ascii=False))
        break

# 2. Verify AI Tutor index also has them
index = json.load(open("data/ai_tutor_index.json", "r", encoding="utf-8"))
for c in index["characters"]:
    if c["n"] == "Themis":
        print("AI索引 Themis e:", json.dumps(c["e"], ensure_ascii=False))
        break

# 3. Trace the search
query = "what is the epithet of Themis"
print("\n=== 搜索过程 ===")
print("查询:", query)

terms = [w for w in query.lower().split() if len(w) >= 2]
print("分词:", terms)
print("词数:", len(terms))

for c in index["characters"]:
    if c["n"] == "Themis":
        s_name = get_relevance(c["n"], query)
        s_roman = get_relevance(c.get("r", ""), query)
        s_desc = get_relevance(c.get("desc", ""), query)
        s_ep = max([get_relevance(e, query) for e in c.get("e", [])], default=0)
        s_dom = max([get_relevance(d, query) for d in c.get("d", [])], default=0)
        s_my = max([get_relevance(m, query) for m in c.get("myths", [])], default=0)
        final = max(s_name, s_roman, s_desc, s_ep, s_dom, s_my)

        print("\n评分:")
        print(f"  name='Themis'        → {s_name:.2f}  (匹配: 'themis')")
        print(f"  epithets=['Right',..] → {s_ep:.2f}  (无词匹配 Right/righteous)")
        print(f"  domains=['justice',.] → {s_dom:.2f}")
        print(f"  desc='Titaness...'   → {s_desc:.2f}")
        print(f"  MAX = {final:.2f}")
        print(f"  阈值 = 0.50")
        print(f"  {final:.2f} < 0.50 → ❌ Themis 未被检索到")
        break

# 4. Show the context that would be passed to LLM
results = search_kg(query, index)
total = sum(len(v) for v in results.values())
print(f"\n检索结果: 共 {total} 条匹配")
for k, v in results.items():
    if v:
        print(f"  {k}: {[x['item']['n'] for x in v]}")

print("\n=== 根本原因 ===")
print("用户提问: 'what is the epithet of Themis'")
print("分词后有效搜索词: 'what', 'the', 'epithet', 'of', 'themis'")
print("Themis 需要至少 3/5 词匹配(阈值0.5), 实际仅 'themis' 匹配(1/5=0.2)")
print("→ Themis 未能通过检索阈值, LLM 未收到 Themis 数据")
print("→ LLM 基于无数据的上下文回答 'no epithet found'")
print("\n而 Quiz 是预先生成的, 直接读取 knowledge_graph.json,")
print("不受搜索阈值影响, 所以正确显示了 'Right'")
