"""
quiz_enhancer.py — LLM-enhanced quiz questions.

Enhances distractors (opts) and explanations (exp) via LLM,
keeping answers KG-validated. Falls back to originals on failure.

Usage:
  set DEEPSEEK_API_KEY=sk-...
  python scripts/quiz_enhancer.py
  python scripts/quiz_enhancer.py --limit 30    # test on 30 questions
  python scripts/quiz_enhancer.py --sets 5      # enhance first 5 sets only

Config (env vars):
  LLM_API_KEY              your API key (generic)
  DEEPSEEK_API_KEY         DeepSeek key (fallback)
  OPENAI_API_KEY           OpenAI key (fallback)
  LLM_MODEL                model name (default: deepseek-chat)
  LLM_BASE_URL             API base URL (default: https://api.deepseek.com)
"""

import json, re, os, sys, time
from pathlib import Path

OUTPUT = Path("output/quiz.html")
KG_PATH = Path("data/knowledge_graph.json")
BATCH = 5  # questions per API call
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

# ── KG loader ─────────────────────────────────────────────────────

def load_kg():
    return json.loads(KG_PATH.read_text(encoding="utf-8"))

def _ctx(s, n=150):
    if len(s) <= n:
        return s
    i = s[:n].rfind(" ")
    return s[:i] + "..." if i > 30 else s[:n] + "..."

# ── HTML I/O ───────────────────────────────────────────────────────

def read_sets(path):
    html = path.read_text(encoding="utf-8")
    m = re.search(r"var ALL_SETS = (\[[\s\S]*?\]);", html)
    if not m:
        raise ValueError("ALL_SETS not found")
    return html, json.loads(m.group(1))

def write_sets(path, html, sets):
    j = json.dumps(sets, ensure_ascii=False)
    html = re.sub(r"var ALL_SETS = \[[\s\S]*?\];", "var ALL_SETS = " + j + ";", html)
    path.write_text(html, encoding="utf-8")

# ── KG context ─────────────────────────────────────────────────────

def kg_context(q, kg):
    txt = q.get("q", "")
    parts = []
    myth = None
    for m in kg["myths"]:
        if m["name"] in txt:
            myth = m
            break
    if not myth:
        for m in kg["myths"]:
            for ch in m.get("key_characters", []):
                if ch in txt and ch != q.get("ans", ""):
                    myth = m
                    break
            if myth:
                break

    if myth:
        parts.append(f"Myth: {myth['name']}")
        parts.append(f"Summary: {_ctx(myth.get('summary', ''), 200)}")
        chars = myth.get("key_characters", [])
        if chars:
            parts.append("Characters: " + ", ".join(chars[:8]))
        rels = []
        for r in kg["relationships"]:
            if r.get("source") in chars and r.get("target") in chars:
                rt = r.get("type", "")
                if rt in ("killed_by","parent_of","spouse_of","lover_of",
                          "opponent_of","fought_against","resides_in","child_of"):
                    rels.append(f"{r['source']} --[{rt}]--> {r['target']}")
        if rels:
            parts.append("Relationships: " + "; ".join(rels[:6]))

    ans = q.get("ans", "")
    for c in kg["characters"]:
        if c["name"] == ans:
            info = f"Answer: {ans}"
            doms = c.get("domains", [])
            if doms:
                info += f" (domains: {', '.join(doms[:3])})"
            rn = c.get("roman_name", "")
            if rn and rn != ans:
                info += f" (Roman: {rn})"
            parts.append(info)
            break
    return "\n".join(parts)

# ── LLM call ────────────────────────────────────────────────────────

