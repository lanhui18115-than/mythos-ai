"""
Mythos AI — AI Tutor Backend Server

RAG pipeline: frontend question -> knowledge graph retrieval -> LLM API -> answer + references

Usage:
    py -3 scripts/ai_tutor_server.py

Requires .env file with:
    LLM_API_KEY=<your_api_key>
    LLM_BASE_URL=https://api.deepseek.com  (or any OpenAI-compatible API)
    LLM_MODEL=deepseek-chat
"""

import json
import os
import re
import string
import threading
from pathlib import Path

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

DATA_DIR = Path("data")
INDEX_PATH = DATA_DIR / "ai_tutor_index.json"
DEFAULT_PORT = 5800

app = Flask(__name__)
CORS(app)

tutor_index = None
name_map = None
index_lock = threading.Lock()

STOP_WORDS = {
    "what", "is", "the", "of", "a", "an", "in", "on", "at", "to", "for",
    "with", "by", "about", "does", "do", "can", "tell", "me", "give", "name",
    "list", "find", "show", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "not", "no", "nor", "but", "or", "and", "if",
    "so", "as", "all", "any", "each", "every", "some", "many", "much",
    "more", "most", "other", "own", "same", "too", "very", "just", "also",
    "well", "even", "still", "already", "now", "then", "here", "there",
    "only", "really", "quite", "who", "whom", "whose", "which", "that",
    "this", "these", "those", "it", "its", "you", "your", "they", "them",
    "their", "he", "him", "his", "she", "her", "we", "us", "our", "my",
    "mine", "yourself", "himself", "herself", "itself", "themselves"
}

# Synonym expansion for common query terms (Approach A)
SYNONYM_MAP = {
    "priest": ["priest", "patron", "hierophant", "minister", "priestess"],
    "priests": ["priest", "patron", "hierophant"],
    "led": ["led", "guided", "conducted", "lead"],
    "guide": ["guide", "lead", "escort"],
    "novices": ["novices", "initiate", "beginner", "neophyte"],
    "novice": ["novice", "initiate", "beginner"],
    "initiate": ["initiate", "novice", "beginner"],
    "rites": ["rites", "ritual", "ceremony", "mysteries", "rite"],
    "rite": ["rite", "ritual", "ceremony", "mystery"],
    "ritual": ["ritual", "ceremony", "rite", "mystery"],
    "king": ["king", "ruler", "monarch", "lord"],
    "queen": ["queen", "wife", "lady", "ruler"],
    "father": ["father", "parent", "sire"],
    "mother": ["mother", "parent"],
    "son": ["son", "child", "boy"],
    "daughter": ["daughter", "child", "girl"],
    "child": ["child", "son", "daughter"],
    "killed": ["killed", "slain", "murdered", "died", "slew", "slay"],
    "fought": ["fought", "battled", "warred", "combat"],
    "battle": ["battle", "war", "combat", "fight"],
    "city": ["city", "state", "capital", "kingdom", "town"],
    "destroyed": ["destroyed", "ruined", "sacked", "fell"],
    "loved": ["loved", "beloved", "desired"],
    "love": ["love", "desire", "affection"],
    "tale": ["tale", "story", "myth", "legend"],
    "story": ["story", "myth", "tale", "legend"],
    "god": ["god", "goddess", "deity", "divine"],
    "goddess": ["goddess", "god", "deity", "divine"],
    "prophecy": ["prophecy", "oracle", "prophet", "divination"],
    "oracle": ["oracle", "prophecy", "prophet", "seer"],
    "capital": ["capital", "city", "seat"],
    "reigned": ["reigned", "ruled", "governed", "king"],
    "reign": ["reign", "rule", "kingdom"],
    "war": ["war", "battle", "conflict", "combat"],
    "victory": ["victory", "triumph", "win"],
    "epithet": ["epithet", "title", "name", "epithets"],
    "roman": ["roman", "latin"],
    "symbol": ["symbol", "emblem", "sign", "attribute"],
    "domain": ["domain", "realm", "sphere", "province"],
    "parent": ["parent", "father", "mother"],
}

def expand_query_terms(terms):
    """Expand query terms with synonyms."""
    expanded = set()
    for t in terms:
        if t in SYNONYM_MAP:
            for s in SYNONYM_MAP[t]:
                expanded.add(s)
        else:
            expanded.add(t)
    return list(expanded)

