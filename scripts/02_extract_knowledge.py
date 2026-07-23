"""
程序 2/3：用 AI 从每章文字中提取结构化知识

支持 DeepSeek、OpenAI 等兼容接口的 LLM 服务。

功能：
  1. 读取上一步提取的章节文字文件
  2. 发送给 LLM 进行结构化提取
  3. 解析 AI 返回的 JSON
  4. 每章保存为一个 .json 文件

输出位置：data/knowledge/chapter_XX.json

注意事项：
  - 需要先配置 .env 文件中的 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
  - DeepSeek: LLM_BASE_URL=https://api.deepseek.com  LLM_MODEL=deepseek-chat
  - OpenAI:   LLM_BASE_URL=https://api.openai.com     LLM_MODEL=gpt-4o-mini
  - 每次调用 API 会间隔 2 秒避免频率限制
  - 如果某章较长会自动拆分成多段处理
"""

import json
import time
import os
import sys
from pathlib import Path
import re

from openai import OpenAI
from dotenv import load_dotenv

# ── 配置 ──────────────────────────────────────────────
CHAPTER_TEXT_DIR = Path(__file__).parent.parent / "data" / "chapter_texts"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "knowledge"
ENV_FILE = Path(__file__).parent.parent / ".env"

# 每段最大字符数（降低以减少每段输出量，防止被 token 上限截断）
MAX_CHUNK_CHARS = 15000

# 每段最多重试次数
MAX_RETRIES = 3

# LLM 最大输出 token（加大以容纳 major_myths + evidence_level 等新字段）
MAX_OUTPUT_TOKENS = 12000


def clean_json_string(raw: str) -> str:
    """清理 LLM 返回的原始 JSON 字符串"""
    if not raw:
        return ""
    raw = raw.strip()
    # 移除 markdown 代码块标记
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def try_fix_truncated_json(raw: str) -> str:
    """
    尝试修复被截断的 JSON。
    使用状态机追踪括号嵌套，按 LIFO 顺序补全缺失的闭合符号。
    """
    if not raw:
        return ""
    raw = raw.rstrip()
    if raw.endswith("}"):
        return raw

    # 状态机：追踪括号嵌套，忽略字符串内的内容
    stack = []
    in_string = False
    escape = False

    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("{")
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif ch == "[":
            stack.append("[")
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    # 若截断点在字符串内，补全引号
    if in_string:
        raw += '"'

    # 移除末尾逗号
    raw = raw.rstrip().rstrip(",")

    # 按 LIFO 顺序补全缺失的闭合符号
    for s in reversed(stack):
        raw += "}" if s == "{" else "]"

    return raw


# 全局统计
_fix_count = 0

def extract_chunk(chapter_num: int, text: str, client: OpenAI, model: str) -> dict | None:
    """处理单个文本块，带重试机制"""
    global _fix_count
    user_prompt = f"Chapter {chapter_num}:\n\n{text}"

    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            print(f"    重试第 {attempt} 次...")
            time.sleep(3 * attempt)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=MAX_OUTPUT_TOKENS,
            )

            raw = response.choices[0].message.content
            raw = clean_json_string(raw)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                fixed = try_fix_truncated_json(raw)
                try:
                    data = json.loads(fixed)
                    _fix_count += 1
                    print(f"    [修复] JSON 截断已自动补全 (第{_fix_count}次)")
                except json.JSONDecodeError as e:
                    print(f"    [错误] JSON 解析失败: {e}")
                    print(f"    响应长度: {len(raw)} 字符")
                    print(f"    响应前 300 字符: {raw[:300]}")
                    if attempt < MAX_RETRIES:
                        continue
                    return None

            return data

        except Exception as e:
            print(f"    [错误] API 调用失败: {e}")
            if attempt < MAX_RETRIES:
                continue
            return None

    return None


