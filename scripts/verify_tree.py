import json
from scripts import inspect_graph
# Quick check of family data for Athena
from scripts.diagnose_family import *

# Actually let me just directly check the generated HTML for a known character
with open("output/family_tree.html", "r", encoding="utf-8") as f:
    html = f.read()

# Check that key data is embedded
assert "FAMILIES" in html, "Missing FAMILIES data"
assert "CHARS" in html, "Missing CHARS data"
assert "vis.Network" in html, "Missing vis.Network"
assert "hierarchical" in html, "Missing hierarchical layout"
print("HTML structure check: PASS")

# Count size
print(f"File size: {len(html)} bytes")
print(f"FAMILIES data starts at: {html.index('FAMILIES')}")
print(f"vis.Network call at: {html.index('vis.Network')}")
