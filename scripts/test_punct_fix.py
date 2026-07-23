"""Test the punctuation stripping fix."""
import json, sys
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, load_index, build_context

idx = load_index()

# Test original failing query
query = "What is the Roman name of Hours?"
results = search_kg(query, idx)

hours_found = any(x["item"]["n"] == "Hours" for x in results["characters"])
horae_found = any(x["item"]["n"] == "Horae" for x in results["characters"])
print(f"Query: {query}")
print(f"Hours found: {hours_found}")
print(f"Horae found: {horae_found}")
print("Top results:")
for r in results["characters"][:5]:
    print(f"  {r['item']['n']} (score={r['score']:.2f})")

# Show build_context for verification
ctx = build_context(results)
for line in ctx.split("\n"):
    if "Hours" in line or "Horae" in line:
        print(f"  {line.strip()}")

# Test other punctuated queries
tests = [
    "Who is Zeus?",
    "Tell me about Athena!",
    "What's the story of Persephone?",
]
print("\nOther punctuated queries:")
for t in tests:
    r = search_kg(t, idx)
    names = [x["item"]["n"] for x in r["characters"][:3]]
    print(f"  '{t}' -> {names}")
