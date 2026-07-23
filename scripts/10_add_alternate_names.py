"""
Mythos AI — 角色异体拼名增强 (10_add_alternate_names.py)

为 knowledge_graph.json 中每个角色生成已知异体拼法/转写变体。
输出: data/alternate_names.json

使用 DeepSeek API (复用 llm_enhancer.py 的缓存机制)。
"""

import json
import hashlib
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_FILE = DATA_DIR / "knowledge_graph.json"
OUTPUT_FILE = DATA_DIR / "alternate_names.json"
CACHE_FILE = DATA_DIR / "llm_cache.json"

BATCH_SIZE = 40
SLEEP = float(os.getenv("LLM_SLEEP", "0.05"))


class NameEnhancer:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url=(os.getenv("LLM_BASE_URL", "https://api.deepseek.com") + "/v1"),
        )
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.cache = self._load_cache()

    def _load_cache(self):
        if CACHE_FILE.exists():
            raw = CACHE_FILE.read_text(encoding="utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _cache_key(self, text):
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def _call_llm(self, prompt, cache_key, max_retries=2):
        if cache_key in self.cache:
            return self.cache[cache_key]

        for attempt in range(max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2000,
                )
                result = resp.choices[0].message.content.strip()
                self.cache[cache_key] = result
                self._save_cache()
                return result
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  [ERROR] LLM call failed: {e}")
                    return None

    def batch_get_variants(self, names):
        prompt = f"""You are a classical mythology scholar. For each Greek name below, provide known alternate spellings or transliterations found in academic literature.

Rules:
- Only include variants actually used in English-language scholarship
- Include Latinized forms if they differ significantly
- Include alternate Greek transliterations (e.g. k/c, ai/ae, os/us, etc.)
- If a name has no known variants, use an empty array
- Output ONLY a valid JSON object, nothing else

Names:
{chr(10).join(f'  {i+1}. {n}' for i, n in enumerate(names))}

JSON output:"""

        cache_key = self._cache_key("alternate_names|" + "|".join(names))
        result = self._call_llm(prompt, cache_key)
        if not result:
            return {}

        try:
            cleaned = result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"  [WARN] Failed to parse LLM output for batch, trying per-name fallback")
            return self._fallback_per_name(names)

    def _fallback_per_name(self, names):
        result = {}
        for name in names:
            prompt = f"What are the known alternate spellings of the Greek mythological name '{name}'? Output ONLY a JSON array of strings, or [] if none."
            ck = self._cache_key("alt_fallback|" + name)
            resp = self._call_llm(prompt, ck)
            if resp:
                try:
                    cleaned = resp.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        result[name] = parsed
                    else:
                        result[name] = []
                except json.JSONDecodeError:
                    result[name] = []
            else:
                result[name] = []
            time.sleep(SLEEP)
        return result


def main():
    print("=" * 60)
    print("Mythos AI — 角色异体拼名增强")
    print("=" * 60)

    if not GRAPH_FILE.exists():
        print(f"[ERROR] 知识图谱文件未找到: {GRAPH_FILE}")
        return

    kg = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    characters = kg.get("characters", [])
    print(f"已读取 {len(characters)} 个角色")

    enhancer = NameEnhancer()

    all_names = [c["name"] for c in characters]
    existing = {}
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        print(f"已有 {len(existing)} 个角色的异体拼名数据")

    # Only process names not yet in output
    to_process = [n for n in all_names if n not in existing]
    print(f"待处理: {len(to_process)} 个角色")

    if not to_process:
        print("所有角色已完成，无需处理。")
        return

    results = dict(existing)
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]

    for bi, batch in enumerate(batches):
        print(f"\n批次 {bi+1}/{len(batches)} ({len(batch)} 个角色)...")
        batch_result = enhancer.batch_get_variants(batch)
        for name, variants in batch_result.items():
            if isinstance(variants, list) and len(variants) > 0:
                results[name] = variants
            else:
                results[name] = []
        time.sleep(SLEEP)

        # Save after each batch
        OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        done = sum(1 for v in results.values() if len(v) > 0)
        print(f"  进度: {len(results)}/{len(all_names)} (有异体: {done})")

    # Final save
    OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    total_with = sum(1 for v in results.values() if len(v) > 0)
    print(f"\n{'=' * 60}")
    print(f"完成! {total_with}/{len(all_names)} 个角色有异体拼名")
    print(f"输出: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