# Chinese -> English academic term mapping for search queries
TERM_DICT = {
    "称号": "epithet",
    "别名": "epithet",
    "别称": "epithet",
    "头衔": "epithet",
    "管辖": "domain",
    "掌管": "domain",
    "主管": "domain",
    "司掌": "domain",
    "领域": "domain",
    "象征": "symbol",
    "符号": "symbol",
    "标志": "symbol",
    "神话": "myth",
    "故事": "myth",
    "传说": "myth",
    "关系": "relationship",
    "关联": "relationship",
    "父母": "parent",
    "父亲": "father",
    "母亲": "mother",
    "儿子": "son",
    "女儿": "daughter",
    "配偶": "spouse",
    "丈夫": "husband",
    "妻子": "wife",
    "兄弟": "brother",
    "姐妹": "sister",
    "地点": "place",
    "地方": "place",
    "艺术品": "artwork",
    "作品": "artwork",
    "概念": "concept",
    "定义": "definition",
    "罗马名": "roman",
    "罗马": "roman",
    "希腊名": "name",
}

# ─────────────────────────────────────────────
# 1. Load data
# ─────────────────────────────────────────────

def load_index():
    global tutor_index
    if tutor_index is not None:
        return tutor_index
    with index_lock:
        if tutor_index is not None:
            return tutor_index
        if not INDEX_PATH.exists():
            print(f"[ERROR] Index not found: {INDEX_PATH}")
            return None
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            tutor_index = json.load(f)
        print(f"[INFO] Index loaded: {len(tutor_index['characters'])} chars, "
              f"{len(tutor_index['myths'])} myths, {len(tutor_index['concepts'])} concepts, "
              f"{len(tutor_index['places'])} places, {len(tutor_index['artworks'])} artworks")
        return tutor_index


def load_name_map():
    global name_map
    if name_map is not None:
        return name_map
    path = DATA_DIR / "name_map.json"
    if not path.exists():
        print(f"[WARN] name_map not found: {path}")
        name_map = {}
        return name_map
    with open(path, "r", encoding="utf-8") as f:
        name_map = json.load(f)
    print(f"[INFO] Name map loaded: {len(name_map)} entries")
    return name_map


def expand_chinese_query(query):
    """Expand a Chinese query by translating names and terms to English."""
    if not re.search(r'[\u4e00-\u9fff]', query):
        return query  # no Chinese, return as-is

    _ = load_name_map()
    terms = []

    # Extract Chinese substrings and look up in name_map
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', query)
    for cseg in chinese_chars:
        if cseg in TERM_DICT:
            terms.append(TERM_DICT[cseg])
        if _:
            for eng_name, chinese_list in _.items():
                if cseg in chinese_list:
                    terms.append(eng_name)
                    # Also add the english name in search-friendly fragments
                    terms.extend(eng_name.lower().split())

    # Also add English substrings that appear in the query (e.g. "Themis" in "Themis的称号")
    eng_parts = re.findall(r'[a-zA-Z]+', query)
    for ep in eng_parts:
        if len(ep) >= 2:
            terms.append(ep.lower())

    if terms:
        expanded = query + " " + " ".join(terms)
        return expanded
    return query


# ─────────────────────────────────────────────
# 2. Knowledge graph search
# ─────────────────────────────────────────────

def has_stop_words_only(terms):
    """Check if all terms are stop words."""
    if not terms:
        return True
    return all(t in STOP_WORDS for t in terms)


def clean_term(w):
    return w.strip(string.punctuation)


def get_relevance(text, query, terms=None, synonym_map=None):
    q = query.lower()
    t = text.lower() if text else ""
    if not t:
        return 0
    if terms is None:
        all_terms = [clean_term(w) for w in q.split() if len(clean_term(w)) >= 2]
        all_terms = [w for w in all_terms if w not in STOP_WORDS]
    else:
        all_terms = [clean_term(w) for w in terms if clean_term(w) not in STOP_WORDS and clean_term(w)]
    if not all_terms:
        return 0
    matches = 0
    for w in all_terms:
        if w in t:
            matches += 1
        elif synonym_map and w in synonym_map:
            if any(syn in t for syn in synonym_map[w]):
                matches += 1
    return matches / len(all_terms)


