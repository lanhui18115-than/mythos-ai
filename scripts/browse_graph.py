"""
浏览知识图谱 — 查看提取质量
"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

kg = json.loads(
    (Path(__file__).parent.parent / "data" / "knowledge_graph.json").read_text(encoding="utf-8")
)

meta = kg["metadata"]
print("=" * 60)
print("知识图谱总览")
print("=" * 60)
for k, v in meta.items():
    print(f"  {k}: {v}")
print()

# ── 出现章节最多的角色 ──
chars = kg["characters"]
chars_sorted = sorted(chars, key=lambda c: len(c.get("chapters", [])), reverse=True)
print("出场章节最多的角色 (Top 20):")
print(f"  {'名称':15s} {'罗马名':15s} {'称号':20s} {'章节':4s} {'页码':4s}")
print(f"  {'-'*60}")
for c in chars_sorted[:20]:
    chs = c.get("chapters", [])
    page_count = sum(len(e.get("printed_pages", [])) for e in c.get("evidence", []))
    roman = c.get("roman_name") or ""
    epithet = c.get("epithets", [])
    ep_str = epithet[0] if epithet else ""
    print(f"  {c['name']:15s} {roman:15s} {ep_str:20s} {len(chs):2d}章 {page_count:2d}页")
print()

# ── 没有罗马名的角色（抽查） ──
no_roman = [c for c in chars if not c.get("roman_name")]
print(f"有希腊名无罗马名的角色: {len(no_roman)} 个")
if no_roman:
    print(f"  例如: {', '.join(c['name'] for c in no_roman[:10])}")
print()

# ── 关系最多的角色 ──
rels = kg["relationships"]
source_counts = {}
for r in rels:
    s = r["source"]
    source_counts[s] = source_counts.get(s, 0) + 1
top_rels = sorted(source_counts.items(), key=lambda x: -x[1])[:10]
print("关系最多的角色 (Top 10):")
for name, count in top_rels:
    print(f"  {name:20s}  {count} 条关系")
print()

# ── 关系类型分布 ──
type_counts = {}
for r in rels:
    t = r["type"]
    type_counts[t] = type_counts.get(t, 0) + 1
print("关系类型分布:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t:20s}  {c} 条")
print()

# ── 神话提取 ──
myths = kg["myths"]
myths_sorted = sorted(myths, key=lambda m: len(m.get("key_characters", [])), reverse=True)
print("内容最丰富的神话 (Top 10):")
for m in myths_sorted[:10]:
    chars_list = m.get("key_characters", [])
    pages = m.get("mentioned_pages", [])
    summary = m.get("summary", "")[:80]
    print(f"  {m['name']:30s}  {len(chars_list):2d} 角色  {len(pages):2d}页")
    if summary:
        print(f"    → {summary}...")
print()

# ── 艺术品 ──
artworks = kg["artworks"]
print(f"艺术品总数: {len(artworks)}")
if artworks:
    print("前 10 个艺术品:")
    for a in artworks[:10]:
        desc = a.get("description", "")[:60]
        print(f"  {a['name']:30s} ({a.get('type','')})  {desc}")

# ── 查看 Zeus 的完整记录 ──
print("\n" + "=" * 60)
print("完整记录示例 — Zeus")
print("=" * 60)
zeus = next((c for c in chars if c["name"] == "Zeus"), None)
if zeus:
    print(json.dumps(zeus, indent=2, ensure_ascii=False)[:800])

# ── 查看一个关系示例 ──
print("\n" + "=" * 60)
print("关系示例 (前 5 条)")
print("=" * 60)
for r in rels[:5]:
    print(f"  {r['source']:15s} → {r['target']:15s}  [{r['type']:20s}]  {r.get('description','')[:60]}")
