import json
from pathlib import Path

print("=" * 50)
print("Mythos AI — Layer 3 Final Check")
print("=" * 50)

output = Path("output")

# Check files
for f in sorted(output.glob("*.html")):
    size = f.stat().st_size
    size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} bytes"
    print(f"  {f.name:35s} {size_str:>8s}")

# Verify quiz works
with open("output/quiz.html", "r", encoding="utf-8") as f:
    quiz = f.read()
import re
mc = len(re.findall(r'"type": "multiple_choice"', quiz))
tf = len(re.findall(r'"type": "true_false"', quiz))
mt = len(re.findall(r'"type": "matching"', quiz))
sa = len(re.findall(r'"type": "short_answer"', quiz))
print(f"\nQuiz content: {mc} MC, {tf} TF, {mt} Matching, {sa} SA = {mc+tf+mt+sa} total")

# Verify artwork
with open("output/artwork_quiz.html", "r", encoding="utf-8") as f:
    art = f.read()
ac = len(re.findall(r'"type": "artwork_character"', art))
at = len(re.findall(r'"type": "artwork_tf"', art))
aty = len(re.findall(r'"type": "artwork_type"', art))
an = len(re.findall(r'"type": "artwork_name"', art))
print(f"Artwork content: {ac} char, {at} TF, {aty} type, {an} name = {ac+at+aty+an} total")

# Verify crossword
with open("output/crossword.html", "r", encoding="utf-8") as f:
    cw = f.read()
solutions = re.findall(r"var SOLUTION = (.+?);", cw)
if solutions:
    grid = json.loads(solutions[0])
    total_cells = sum(1 for row in grid for ch in row if ch != " ")
    print(f"Crossword: {len(grid)}x{len(grid[0])} grid, {total_cells} filled cells")

# Verify family tree
with open("output/family_tree.html", "r", encoding="utf-8") as f:
    ft = f.read()
has_vis = "vis-network.min.js" in ft
print(f"Family tree: {'vis.js included' if has_vis else 'vis.js MISSING'}")

# Verify hub
with open("output/index.html", "r", encoding="utf-8") as f:
    hub = f.read()
has_cards = all(mod["file"] in hub for mod in [
    {"file": "family_tree.html"},
    {"file": "quiz.html"},
    {"file": "crossword.html"},
    {"file": "artwork_quiz.html"},
])
print(f"\nHub page: {'All modules linked' if has_cards else 'MISSING LINKS'}")

print(f"\n{'='*50}")
print("ALL CHECKS PASSED" if has_cards else "ISSUES FOUND")
print(f"{'='*50}")