def search_kg(query, index):
    q = query.strip().lower()
    all_terms = [clean_term(w) for w in q.split() if len(clean_term(w)) >= 2]
    sig_terms = [w for w in all_terms if w not in STOP_WORDS]

    results = {"characters": [], "myths": [], "concepts": [], "places": [], "artworks": []}

    def score(s):
        return get_relevance(s, q, sig_terms, synonym_map=SYNONYM_MAP)

    # If no significant terms found, use all terms
    effective_terms = sig_terms if sig_terms else all_terms

    def score_with_boost(name_val, extra_texts, query_terms):
        base = get_relevance(name_val, q, query_terms, synonym_map=SYNONYM_MAP)
        # Exact name match boost
        name_lower = name_val.lower()
        for t in query_terms:
            if t == name_lower:
                base = max(base, 1.0)
            elif t in name_lower:
                base = max(base, len(t) / len(name_lower))
        for et in extra_texts:
            base = max(base, get_relevance(et, q, query_terms, synonym_map=SYNONYM_MAP))
        return base

    for c in index["characters"]:
        extra = []
        extra.extend(c.get("e", []))
        extra.extend(c.get("d", []))
        extra.extend(c.get("sy", []))
        extra.extend(c.get("myths", []))
        extra.append(c.get("desc", ""))
        if c.get("r"):
            extra.append(c["r"])
        s = score_with_boost(c["n"], extra, effective_terms)
        if s >= 0.3:
            results["characters"].append({"item": c, "score": s})

    for m in index["myths"]:
        extra = [m.get("s", "")]
        extra.extend(m.get("kc", []))
        s = score_with_boost(m["n"], extra, effective_terms)
        if s >= 0.3:
            results["myths"].append({"item": m, "score": s})

    for c in index["concepts"]:
        extra = [c.get("def", "")]
        s = score_with_boost(c["n"], extra, effective_terms)
        if s >= 0.3:
            results["concepts"].append({"item": c, "score": s})

    for p in index["places"]:
        extra = [p.get("desc", "")]
        s = score_with_boost(p["n"], extra, effective_terms)
        if s >= 0.3:
            results["places"].append({"item": p, "score": s})

    for a in index["artworks"]:
        extra = [a.get("desc", "")]
        s = score_with_boost(a["n"], extra, effective_terms)
        if s >= 0.3:
            results["artworks"].append({"item": a, "score": s})

    for key in results:
        results[key].sort(key=lambda x: x["score"], reverse=True)
        results[key] = results[key][:5]

    return results


def compress_pages(pages):
    """Compress page list into range notation."""
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges = []
    start = sorted_pages[0]
    end = sorted_pages[0]
    for p in sorted_pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = p
            end = p
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ", ".join(ranges)


def format_evidence(ev):
    if not ev:
        return ""
    parts = []
    for e in ev[:3]:
        pages = compress_pages(e.get("pp", []))
        parts.append(f"Ch.{e['ch']}" + (f" (pp. {pages})" if pages else ""))
    return "; ".join(parts)


def build_context(results):
    sections = []

    REL_LABELS = {
        "parent_of": "Parent of", "child_of": "Child of",
        "spouse_of": "Spouse of", "lover_of": "Lover of",
        "sibling_of": "Sibling of", "married_to": "Married to",
        "roman_equivalent": "Roman equivalent", "greek_equivalent": "Greek equivalent",
        "identified_with": "Identified with", "fought_against": "Fought against",
        "killed_by": "Killed by", "killed": "Killed",
    }

    def format_rels(rels):
        if not rels:
            return ""
        parts = []
        for rel in rels[:5]:
            label = REL_LABELS.get(rel["t"], rel["t"].replace("_", " "))
            desc = rel.get("desc", "")
            ch = rel.get("ch", 0)
            pp = rel.get("pp", [])
            ref = f" (Ch.{ch}" + (f" pp. {compress_pages(pp)}" if pp else "") + ")"
            if desc:
                parts.append(f"    {label}: {rel.get('other','')} - {desc}{ref}")
            else:
                parts.append(f"    {label}: {rel.get('other','')}{ref}")
        return "\n".join(parts)

    if results["characters"]:
        lines = ["=== 教材人物知识 ==="]
        for r in results["characters"]:
            c = r["item"]
            line = f"- {c['n']}"
            if c.get("r") and c["r"] != c["n"]:
                line += f" (Roman: {c['r']})"
            if c.get("t"):
                line += f" [{c['t']}]"
            if c.get("desc"):
                line += f": {c['desc']}"
            if c.get("e"):
                line += f"\n  Epithets: {', '.join(c['e'][:6])}"
            if c.get("d"):
                line += f"\n  Domains: {', '.join(c['d'][:6])}"
            if c.get("sy"):
                line += f"\n  Symbols: {', '.join(c['sy'][:4])}"
            if c.get("myths"):
                line += f"\n  Related myths: {', '.join(c['myths'][:3])}"
            if c.get("rel"):
                rels_text = format_rels(c["rel"])
                if rels_text:
                    line += f"\n  {rels_text}"
            if c.get("ev"):
                line += f"\n  Source: {format_evidence(c['ev'])}"
            lines.append(line)
        sections.append("\n".join(lines))

    if results["myths"]:
        lines = ["=== 教材神话知识 ==="]
        for r in results["myths"]:
            m = r["item"]
            line = f"- {m['n']}"
            if m.get("s"):
                line += f"\n  Summary: {m['s']}"
            if m.get("kc"):
                line += f"\n  Key characters: {', '.join(m['kc'][:5])}"
            if m.get("ev"):
                line += f"\n  Source: {format_evidence(m['ev'])}"
            lines.append(line)
        sections.append("\n".join(lines))

    if results["concepts"]:
        lines = ["=== 教材概念 ==="]
        for r in results["concepts"]:
            x = r["item"]
            line = f"- {x['n']}: {x.get('def', '')}"
            lines.append(line)
        sections.append("\n".join(lines))

    if results["places"]:
        lines = ["=== 教材地点 ==="]
        for r in results["places"]:
            p = r["item"]
            line = f"- {p['n']}: {p.get('desc', '')}"
            lines.append(line)
        sections.append("\n".join(lines))

    if results["artworks"]:
        lines = ["=== 教材艺术品 ==="]
        for r in results["artworks"]:
            a = r["item"]
            line = f"- {a['n']}: {a.get('desc', '')}"
            lines.append(line)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


