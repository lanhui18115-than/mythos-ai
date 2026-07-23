"""Test Dardanus parent query via API."""
import requests, re

def strip_emoji(text):
    return re.sub(r'[\U0001F300-\U0001FFFF\U00002000-\U00002700\u2600-\u27BF\uFE00-\uFE0F]', '', text)

# Test: Dardanus parent
print("=== Test: Parent of Dardanus ===")
r = requests.post("http://localhost:5800/api/ask",
                  json={"question": "Who is the parent of Dardanus?"}, timeout=120)
data = r.json()
ans = data["data"]["answer"]
safe = strip_emoji(ans)[:600]
print(f"Answer:\n{safe}")
print()

# Verify key info
checks = {
    "Zeus mentioned": "Zeus" in ans,
    "Electra mentioned": "Electra" in ans,
    "Ch.19 reference": "Ch.19" in ans or "ch.19" in ans.lower(),
    "p.473 reference": "473" in ans,
}
for label, ok in checks.items():
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")
