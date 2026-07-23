"""
Mythos AI — Visual Description Generator (04_generate_visual_descriptions.py)

Uses Gemini API to generate visual descriptions of artwork images,
cross-validates against Knowledge Graph depicted characters.

Output: data/artwork_visual_desc.json
  {
    "ART_XXXX": {
      "description": "Gemini's visual description text",
      "figures_found": ["Zeus", ...],
      "validation_issues": ["HALLUCINATION_RISK: ...", "INCOMPLETE: ..."],
      "image_used": "path/to/image.jpg"
    },
    ...
  }
"""

import json
import base64
import time
import os
import re
import sys
from pathlib import Path

GRAPH_FILE = Path("data/knowledge_graph.json")
IMAGE_MAP_FILE = Path("data/artwork_image_map.json")
OUTPUT_FILE = Path("data/artwork_visual_desc.json")
IMAGE_DIR = Path("data/artwork_images")

SYSTEM_PROMPT = """You are a classical mythology expert analyzing ancient Greek and Roman artworks.

Describe ONLY what you see in this image. Be specific and concise (2-4 sentences).

1. Which mythological figure(s) appear — use their EXACT Greek mythological names (e.g. "Zeus", "Heracles", "Athena"). If you cannot confidently identify a figure, describe their appearance instead of guessing a name.
2. What is happening in the scene — one sentence.
3. Key identifying attributes visible — clothing, weapons, animals, symbols (e.g. thunderbolt, aegis, lion skin, caduceus, laurel wreath).

CRITICAL RULES:
- ONLY name figures you are highly confident about based on clear visual evidence.
- If uncertain, say "a figure" or describe attributes.
- Do NOT make up or hallucinate mythological names.
- Be concise: 2-4 sentences total, no more than 300 characters."""


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


import urllib.request as _urllib


def _get_opener():
    """Build url opener with proxy support from env vars."""
    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    if proxy_url:
        proxy = {"http": proxy_url, "https": proxy_url}
        handler = _urllib.ProxyHandler(proxy)
        return _urllib.build_opener(handler)
    return _urllib.build_opener()