# ─────────────────────────────────────────────
# 3. LLM API (OpenAI-compatible, e.g. DeepSeek)
# ─────────────────────────────────────────────

def load_config():
    """Load LLM config from env or .env file."""
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    env_path = Path(".env")
    if env_path.exists() and (not api_key):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("\"'")
                    if k == "LLM_API_KEY":
                        api_key = v
                    elif k == "LLM_BASE_URL":
                        base_url = v
                    elif k == "LLM_MODEL":
                        model = v

    return api_key, base_url.rstrip("/"), model


def build_messages(context, question):
    system_prompt = (
        "你是一位古希腊罗马神话课程的助教，友善且乐于助人。\n\n"
        "回答风格：\n"
        "- 日常问候、闲聊可以直接自然回应，不需要依赖教材知识\n"
        "- 对于神话相关的问题，基于下方【教材知识】回答，标注章节页码\n"
        "- 教材知识不足时，可结合常识简要说明，但需标注哪些是教材内容、哪些是补充\n"
        "- 回答简洁清晰，适合本科生理解\n"
        "- 如果用户的问题中不包含中文，请用英语回答；如果包含中文，则用中文回答\n\n"
        "教材知识（用于神话问题）：\n"
        f"===== 教材知识开始 =====\n"
        f"{context}\n"
        f"===== 教材知识结束 =====\n\n"
        "注意：神话问题请优先使用教材知识；日常对话无需拘束。"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]


def build_verify_messages(context, answer):
    verify_prompt = (
        "你是一个事实核查员。下面有一段【教材知识】和一个【AI回答】。\n\n"
        "请检查【AI回答】中关于神话事实的陈述是否在【教材知识】中有依据。\n"
        "注意事项：\n"
        "- 日常问候、闲聊用语无需核查\n"
        "- 仅关注神话相关的知识性陈述\n"
        "具体检查每一项神话陈述：\n"
        "1. 是否在教材知识中有明确依据？\n"
        "2. 是否有超出教材范围的推测或编造？\n\n"
        f"===== 教材知识 =====\n"
        f"{context}\n"
        f"===== AI回答 =====\n"
        f"{answer}\n\n"
        "请用以下格式回答：\n"
        "核查结果：通过/有问题\n"
        "问题陈述（如果有的话）：\n"
        "- 问题1...\n"
        "- 问题2..."
    )
    return [{"role": "user", "content": verify_prompt}]


def extract_references(results):
    """Extract unique chapter/page references from KG results, grouped by chapter."""
    chapter_pages = {}
    for key in ["characters", "myths"]:
        for r in results.get(key, []):
            for ev in r["item"].get("ev", []):
                ch = ev.get("ch", "")
                if ch not in chapter_pages:
                    chapter_pages[ch] = set()
                for pp in ev.get("pp", []):
                    chapter_pages[ch].add(pp)
    refs = []
    for ch in sorted(chapter_pages.keys()):
        pages = sorted(chapter_pages[ch])
        compressed = compress_pages(pages)
        refs.append(f"Ch.{ch} pp. {compressed}")
    return refs[:10]