def call_llm(system_prompt, user_prompt, retries=3):
    import openai
    import time
    api_key = LLM_API_KEY or os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise ValueError("Set LLM_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url=LLM_BASE_URL)
    last_err = None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=3000,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                wait = 2 ** attempt * 5
                print(f"  Retry {attempt+1}/{retries} after {wait}s: {e}")
                time.sleep(wait)
    raise last_err

# ── Prompt builder (batch) ──────────────────────────────────────────

def build_batch_prompt(batch, kg):
    items = []
    for q in batch:
        ctx = kg_context(q, kg)
        is_parent_q = "parent" in q.get("q", "").lower()
        if q["t"] == "mc" and not is_parent_q:
            instructions = "Replace wrong options with more plausible alternatives. Keep 4 options total."
        else:
            instructions = "This question has fixed options — only enhance the explanation."
        items.append(
            f"--- Question (type: {q['t']}) ---\n"
            f"{json.dumps(q, ensure_ascii=False)}\n"
            f"--- Context ---\n{ctx}\n"
            f"--- Instruction ---\n{instructions}"
        )
    type_note = (
        "For 'mc' questions: return 'opts' (array of 4 strings) and 'exp' (string).\n"
        "For 'tf' and 'sa' questions: return only 'exp' (string), do NOT include 'opts'.\n"
        "Never change the correct answer."
    )
    return (
        "Enhance each quiz question below. Keep answers EXACTLY as given.\n"
        + type_note + "\n\n" +
        "\n\n".join(items) +
        "\n\nReturn a JSON object with key \"questions\" — an array. "
        "Each element has 'exp' (string). For mc questions, also include 'opts' (array of 4 strings)."
    )

# ── Validator ────────────────────────────────────────────────────────

def validate_q(orig, result, kg):
    errs = []
    is_parent_q = "parent" in orig.get("q", "").lower()
    if orig["t"] == "mc" and not is_parent_q:
        if not isinstance(result.get("opts"), list) or len(result["opts"]) != 4:
            errs.append("opts must be array of 4")
            return errs
        if orig["ans"] not in result["opts"]:
            errs.append(f"ans '{orig['ans']}' not in opts")
            return errs
        if len(set(result["opts"])) != 4:
            errs.append("duplicate opts")
            return errs
        all_entities = {c["name"] for c in kg["characters"]}
        all_entities |= {p["name"] for p in kg.get("places", [])}
        for o in result["opts"]:
            if o not in all_entities:
                errs.append(f"unknown entity: {o}")
                return errs
    if not result.get("exp") or len(result["exp"]) < 15:
        errs.append("exp too short")
    return errs

# ── Main ────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max questions to enhance (test)")
    ap.add_argument("--sets", type=int, default=0, help="enhance only first N sets")
    args = ap.parse_args()

    kg = load_kg()
    html, all_sets = read_sets(OUTPUT)
    print(f"Loaded {len(all_sets)} sets")

    total_enhanced = 0
    total_failed = 0
    total_skipped = 0
    total_all = sum(len(s) for s in all_sets)

    for si, questions in enumerate(all_sets):
        if args.sets and si >= args.sets:
            break

        # Collect non-match, non-already-enhanced questions
        to_enhance = []
        indices = []
        for qi, q in enumerate(questions):
            if args.limit and total_enhanced + total_failed + total_skipped >= args.limit:
                break
            if q["t"] == "match":
                # Even match questions benefit from a better explanation
                # We just don't change their options
                pass
            if q.get("enhanced"):
                total_skipped += 1
                continue
            to_enhance.append(q)
            indices.append(qi)

        if not to_enhance:
            continue

        # Process in batches
        for start in range(0, len(to_enhance), BATCH):
            batch = to_enhance[start:start+BATCH]
            idxs = indices[start:start+BATCH]
            try:
                prompt = build_batch_prompt(batch, kg)
                result = call_llm(
                    "You are a Greek mythology quiz editor. You never change the correct answer. "
                    "All entities must be real Greek mythology figures. Return valid JSON.",
                    prompt
                )
                results = result.get("questions", [result])
                for qi, q in enumerate(batch):
                    if qi >= len(results):
                        total_failed += 1
                        continue
                    errs = validate_q(q, results[qi], kg)
                    if errs:
                        total_failed += 1
                        continue
                    is_parent_q = "parent" in q.get("q", "").lower()
                    if q["t"] == "mc" and not is_parent_q:
                        q["opts"] = results[qi]["opts"]
                    q["exp"] = results[qi]["exp"]
                    q["enhanced"] = True
                    total_enhanced += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  Batch error: {e}")
                total_failed += len(batch)

            done = total_enhanced + total_failed + total_skipped
            if done % 20 == 0:
                print(f"  {done}/{total_all}  (ok={total_enhanced} fail={total_failed})")
                write_sets(OUTPUT, html, all_sets)  # periodic save

    write_sets(OUTPUT, html, all_sets)
    print(f"\nDone: {total_enhanced} enhanced, {total_failed} failed, {total_skipped} skipped")
    print(f"Saved to {OUTPUT}")

if __name__ == "__main__":
    main()
