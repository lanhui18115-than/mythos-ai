"""
LLM Enhancer for crossword clues and explanations.
Uses DeepSeek API (OpenAI-compatible).
"""

import os
import json
import hashlib
import time
from pathlib import Path
from openai import OpenAI

CACHE_FILE = Path("data/llm_cache.json")
SLEEP = float(os.getenv("LLM_SLEEP", "0.05"))  # seconds between calls


class LLMEnhancer:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url=(os.getenv("LLM_BASE_URL", "https://api.deepseek.com") + "/v1"),
        )
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.cache = self._load_cache()

    def _load_cache(self):
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return {}

    def _save_cache(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _call_llm(self, prompt, cache_key=None, max_retries=2):
        if cache_key and cache_key in self.cache:
            return self.cache[cache_key]

        for attempt in range(max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=400,
                )
                result = resp.choices[0].message.content.strip()

                if cache_key:
                    self.cache[cache_key] = result
                    self._save_cache()

                return result

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise e

    def _make_cache_key(self, *parts):
        raw = "||".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def enhance_clue(self, answer, clue, context=""):
        if not clue or len(clue) < 3:
            return clue

        prompt = f"""You are improving crossword clues for a Greek mythology puzzle.
Given the answer word, current clue, and background context, rewrite the clue.

Rules:
- Keep it 5-25 words
- Do NOT include the answer word
- Make it specific, natural, and solvable
- Add a concrete mythological reference if possible
- Output ONLY the rewritten clue text, nothing else

Answer: {answer}
Current clue: {clue}
Context: {context[:500]}

Rewritten clue:"""

        cache_key = self._make_cache_key("enhance", answer, clue)
        try:
            result = self._call_llm(prompt, cache_key)
            result = result.strip().strip('"').strip("'")
            if len(result) < 5 or len(result) > 200:
                return clue
            if result.lower() == answer.lower():
                return clue
            return result
        except Exception as e:
            print(f"  [LLM] enhance_clue failed for {answer}: {e}")
            return clue

    def generate_explanation(self, answer, clue, context=""):
        prompt = f"""Write a short Chinese explanation (2-3 sentences) about this Greek mythology crossword answer.
Explain who/what this figure, place, or concept is and its mythological significance.
Write naturally for Chinese students learning about Greek mythology.

Answer: {answer}
Clue: {clue}
Context: {context[:500]}

Chinese explanation:"""

        cache_key = self._make_cache_key("explain", answer)
        try:
            result = self._call_llm(prompt, cache_key)
            if len(result) < 10:
                return ""
            return result.strip()
        except Exception as e:
            print(f"  [LLM] generate_explanation failed for {answer}: {e}")
            return ""