def call_llm(messages, api_key, base_url, model):
    """Call OpenAI-compatible chat API (DeepSeek, etc.)."""
    url = f"{base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        data = resp.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            print(f"[ERROR] LLM API error: {error_msg}")
            return None, error_msg

        answer = data["choices"][0]["message"]["content"]
        return answer, None

    except requests.exceptions.Timeout:
        return None, "请求超时，请稍后重试"
    except requests.exceptions.RequestException as e:
        return None, f"网络错误: {str(e)}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return None, f"解析响应失败: {str(e)}"


# ─────────────────────────────────────────────
# 4. Flask routes
# ─────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "index_loaded": tutor_index is not None})


@app.route("/api/ask", methods=["POST"])
def ask():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"status": 1000, "message": "invalid input"}), 400

    question = body.get("question", "")
    if not question.strip():
        return jsonify({"status": 1000, "message": "question is required"}), 400

    # 1. Expand query (Chinese -> English translation)
    expanded_query = expand_chinese_query(question)

    # 2. Search knowledge graph
    index = load_index()
    if not index:
        return jsonify({"status": 1001, "message": "knowledge index not loaded"}), 500

    results = search_kg(expanded_query, index)

    # 2. Build context from KG results
    context = build_context(results)

    total_found = (
        len(results["characters"]) + len(results["myths"]) +
        len(results["concepts"]) + len(results["places"]) +
        len(results["artworks"])
    )

    # Load API config early for Approach B
    api_key, base_url, model = load_config()

    # Approach B: LLM-based query expansion if results are too sparse
    if total_found < 2 and api_key:
        try:
            ext_prompt = (
                "Extract 2-5 key search terms (important names, roles, places, concepts) "
                "from this question about Greek/Roman mythology. "
                "Return ONLY comma-separated terms, nothing else.\n\n"
                f"Question: {question}"
            )
            ext_messages = [
                {"role": "system", "content": "You extract search keywords from mythology questions."},
                {"role": "user", "content": ext_prompt}
            ]
            ext_resp, _ = call_llm(ext_messages, api_key, base_url, model)
            if ext_resp and ext_resp.strip():
                ext_terms = [t.strip() for t in ext_resp.strip().split(",") if t.strip()]
                if ext_terms:
                    llm_expanded = " ".join(ext_terms)
                    new_results = search_kg(llm_expanded, index)
                    new_total = sum(len(v) for v in new_results.values())
                    if new_total > total_found:
                        results = new_results
                        total_found = new_total
                        context = build_context(results)
        except Exception:
            pass

    if total_found == 0:
        context = "教材中没有找到与这个问题直接相关的知识条目。"

    # 3. Try LLM API
    if api_key:
        # 3a. Generate answer
        messages = build_messages(context, question)
        answer, error = call_llm(messages, api_key, base_url, model)

        if answer:
            # 3b. (C) Post-response verification
            has_issues = False
            verify_result = ""
            try:
                vmsg = build_verify_messages(context, answer)
                vresp, verr = call_llm(vmsg, api_key, base_url, model)
                if vresp and "有问题" in vresp:
                    has_issues = True
                    verify_result = vresp
            except Exception:
                pass

            if has_issues and verify_result:
                answer += (
                    "\n\n---\n⚠️ **AI 自查提醒**：以下陈述可能超出教材范围，请对照教材核实：\n"
                    f"{verify_result}"
                )

            # 3c. (D) Append reference list
            refs = extract_references(results)
            if refs:
                ref_lines = [f"- {r}" for r in refs]
                answer += (
                    "\n\n---\n📖 **教材引用汇总**\n"
                    + "\n".join(ref_lines)
                    + "\n\n*建议翻阅教材对应章节获取更详细的内容。*"
                )

            return jsonify({
                "status": 0,
                "data": {
                    "answer": answer,
                    "references": refs if refs else [],
                    "threadId": ""
                }
            })

        # LLM failed, fall through to KG fallback
        fallback_reason = error or "unknown error"
    else:
        fallback_reason = "未配置 LLM API Key"

    # 4. Fallback: return KG search results directly
    refs = extract_references(results)
    ref_text = ("\n📖 教材引用汇总\n" + "\n".join(f"- {r}" for r in refs)) if refs else ""
    return jsonify({
        "status": 0,
        "data": {
            "answer": (
                f"（AI 服务暂不可用: {fallback_reason}）\n\n"
                f"这是基于教材知识图谱的检索结果：\n\n{context[:3000]}"
                f"{ref_text}"
            ),
            "references": refs if refs else [],
            "threadId": ""
        }
    })


# ─────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────

# Load index at import time (for gunicorn)
load_index()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"[INFO] AI Tutor server starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