def call_gemini(image_path, api_key):
    """Call Gemini API with image, return response text or None."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    suffix = Path(image_path).suffix.lower()
    mime_type = "image/png" if suffix == ".png" else "image/jpeg"

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": image_data}},
                {"text": SYSTEM_PROMPT},
            ]
        }],
        "generationConfig": {
            "temperature": 0.05,
            "maxOutputTokens": 400,
            "topP": 0.95,
        }
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    req = _urllib.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/json")

    opener = _get_opener()
    try:
        with opener.open(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if not candidates:
            reason = result.get("promptFeedback", {}).get("blockReason", "unknown")
            print(f"  [BLOCKED] Reason: {reason}")
            return None
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return text.strip()
    except Exception as e:
        print(f"  [API ERROR] {e}")
        return None


def extract_figures(text, all_char_names):
    """Find which known character names appear in the Gemini response.

    Uses word-boundary matching to avoid false positives like "Ea" matching "area".
    Only matches names with 3+ characters (excludes 2-letter fragments).
    """
    text_lower = text.lower()
    found = set()
    # Sort longest first for correctness
    for name in sorted(all_char_names, key=len, reverse=True):
        if len(name) < 3:
            continue
        n_lower = name.lower()
        # Word-boundary check: ensure name appears as a standalone word
        pattern = re.compile(r'(?<!\w)' + re.escape(n_lower) + r'(?!\w)')
        if pattern.search(text_lower):
            found.add(name)
    return found


def cross_validate(figures_found, expected_depicted, artwork_name):
    """Return list of validation issues."""
    issues = []
    for f in sorted(figures_found - expected_depicted):
        expected_str = ", ".join(sorted(expected_depicted)) if expected_depicted else "(none in KG)"
        issues.append(f"HALLUCINATION_RISK: Gemini mentions '{f}' but KG depicts {expected_str}")
    for e in sorted(expected_depicted - figures_found):
        issues.append(f"INCOMPLETE: Gemini missed '{e}' (in KG depicts list)")
    return issues


def get_depicted_characters(kg, artwork_name):
    """Get set of character names depicted in an artwork per KG."""
    dep_set = set()
    for r in kg.get("relationships", []):
        if r.get("type") != "depicts":
            continue
        src, tgt = r["source"], r["target"]
        if src == artwork_name:
            dep_set.add(tgt)
        if tgt == artwork_name:
            dep_set.add(src)
    return dep_set


def ensure_pil():
    """Make sure we have basic image handling. If Pillow not available, skip checks."""
    try:
        import PIL.Image
        return True
    except ImportError:
        return False


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[FATAL] Set GEMINI_API_KEY environment variable first.")
        sys.exit(1)

    print("=" * 60)
    print("Mythos AI — Visual Description Generator (Gemini)")
    print("=" * 60)

    kg = _load_json(GRAPH_FILE)
    image_map = _load_json(IMAGE_MAP_FILE)

    all_char_names = {c["name"] for c in kg.get("characters", [])}
    print(f"Loaded {len(all_char_names)} characters from KG.")

    # Build artwork_id -> set of depicted characters
    art_depicted = {}
    for artwork in kg["artworks"]:
        art_depicted[artwork["id"]] = get_depicted_characters(kg, artwork["name"])

    # Collect artworks that have images
    to_process = []
    for artwork in kg["artworks"]:
        aid = artwork["id"]
        if aid not in image_map:
            continue
        first_img = Path(image_map[aid][0])
        if not first_img.exists():
            print(f"  [WARN] Missing file: {first_img}")
            continue
        to_process.append((aid, artwork["name"], first_img))

    print(f"Artworks to process: {len(to_process)}")

    # Load existing results (support resume)
    results = {}
    if OUTPUT_FILE.exists():
        results = _load_json(OUTPUT_FILE)
        print(f"Loaded {len(results)} cached results.")

    for idx, (aid, name, img_path) in enumerate(to_process, 1):
        if aid in results and results[aid].get("description"):
            print(f"[{idx}/{len(to_process)}] {name} — cached")
            continue
        if aid in results and not results[aid].get("description"):
            print(f"[{idx}/{len(to_process)}] {name} — retry (null desc)")

        print(f"[{idx}/{len(to_process)}] {name} ({img_path.name})... ", end="")
        sys.stdout.flush()

        text = call_gemini(img_path, api_key)
        if not text:
            print("FAILED (no valid response)")
            results[aid] = {
                "description": None,
                "figures_found": [],
                "validation_issues": ["API call failed or blocked"],
                "image_used": str(img_path),
            }
            _save_json(OUTPUT_FILE, results)
            time.sleep(0.5)
            continue

        print("OK")
        figures = extract_figures(text, all_char_names)
        expected = art_depicted.get(aid, set())
        issues = cross_validate(figures, expected, name)

        results[aid] = {
            "description": text,
            "figures_found": sorted(figures),
            "validation_issues": issues,
            "image_used": str(img_path),
        }

        # Save after each artwork for resume
        _save_json(OUTPUT_FILE, results)
        time.sleep(2.0)  # Rate limiting: ~30 RPM safe for free tier

    # Summary
    total_desc = sum(1 for v in results.values() if v.get("description"))
    total_issues = sum(len(v.get("validation_issues", [])) for v in results.values())
    total_hall = sum(1 for v in results.values() for iss in v.get("validation_issues", []) if "HALLUCINATION" in iss)
    total_inc = sum(1 for v in results.values() for iss in v.get("validation_issues", []) if "INCOMPLETE" in iss)

    print()
    print("=" * 60)
    print("Summary")
    print(f"  Total artworks processed:  {len(results)}")
    print(f"  With valid descriptions:   {total_desc}")
    print(f"  Total validation issues:   {total_issues}")
    print(f"  Hallucination risks:       {total_hall}")
    print(f"  Incomplete flags:          {total_inc}")
    print(f"  Output: {OUTPUT_FILE.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