# ── 系统提示词（提取规则） ─────────────────────────
SYSTEM_PROMPT = """You are a precise knowledge extraction system for the textbook "Classical Mythology" (11th edition) by Morford, Lenardon, and Sham.

Your task: Extract ALL mythological knowledge from the given chapter text. Output ONLY valid JSON.

TEXT FORMAT:
- Each page begins with [PDF_PAGE N] and [PRINTED_PAGE N] markers.
- Use PRINTED_PAGE numbers for all page references in your output.

ENTITY TYPES TO EXTRACT:

1. characters — gods, heroes, mortals, monsters, Titans, nymphs, etc.
   Fields:
   - name (Greek name, NO parentheses — use description to distinguish)
   - roman_name (string, if mentioned)
   - epithets (list of strings)
   - domains (list of what they govern)
   - symbols (list)
   - type (god/hero/mortal/monster/titan/nymph/other)
   - description (1-2 sentences; if multiple characters share a name, include disambiguating info like parentage here)
   - major_myths (list of myth names this character participates in, from this chapter)
   - mentioned_pages (list of printed page numbers)

2. myths — complete stories, episodes, or narrative traditions
   Fields: name, summary (2-3 sentences), key_characters (list of character names), mentioned_pages

3. places — real or mythological locations
   Fields: name, type (real/mythological/underworld/etc.), description, mentioned_pages

4. concepts — abstract ideas, themes, religious concepts, literary terms
   Fields: name, definition (1-2 sentences), mentioned_pages

5. artworks — sculptures, vases, paintings, mosaics, buildings described in the text
   Fields: name, type (sculpture/vase/painting/mosaic/building/other), description, mentioned_pages

RELATIONSHIPS TO EXTRACT:

For every meaningful connection between entities, extract:
- source: name of the source entity (must be a name used in this chapter's entity list)
- target: name of the target entity (must be a name used in this chapter's entity list)
- type: one of (parent_of, child_of, spouse_of, sibling_of, lover_of, roman_equivalent, appears_in, participates_in, depicted_in, introduced_in, associated_with, created_by, killed_by, fought_against, transformed_into, loved_by, hated_by, ruled_over, founded, resides_in, companion_of, opponent_of, identified_with)
- description: brief context (1 sentence)
- page: printed page number
- chapter: chapter number (integer)
- evidence_level: one of "explicit" (directly stated in text), "implicit" (reasonably inferred from text), "supplementary" (do not use)

CRITICAL RULES:
1. ONLY extract information explicitly stated in the provided chapter text.
2. Do NOT add outside knowledge from other sources.
3. Greek names are the primary name; Roman names go in the roman_name field.
4. If a character appears but no details are given, still include them with a minimal entry.
5. Do not make up page numbers — use only the [PRINTED_PAGE N] markers from the text.
6. Be concise in descriptions to keep JSON compact.
7. OUTPUT VALID JSON ONLY — no explanations, no markdown.
8. NEVER use parentheses in character names. For characters with the same name (e.g. two characters both named "Ajax"), use the description field to differentiate (e.g. "Son of Telamon, Greek hero" vs. "Son of Oïleus, Locrian prince"). Use standard epithets like "Telamonian Ajax" or "Ajax the Greater" if the text supports it.
9. Always fill the major_myths field for every character — list all myths from this chapter that the character appears in.
10. Always fill chapter and evidence_level for every relationship.

OUTPUT FORMAT:
{
  "characters": [ { "name": "...", "roman_name": "...", "epithets": [], "domains": [], "symbols": [], "type": "...", "description": "...", "major_myths": [], "mentioned_pages": [] } ],
  "myths": [ { "name": "...", "summary": "...", "key_characters": [], "mentioned_pages": [] } ],
  "places": [ { "name": "...", "type": "...", "description": "...", "mentioned_pages": [] } ],
  "concepts": [ { "name": "...", "definition": "...", "mentioned_pages": [] } ],
  "artworks": [ { "name": "...", "type": "...", "description": "...", "mentioned_pages": [] } ],
  "relationships": [ { "source": "...", "target": "...", "type": "...", "description": "...", "page": 0, "chapter": 0, "evidence_level": "explicit" } ]
}"""


def get_chapter_title(chapter_num: int) -> str:
    """从章节文字文件的第一行推断标题"""
    filepath = CHAPTER_TEXT_DIR / f"chapter_{chapter_num:02d}.txt"
    if not filepath.exists():
        return ""
    text = filepath.read_text(encoding="utf-8")[:500]
    m = re.search(r"Chapter\s+\d+\s+(.+?)(?:\n|$)", text)
    if m:
        return m.group(1).strip()
    return ""


def count_tokens(text: str) -> int:
    """粗略估算 token 数（英文约 4 字符 = 1 token）"""
    return len(text) // 4


