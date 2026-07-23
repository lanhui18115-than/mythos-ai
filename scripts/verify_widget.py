"""Verify AI Tutor widget integration across all pages."""
import os
import re

BASE = "output"
FILES = [
    "index.html",
    "learning_center.html",
    "quiz.html",
    "crossword.html",
    "family_tree.html",
    "artwork_quiz.html",
    "character_index.html",
]

ok = 0
for f in FILES:
    path = os.path.join(BASE, f)
    content = open(path, "r", encoding="utf-8").read()
    has_widget = "ai_tutor_widget.js" in content
    has_body_end = "</body>" in content
    status = "OK" if has_widget else "MISSING"
    if has_widget:
        ok += 1
    print(f"  [{status}] {f}  (</body>: {has_body_end})")

print(f"\n  Result: {ok}/{len(FILES)} pages include the widget")

# Check JS size
js_size = os.path.getsize(os.path.join(BASE, "ai_tutor_widget.js"))
index_size = os.path.getsize("data/ai_tutor_index.json")
print(f"\n  ai_tutor_widget.js: {js_size // 1024} KB")
print(f"  ai_tutor_index.json: {index_size // 1024} KB")
