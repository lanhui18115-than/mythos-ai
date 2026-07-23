"""Root cause analysis: Hours Roman name."""
import json, sys, re
sys.path.insert(0, "scripts")
from ai_tutor_server import search_kg, load_index, get_relevance, STOP_WORDS

idx = load_index()

query = "What is the Roman name of Hours?"

# Show the raw tokenization
terms_raw = query.lower().split()
print("Raw split terms:", terms_raw)

# Show filtered terms
terms = [w for w in query.lower().split() if len(w) >= 2]
print("Filtered (len>=2):", terms)

# Show stop-filtered terms
sig = [w for w in terms if w not in STOP_WORDS]
print("After stop-filter:", sig)

# The problem: 'hours?' has a question mark
print()
print("=== ROOT CAUSE ===")
print(f"Token 'hours?' contains trailing '?'")
print(f"Check: 'hours?' in 'hours' -> {'hours?' in 'hours'}")
print(f"Check: 'hours?' in 'horae' -> {'hours?' in 'horae'}")
print(f"Check: 'hours' in 'hours' -> {'hours' in 'hours'}")
print(f"Check: 'hours' in 'Horae'.lower() -> {'hours' in 'Horae'.lower()}")
print(f"Check: 'roman' in 'Hours'.lower() -> {'roman' in 'Hours'.lower()}")
print(f"Check: 'roman' in 'Horae'.lower() -> {'roman' in 'Horae'.lower()}")
print()

# Verify: what if we strip punctuation?
import string
clean_terms = [w.strip(string.punctuation) for w in terms if w not in STOP_WORDS]
print(f"Cleaned terms (strip punct): {clean_terms}")

# Now test with cleaned terms
print()
print("=== WITH PUNCTUATION STRIPPED ===")
for c in idx["characters"]:
    if "hour" in c["n"].lower() or "horae" in c["n"].lower():
        s = get_relevance(c["n"], " ".join(clean_terms), clean_terms)
        s_r = get_relevance(c.get("r",""), " ".join(clean_terms), clean_terms)
        print(f"  {c['n']}: name_score={s:.2f} roman_score={s_r:.2f}")

# So the fix is: strip punctuation from each term in get_relevance
print()
print("=== SUMMARY ===")
print("The term 'hours?' (with '?') fails substring match against 'hours'")
print("All search terms score 0.00 against Hours/Horae entries")
print("Hours/Horae are never retrieved, LLM sees no relevant data")
print()
print("Fix: strip string.punctuation from each search term before matching")
