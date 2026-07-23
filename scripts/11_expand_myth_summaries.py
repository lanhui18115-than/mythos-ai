"""
Mythos AI — 神话摘要扩写 (11_expand_myth_summaries.py)

基于教材原文扩展每个 myth 的 summary 为详细中文摘要。
输入: knowledge_graph.json + data/chapter_texts/chapter_*.txt
输出: data/enhanced_myth_summaries.json

Textbook First: 摘要内容严格锚定教材原文章节页码。
"""

import json
import hashlib
import re
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

# Handle console encoding for Chinese output
if sys.stdout.encoding.lower() in ('gbk', 'gb2312', 'cp936'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_FILE = DATA_DIR / "knowledge_graph.json"
CHAPTER_DIR = DATA_DIR / "chapter_texts"
OUTPUT_FILE = DATA_DIR / "enhanced_myth_summaries.json"
CACHE_FILE = DATA_DIR / "llm_cache.json"

SLEEP = float(os.getenv("LLM_SLEEP", "0.05"))


class MythEnhancer:
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
                    temperature=0.3,
                    max_tokens=1500,
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

    def expand_summary(self, myth_name, current_summary, textbook_excerpt, key_chars):
        prompt = f"""You are a classical mythology textbook author. Expand the following myth summary into a detailed Chinese academic summary (8-15 sentences).

Guidelines:
- Base your expansion on the textbook excerpt provided below
- Include key characters, setting, causes, major events, and outcomes
- Keep the tone academic but accessible for undergraduate students
- Include specific details from the textbook excerpt
- Do not invent facts not supported by the textbook excerpt
- Write in Chinese (中文)
- The existing summary is your starting point

Myth name: {myth_name}

Key characters: {', '.join(key_chars) if key_chars else 'N/A'}

Existing summary: {current_summary}

Textbook excerpt:
{textbook_excerpt[:2500]}

Expanded Chinese summary:"""

        ck = self._cache_key("myth_expand|" + myth_name)
        return self._call_llm(prompt, ck)


def load_chapter_pages():
    """Pre-index all chapter texts by printed page number."""
    chapter_pages = {}
    for ch_file in sorted(CHAPTER_DIR.glob("chapter_*.txt")):
        ch_num = int(re.search(r"(\d+)", ch_file.stem).group(1))
        text = ch_file.read_text(encoding="utf-8")
        pages = {}
        current_page = None
        current_lines = []

        for line in text.split("\n"):
            m = re.search(r"\[PRINTED_PAGE (\d+)\]", line)
            if m:
                if current_page is not None:
                    pages[current_page] = "\n".join(current_lines).strip()
                current_page = int(m.group(1))
                current_lines = [line]
            else:
                if current_page is not None:
                    current_lines.append(line)

        if current_page is not None:
            pages[current_page] = "\n".join(current_lines).strip()

        chapter_pages[ch_num] = pages

    return chapter_pages


def extract_relevant_text(chapter_pages, chapters, mentioned_pages):
    """Extract textbook text around the mentioned pages for a myth."""
    excerpts = []
    for ch in chapters:
        if ch not in chapter_pages:
            continue
        ch_text = chapter_pages[ch]
        for pg in mentioned_pages:
            if pg in ch_text:
                excerpts.append(f"[Chapter {ch}, Page {pg}]\n{ch_text[pg][:800]}")
            else:
                # Try nearby pages
                for offset in range(-1, 2):
                    nearby = pg + offset
                    if nearby in ch_text:
                        excerpts.append(f"[Chapter {ch}, Page {nearby} (near ref p.{pg})]\n{ch_text[nearby][:600]}")
                        break
    return "\n\n".join(excerpts[:5])  # Limit to 5 excerpts


def main():
    print("=" * 60)
    print("Mythos AI — 神话摘要扩写")
    print("=" * 60)

    if not GRAPH_FILE.exists():
        print(f"[ERROR] 知识图谱未找到: {GRAPH_FILE}")
        return

    kg = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    myths = kg.get("myths", [])
    print(f"已读取 {len(myths)} 个神话")

    print("加载章节文本索引...")
    chapter_pages = load_chapter_pages()
    print(f"已索引 {len(chapter_pages)} 章的页面内容")

    enhancer = MythEnhancer()

    existing = {}
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        print(f"已有 {len(existing)} 个神话的扩写摘要")

    to_process = [m for m in myths if m["name"] not in existing]
    print(f"待处理: {len(to_process)} 个神话")

    if not to_process:
        print("所有神话已完成，无需处理。")
        return

    results = dict(existing)
    total = len(to_process)

    for i, myth in enumerate(to_process):
        name = myth["name"]
        summary = myth.get("summary", "")
        key_chars = myth.get("key_characters", [])
        chapters = myth.get("chapters", [])
        mentioned = myth.get("mentioned_pages", [])

        print(f"\n[{i+1}/{total}] {name}...")

        textbook_excerpt = extract_relevant_text(chapter_pages, chapters, mentioned)
        if not textbook_excerpt:
            print(f"  [SKIP] 未找到教材原文，跳过")
            results[name] = summary
            continue

        expanded = enhancer.expand_summary(name, summary, textbook_excerpt, key_chars)
        if expanded and len(expanded) > len(summary):
            results[name] = expanded
            print(f"  OK ({len(expanded)} 字符)")
        else:
            print(f"  [FALLBACK] 使用原始摘要")
            results[name] = summary

        time.sleep(SLEEP)

        # Save every 10 myths
        if (i + 1) % 10 == 0:
            OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [SAVED] 已保存 {len(results)}/{total}")

    OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    expanded_count = sum(1 for v in results.values() if len(v) > 100)
    print(f"\n{'=' * 60}")
    print(f"完成! {expanded_count}/{len(results)} 个神话已扩写")
    print(f"输出: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
