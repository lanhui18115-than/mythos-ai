"""
Verify all 4 fixes are working.
"""
import json, sys, os
sys.path.insert(0, "scripts")
os.environ["PYTHONIOENCODING"] = "utf-8"

from ai_tutor_server import build_context, search_kg, load_index, load_name_map, \
    expand_chinese_query, compress_pages, format_evidence

idx = load_index()

print("=" * 50)
print("FIX 1: build_context includes epithets/domains/symbols")
print("=" * 50)
results = search_kg("Themis", idx)
ctx = build_context(results)
for line in ctx.split("\n"):
    if "Themis" in line or line.strip().startswith("Epithets") or line.strip().startswith("Domains") or line.strip().startswith("Symbols"):
        print("  " + line.strip())
print()

print("=" * 50)
print("FIX 2: Search threshold + stop words + name boost")
print("=" * 50)
queries = [
    "what is the epithet of Themis",
    "epithet of Themis",
    "what does Themis govern",
    "what is the roman name of Themis",
]
for q in queries:
    results = search_kg(q, idx)
    themis = any(x["item"]["n"] == "Themis" for x in results["characters"])
    total = sum(len(v) for v in results.values())
    print(f"  ['YES' if themis else 'NO '] '{q}' -> {total} results")
print()

print("=" * 50)
print("FIX 3: Chinese query expansion")
print("=" * 50)
load_name_map()
tests = [
    "Themis de cheng hao shi shen me",
    "Themis cheng hao",
]
for q in tests:
    expanded = expand_chinese_query(q)
    results = search_kg(expanded, idx)
    themis = any(x["item"]["n"] == "Themis" for x in results["characters"])
    print(f"  Original: '{q}'")
    print(f"  Expanded: '{expanded}'")
    print(f"  Themis found: {'YES' if themis else 'NO'}")
    print()

print("=" * 50)
print("FIX 4: Evidence page compression")
print("=" * 50)
test = [82, 83, 86, 91, 92, 93, 94, 95, 96, 97, 98, 99, 102, 104, 105]
print(f"  Input:  {test}")
print(f"  Output: {compress_pages(test)}")

# Show actual evidence in output
results = search_kg("Themis", idx)
ctx = build_context(results)
for line in ctx.split("\n"):
    if "Source:" in line:
        print(f"  Context evidence: {line.strip()}")
        break
