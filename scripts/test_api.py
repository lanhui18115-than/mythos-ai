"""Test the API endpoint with fixed code."""
import requests, json, re

def strip_emoji(text):
    emoji = re.compile(r'[\U0001F300-\U0001FFFF\U00002000-\U00002700\u2600-\u27BF\uFE00-\uFE0F]')
    return emoji.sub('', text)

# Test 1: Themis epithet (the original failing case)
print("=== Test 1: Themis epithet ===")
r = requests.post("http://localhost:5800/api/ask",
                  json={"question": "what is the epithet of Themis"}, timeout=120)
data = r.json()
ans = data["data"]["answer"]
checks = {
    "Themis mentioned": "Themis" in ans,
    "Right epithet found": "Right" in ans,
    "Roman name or Justitia": "Justitia" in ans or "Roman" in ans,
    "Chapter reference present": "Ch." in ans,
}
for label, ok in checks.items():
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")
safe_ans = strip_emoji(ans)[:500]
print(f"  Answer: {safe_ans}")

# Test 2: Zeus query (check all fields present)
print("\n=== Test 2: Zeus full info ===")
r = requests.post("http://localhost:5800/api/ask",
                  json={"question": "Zeus"}, timeout=120)
data = r.json()
ans = data["data"]["answer"]
safe_ans = strip_emoji(ans)[:600]
print(f"  Answer: {safe_ans}")
