"""Test Dardanus parent query with relationship data."""
import json, sys
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, build_context, load_index

# Force reload index
import ai_tutor_server
ai_tutor_server.tutor_index = None
idx = load_index()

# Verify Dardanus has relationships in index
print("=== Dardanus in index ===")
for c in idx["characters"]:
    if c["n"] == "Dardanus":
        print(f"  desc: {c.get('desc','')}")
        print(f"  rels: {json.dumps(c.get('rel',[]), ensure_ascii=False, indent=4)}")
        break

# Test search
query = "Who is the parent of Dardanus?"
results = search_kg(query, idx)

print(f"\n=== Search: {query} ===")
print(f"Dardanus found: {any(x['item']['n']=='Dardanus' for x in results['characters'])}")

# Show the context that will be sent to LLM
ctx = build_context(results)
print("\n=== Context for Dardanus ===")
for line in ctx.split("\n"):
    if "Dardanus" in line or "Parent" in line or "Child" in line or "Zeus" in line or "Electra" in line or "child_of" in line:
        print(f"  {line.strip()}")