def split_chapter_text(text: str, max_chars: int) -> list[str]:
    """如果章节文字太长，按段落边界拆分成多段"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current += ("\n\n" + para) if current else para
    if current:
        chunks.append(current)
    return chunks


def merge_chunk_results(results: list[dict]) -> dict:
    """合并多个分段提取的结果"""
    if not results:
        return {}
    if len(results) == 1:
        return results[0]

    merged = {
        "chapter": None,
        "title": "",
        "characters": [],
        "myths": [],
        "places": [],
        "concepts": [],
        "artworks": [],
        "relationships": [],
    }

    for category in ["characters", "myths", "places", "concepts", "artworks"]:
        seen_names = {}
        for result in results:
            for entity in result.get(category, []):
                name = entity.get("name", "")
                if not name:
                    continue
                key = name.strip().lower()
                if key in seen_names:
                    existing = seen_names[key]
                    existing["mentioned_pages"] = sorted(set(
                        existing.get("mentioned_pages", []) + entity.get("mentioned_pages", [])
                    ))
                    if not existing.get("description") and entity.get("description"):
                        existing["description"] = entity["description"]
                    if not existing.get("roman_name") and entity.get("roman_name"):
                        existing["roman_name"] = entity["roman_name"]
                    if "major_myths" in existing and "major_myths" in entity:
                        existing_mm = set(existing["major_myths"])
                        existing_mm.update(entity["major_myths"])
                        existing["major_myths"] = sorted(existing_mm)
                else:
                    seen_names[key] = dict(entity)
        merged[category] = list(seen_names.values())

    seen_rels = set()
    for result in results:
        for rel in result.get("relationships", []):
            key = (rel.get("source", "").strip().lower(),
                   rel.get("target", "").strip().lower(),
                   rel.get("type", ""))
            if key not in seen_rels:
                seen_rels.add(key)
                merged["relationships"].append(rel)

    return merged


def extract_chapter(chapter_num: int, client: OpenAI, model: str) -> dict | None:
    """提取单一章节的知识"""
    filepath = CHAPTER_TEXT_DIR / f"chapter_{chapter_num:02d}.txt"
    if not filepath.exists():
        print(f"  [跳过] 找不到第 {chapter_num} 章文字文件")
        return None

    text = filepath.read_text(encoding="utf-8")
    if not text.strip():
        print(f"  [跳过] 第 {chapter_num} 章文字为空")
        return None

    title = get_chapter_title(chapter_num)
    print(f"\n  正在处理第 {chapter_num} 章: {title or ''}")
    print(f"  文字长度: {len(text)} 字符 (约 {count_tokens(text)} tokens)")

    chunks = split_chapter_text(text, MAX_CHUNK_CHARS)
    if len(chunks) > 1:
        print(f"  拆分为 {len(chunks)} 段处理 (每段约 {MAX_CHUNK_CHARS} 字符)")

    results = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"  处理第 {i+1}/{len(chunks)} 段...")
        else:
            print(f"  发送给 AI 提取中...")

        data = extract_chunk(chapter_num, chunk, client, model)
        if data:
            results.append(data)
        else:
            print(f"  [失败] 第 {i+1} 段所有重试均失败")
            return None

        if i < len(chunks) - 1:
            time.sleep(2)

    if not results:
        print(f"  [失败] 第 {chapter_num} 章所有尝试均失败")
        return None

    merged = merge_chunk_results(results)
    merged["chapter"] = chapter_num
    if title:
        merged["title"] = title

    char_count = len(merged.get("characters", []))
    myth_count = len(merged.get("myths", []))
    rel_count = len(merged.get("relationships", []))
    print(f"  提取结果: {char_count} 个人物, {myth_count} 个神话, {rel_count} 条关系")

    return merged


def main():
    """主函数：处理所有章节"""
    print("=" * 60)
    print("Mythos AI — 章节知识提取工具")
    print("=" * 60)

    # 解析命令行参数
    force = "--force" in sys.argv

    load_dotenv(ENV_FILE)
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key or "your-key" in api_key:
        print(f"\n[错误] 未配置 LLM API Key！")
        print(f"  请编辑 {ENV_FILE} 文件")
        print(f"  将 LLM_API_KEY 设为你的真实 Key")
        print()
        print(f"  DeepSeek 申请地址: https://platform.deepseek.com/api_keys")
        return

    client = OpenAI(api_key=api_key, base_url=base_url)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = list(CHAPTER_TEXT_DIR.glob("chapter_*.txt"))
    if not txt_files:
        print(f"\n[错误] 未找到章节文字文件！")
        print(f"  请先运行 01_extract_pdf_text.py")
        print(f"  文件应位于: {CHAPTER_TEXT_DIR}")
        return

    chapter_nums = sorted([
        int(f.stem.split("_")[1]) for f in txt_files
        if f.stem.startswith("chapter_")
    ])
    print(f"\n找到 {len(chapter_nums)} 个章节文件: {chapter_nums}")
    print(f"API 地址: {base_url}")
    print(f"处理模型: {model}")
    if force:
        print("🔧 --force 模式: 将重新提取所有章节")
    else:
        existing = list(OUTPUT_DIR.glob("chapter_*.json"))
        if existing:
            print(f"⚠️  发现 {len(existing)} 个已有提取文件，将跳过它们")
            print(f"   如需重新提取，请删除 data/knowledge/ 下的文件或加 --force 参数")
    print("=" * 60)

    successful = 0
    for ch_num in chapter_nums:
        out_path = OUTPUT_DIR / f"chapter_{ch_num:02d}.json"
        if out_path.exists() and not force:
            print(f"\n[跳过] 第 {ch_num} 章已提取 (文件已存在)")
            successful += 1
            continue

        result = extract_chapter(ch_num, client, model)
        if result:
            # 先保存到临时文件，确保写入完整
            out_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  已保存: {out_path.name}")
            successful += 1
        else:
            print(f"  [失败] 第 {ch_num} 章提取失败")

        time.sleep(2)

    print("\n" + "=" * 60)
    print(f"处理完成！成功提取 {successful}/{len(chapter_nums)} 章")
    print(f"输出目录: {OUTPUT_DIR}")

    if successful == len(chapter_nums):
        print("\n所有章节已提取完毕，可以运行 03_merge_knowledge.py 合并知识图谱！")


if __name__ == "__main__":
    main()
