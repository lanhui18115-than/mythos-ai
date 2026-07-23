"""
Mythos AI — Artwork Identification Module (07_artwork_quiz.py)

Generates artwork-based learning questions from the knowledge graph.
Students identify characters, stories, and mythological scenes
depicted in artworks from the textbook.

Output: output/artwork_quiz.html (browser-ready)
"""

import json
import random
import re
from pathlib import Path
from collections import defaultdict

GRAPH_FILE = Path("data/knowledge_graph.json")
IMAGE_MAP_FILE = Path("data/artwork_image_map.json")
VISUAL_DESC_FILE = Path("data/artwork_visual_desc.json")
OUTPUT_FILE = Path("output/artwork_quiz.html")

random.seed(42)


def load_kg():
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


_STOP_WORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "for",
               "with", "by", "and", "or", "his", "her", "its", "their",
               "one", "two", "from", "this", "that", "is", "are", "was"}

# Words that indicate a narrative/scene artwork (vs. iconic portrait/statue)
_NARRATIVE_WORDS = {"offers", "offering", "devouring", "devours", "wounds",
    "fighting", "battle", "death", "dying", "birth", "abduction", "rape",
    "murder", "killing", "kills", "stealing", "steals", "carrying", "carries",
    "returns", "returning", "hunt", "hunting", "playing", "dancing",
    "sacrifice", "wrestling", "fleeing", "pursuing", "chasing", "running",
    "creating", "punishment", "punishing", "trick", "tricking", "quarrel",
    "theft", "wounding", "seducing", "seduces", "rescuing", "rescues"}


def _word_set(words):
    """Normalize words for matching: lowercase, strip suffixes, remove short/stop words."""
    out = set()
    for w in re.findall(r"[a-zA-Z]+", words.lower()):
        if w in _STOP_WORDS or len(w) < 3:
            continue
        out.add(w)
        # Strip common suffixes
        w2 = w
        for suf in ["ing", "ed", "tion", "s", "ren", "en"]:
            if w2.endswith(suf) and len(w2) > len(suf) + 2:
                w2 = w2[:-len(suf)]
        if len(w2) >= 3 and w2 != w:
            out.add(w2)
    return out


def _build_char_description(char_names, char_by_name):
    """Build a simple description from character data (for iconic artworks)."""
    parts = []
    for name in char_names:
        c = char_by_name.get(name)
        if not c:
            parts.append(name)
            continue
        desc = c.get("description", "")
        domains = c.get("domains", [])
        epithets = c.get("epithets", [])
        line = name
        if domains:
            line += f" — {', '.join(domains[:3])}"
        if epithets:
            line += f" ({'; '.join(epithets[:3])})"
        parts.append(line)
    return " \\ ".join(parts)


def build_story_candidates(artwork_name, depicted, char_by_name, myth_by_name, description=""):
    """Return sorted list of (score, story_text, myth_name) candidates for an artwork.

    For narrative artworks (name contains action words), finds myth matches
    using character overlap + description word overlap with stemming.
    For iconic artworks (portraits/statues), returns a single char-description.
    Returns empty list if no candidates.
    """
    depicted_set = set(depicted)
    if not depicted_set:
        return []

    art_words = set(w.lower() for w in re.findall(r"[a-zA-Z]+", artwork_name))
    is_narrative = bool(art_words & _NARRATIVE_WORDS)

    if not is_narrative:
        return [(100, _build_char_description(depicted, char_by_name), "")]

    # Narrative artwork: collect scored myth candidates
    desc_words = _word_set(description)
    scored = []
    seen = set()
    for char_name in depicted:
        char = char_by_name.get(char_name)
        if not char:
            continue
        for myth_name in char.get("major_myths", []):
            if myth_name in seen:
                continue
            seen.add(myth_name)
            myth = myth_by_name.get(myth_name)
            if not myth or not myth.get("summary"):
                continue
            key_chars = set(myth.get("key_characters", []))
            summary_words = _word_set(myth["summary"])
            char_overlap = len(depicted_set & key_chars)
            desc_overlap = len(desc_words & summary_words)
            if desc_overlap < 2:
                continue
            score = char_overlap * 10 + desc_overlap * 3
            scored.append((score, myth["summary"], myth_name))

    if not scored:
        return [(50, _build_char_description(depicted, char_by_name), "")]

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def build_artwork_questions(kg):
    """Generate artwork-related questions"""
    questions = []

    # Load image map
    image_map = {}
    if IMAGE_MAP_FILE.exists():
        image_map = json.loads(IMAGE_MAP_FILE.read_text(encoding="utf-8"))
    art_name_to_images = {}
    for a in kg["artworks"]:
        for aid, paths in image_map.items():
            if a["id"] == aid:
                urls = []
                for p in paths:
                    fname = Path(p).name
                    urls.append(f"../data/artwork_images/{fname}")
                art_name_to_images[a["name"]] = urls
                break

    # Load visual descriptions
    visual_descriptions = {}
    if VISUAL_DESC_FILE.exists():
        visual_descriptions = json.loads(VISUAL_DESC_FILE.read_text(encoding="utf-8"))

    # Build artwork name → ID mapping
    art_name_to_id = {a["name"]: a["id"] for a in kg["artworks"]}

    def get_images(artwork_name):
        urls = art_name_to_images.get(artwork_name, [])
        return urls[0] if urls else None

    def get_visual_desc(artwork_name):
        aid = art_name_to_id.get(artwork_name)
        if aid and aid in visual_descriptions:
            vd = visual_descriptions[aid]
            return vd.get("corrected_description") or vd.get("description")
        return None

    # Build lookups
    char_by_name = {c["name"]: c for c in kg.get("characters", [])}
    myth_by_name = {m["name"]: m for m in kg.get("myths", [])}

    # Build artwork → depicted characters
    art_depictions = defaultdict(list)
    for r in kg["relationships"]:
        if r.get("type") in ("depicted_in", "depicts"):
            art_depictions[r["source"]].append(r)
            art_depictions[r["target"]].append(r)

    depicted_chars = set()
    for r in kg["relationships"]:
        if r.get("type") == "depicted_in":
            depicted_chars.add(r["source"])

    # Pre-compute story candidates per artwork
    artwork_candidates = {}
    for artwork in kg["artworks"]:
        name = artwork["name"]
        desc = artwork.get("description", "")
        rels = art_depictions.get(name, [])
        depicted = set()
        for r in rels:
            if r["type"] == "depicts" and r["source"] == name:
                depicted.add(r["target"])
            elif r["type"] == "depicted_in" and r["target"] == name:
                depicted.add(r["source"])
        artwork_candidates[name] = build_story_candidates(name, depicted, char_by_name, myth_by_name, desc)

    # Greedy bipartite assignment: match each story to the artwork that scores highest for it
    all_entries = []  # (artwork_name, score, tiebreaker, story)
    for aname, cands in artwork_candidates.items():
        a = next((x for x in kg["artworks"] if x["name"] == aname), {})
        desc_lower = (a.get("description", "") + " " + aname).lower()
        for score, story, mname in cands:
            # Tiebreaker: how many myth-name words appear in the artwork name or description
            tie = sum(1 for w in re.findall(r"[a-zA-Z]+", mname.lower()) if w in desc_lower and len(w) >= 3)
            all_entries.append((aname, score, tie, story))

    assigned_stories = {}
    used_artworks = set()
    used_stories_set = set()
    for aname, score, tie, story in sorted(all_entries, key=lambda x: (-x[1], -x[2])):
        if aname not in used_artworks and story not in used_stories_set:
            assigned_stories[aname] = story
            used_artworks.add(aname)
            used_stories_set.add(story)

    def pick_story(name):
        story = assigned_stories.get(name)
        if story:
            return story
        # Fallback: best candidate even if used (better than no story)
        cands = artwork_candidates.get(name, [])
        return cands[0][1] if cands else None

    for artwork in kg["artworks"]:
        name = artwork["name"]
        desc = artwork.get("description", "")
        if not desc or len(desc) < 20:
            continue
        rels = art_depictions.get(name, [])
        depicted = set()
        for r in rels:
            if r["type"] == "depicts" and r["source"] == name:
                depicted.add(r["target"])
            elif r["type"] == "depicted_in" and r["target"] == name:
                depicted.add(r["source"])

        story = pick_story(name)

        if len(depicted) >= 2:
            correct = random.choice(list(depicted))
            pool = list(depicted_chars - {correct})
            random.shuffle(pool)
            distractors = pool[:3]
            if len(distractors) < 3:
                continue
            options = [correct] + distractors
            random.shuffle(options)
            evidence = artwork.get("evidence", [])
            ref = f"ch.{evidence[0]['chapter']} p.{', '.join(str(p) for p in artwork.get('mentioned_pages', []))}" if evidence else ""
            questions.append({
                "type": "artwork_character",
                "artwork": name,
                "description": desc,
                "image_url": get_images(name),
                "question": "Which mythological figure is depicted in this artwork?",
                "options": options,
                "correct": correct,
                "explanation": f'This artwork depicts {", ".join(sorted(depicted))}. It is a {artwork.get("type", "artwork")} described as: {desc[:200]}',
                "reference": ref,
                "story": story,
                "visual_desc": get_visual_desc(name),
            })

        if len(depicted) >= 1:
            char = random.choice(list(depicted))
            is_true = random.random() < 0.5
            if is_true:
                statement = f"Does this artwork depict {char}?"
                correct_bool = True
                explanation = f"Yes, {char} is depicted in this artwork."
            else:
                other = random.choice(list(depicted_chars - {char} - depicted))
                if not other:
                    continue
                statement = f"Does this artwork depict {other}?"
                correct_bool = False
                explanation = f"No, this artwork does not depict {other}. It depicts {', '.join(sorted(depicted))}."
            evidence = artwork.get("evidence", [])
            ref = f"ch.{evidence[0]['chapter']}" if evidence else ""
            questions.append({
                "type": "artwork_tf",
                "artwork": name,
                "description": desc,
                "image_url": get_images(name),
                "question": statement,
                "correct": correct_bool,
                "explanation": explanation + f'\n\n"{name}" is a {artwork.get("type", "artwork")} described as: {desc[:200]}',
                "reference": ref,
                "story": story,
                "visual_desc": get_visual_desc(name),
            })

    questions = [q for q in questions if q.get("image_url") is not None and q["type"] not in ("artwork_type", "artwork_name")]
    return questions


def generate_html(questions):
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mythos AI — 艺术品识别</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',sans-serif; background:#0a0a1a; color:#eee; padding:20px; }
  .container { max-width:900px; margin:0 auto; }
  h1 { color:#F5D742; font-size:24px; margin-bottom:4px; }
  .subtitle { color:#666; font-size:13px; margin-bottom:20px; }
  .stats { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
  .stat { background:#111128; border:1px solid #2a2a4a; border-radius:8px; padding:10px 16px; text-align:center; min-width:90px; }
  .stat .n { font-size:20px; font-weight:bold; color:#F5D742; }
  .stat .l { font-size:11px; color:#888; }
  .controls { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
  .controls button { padding:8px 16px; border:1px solid #333; background:#111128; color:#ccc; border-radius:6px; cursor:pointer; font-size:13px; }
  .controls button:hover { background:#F5D742; color:#111; }
  .controls button.primary { background:#F5D742; color:#111; font-weight:bold; }
  .q-card { background:#111128; border:1px solid #2a2a4a; border-radius:8px; padding:16px; margin-bottom:12px; }
  .q-label { font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#555; margin-bottom:4px; }
  .q-artwork { color:#F5D742; font-size:13px; font-weight:bold; margin-bottom:6px; }
  .q-img-wrap { text-align:center; margin-bottom:10px; background:#0e0e2a; border-radius:6px; padding:8px; min-height:60px; display:flex; align-items:center; justify-content:center; }
  .q-img { max-width:100%; max-height:300px; border-radius:4px; cursor:zoom-in; transition:max-height 0.2s; object-fit:contain; }
  .q-img-expanded { max-height:none; cursor:zoom-out; }
  .q-img-missing { opacity:0.4; font-size:11px; color:#555; }
  .q-img-placeholder { font-style:italic; }
  .q-desc { background:#0e0e2a; border-left:2px solid #F5D742; padding:10px 14px; border-radius:4px; font-size:13px; color:#aaa; line-height:1.6; margin-bottom:12px; font-style:italic; }
  .q-text { font-size:15px; margin-bottom:12px; line-height:1.5; }
  .opts { display:flex; flex-direction:column; gap:6px; }
  .opts label { display:flex; align-items:center; gap:8px; padding:8px 12px; border:1px solid #2a2a4a; border-radius:6px; cursor:pointer; font-size:13px; }
  .opts label:hover { border-color:#555; }
  .opts label.correct { border-color:#2ecc71; background:rgba(46,204,113,0.1); }
  .opts label.wrong { border-color:#e74c3c; background:rgba(231,76,60,0.1); }
  .opts label.disabled { opacity:0.7; cursor:default; }
  .tf-opts { display:flex; gap:10px; }
  .tf-btn { padding:8px 24px; border:1px solid #333; border-radius:6px; cursor:pointer; font-size:14px; background:#1a1a3e; color:#bbb; }
  .tf-btn:hover { border-color:#F5D742; }
  .tf-btn.correct-btn { border-color:#2ecc71; background:rgba(46,204,113,0.2); }
  .tf-btn.wrong-btn { border-color:#e74c3c; background:rgba(231,76,60,0.2); }
  .tf-btn.dimmed-btn { opacity:0.4; }
  .tf-btn:disabled { cursor:default; }
  .q-feedback { margin-top:10px; padding:8px 12px; border-radius:6px; font-size:14px; font-weight:bold; text-align:center; }
  .q-feedback.correct { background:rgba(46,204,113,0.15); color:#2ecc71; border:1px solid rgba(46,204,113,0.3); }
  .q-feedback.wrong { background:rgba(231,76,60,0.15); color:#e74c3c; border:1px solid rgba(231,76,60,0.3); }
  .q-reveal { margin-top:12px; padding:12px; background:rgba(245,215,66,0.05); border:1px solid rgba(245,215,66,0.2); border-radius:6px; }
  .q-reveal .q-artwork { color:#F5D742; font-size:14px; font-weight:bold; margin-bottom:6px; }
  .q-visual-desc { background:rgba(245,215,66,0.08); border:1px solid rgba(245,215,66,0.2); padding:8px 12px; border-radius:4px; font-size:12px; color:#bbb; line-height:1.5; margin-bottom:8px; }
  .q-reveal .q-desc { background:#0e0e2a; border-left:2px solid #F5D742; padding:8px 12px; border-radius:4px; font-size:12px; color:#aaa; line-height:1.5; margin-bottom:8px; font-style:italic; }
  .q-story { background:rgba(46,204,113,0.05); border:1px solid rgba(46,204,113,0.15); padding:10px 14px; border-radius:6px; font-size:13px; color:#ccc; line-height:1.6; margin-bottom:8px; }
  .q-explanation { font-size:12px; color:#888; line-height:1.5; margin-bottom:4px; }
  .q-reveal .ref { color:#555; font-size:11px; margin-top:4px; }
  .reveal-btn { margin-top:10px; padding:8px 20px; border:1px solid #F5D742; border-radius:6px; background:transparent; color:#F5D742; cursor:pointer; font-size:13px; font-weight:bold; width:100%; }
  .reveal-btn:hover { background:#F5D742; color:#111; }
  .filter-bar { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
  .filter-bar button { padding:4px 12px; border:1px solid #333; border-radius:4px; background:transparent; color:#666; cursor:pointer; font-size:11px; }
  .filter-bar button:hover { color:#F5D742; border-color:#F5D742; }
  .filter-bar button.act { color:#F5D742; border-color:#F5D742; }
  .score-bar { position:sticky; top:0; background:#0a0a1a; padding:8px 0; margin-bottom:12px; border-bottom:1px solid #2a2a4a; display:flex; justify-content:space-between; font-size:13px; color:#888; z-index:10; }
</style>
</head>
<body>
<div class="container">
  <h1>Mythos AI — 艺术品识别</h1>
  <div class="subtitle">基于教材《Classical Mythology》中描述的艺术品 · 识别角色、故事与象征</div>
  <div class="controls">
    <button class="primary" onclick="showAll()">全部</button>
    <button onclick="filterType('artwork_character', this)">角色识别</button>
    <button onclick="filterType('artwork_tf', this)">判断</button>
  </div>
  <div class="score-bar">
    <span id="scoreDisplay">已答: 0 / 0  正确: 0</span>
  </div>
  <div id="quiz"></div>
</div>
<script>
var questions = """ + json.dumps(questions, ensure_ascii=False) + """;
var answered = {};
var score = {correct:0, answered:0};

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;').replace(/"/g,'&quot;');
}

function render() {
  var html = '';
  questions.forEach(function(q, i) {
    var answeredFlag = answered[i] !== undefined;
    var isCorrect = answeredFlag && (q.type === 'artwork_tf' ? (answered[i] === 'True') === q.correct : answered[i] === q.correct);
    html += '<div class="q-card" data-type="' + q.type + '">';
    html += '<div class="q-label">' + typeLabel(q.type) + '</div>';

    // Image (always visible)
    if (q.image_url) {
      html += '<div class="q-img-wrap"><img class="q-img" src="' + esc(q.image_url) + '" alt="artwork"></div>';
    } else {
      html += '<div class="q-img-wrap q-img-missing"><span class="q-img-placeholder">[教材图片未提取]</span></div>';
    }

    // Question (always visible)
    html += '<div class="q-text">' + (i+1) + '. ' + esc(q.question) + '</div>';

    // Options
    if (q.type === 'artwork_character') {
      html += '<div class="opts">';
      q.options.forEach(function(o) {
        var cls = '';
        var extra = '';
        if (answeredFlag) {
          cls = 'disabled';
          if (o === q.correct) cls += ' correct';
          else if (answered[i] === o) cls += ' wrong';
          if (o === q.correct) extra = ' <span style="color:#2ecc71">&#10003;</span>';
          else if (answered[i] === o) extra = ' <span style="color:#e74c3c">&#10007;</span>';
        }
        html += '<label class="' + cls + '" data-q="' + i + '" data-val="' + esc(o) + '">';
        html += '<input type="radio" name="q' + i + '" ' + (answeredFlag ? 'disabled' : '') + '>';
        html += esc(o) + extra + '</label>';
      });
      html += '</div>';
    }

    if (q.type === 'artwork_tf') {
      html += '<div class="tf-opts">';
      ['True', 'False'].forEach(function(v) {
        var cls = 'tf-btn';
        if (answeredFlag) {
          var isCorrectChoice = (v === 'True') === q.correct;
          var isUserChoice = answered[i] === v;
          if (isCorrectChoice) cls += ' correct-btn';
          else if (isUserChoice) cls += ' wrong-btn';
          else cls += ' dimmed-btn';
          cls += ' disabled';
        }
        html += '<button class="' + cls + '" data-q="' + i + '" data-val="' + v + '" ' + (answeredFlag ? 'disabled' : '') + '>' + v + '</button>';
      });
      html += '</div>';
    }

    // Answer feedback header (shown after answering)
    if (answeredFlag) {
      html += '<div class="q-feedback ' + (isCorrect ? 'correct' : 'wrong') + '">' + (isCorrect ? '✅ 正确！' : '❌ 错误') + '</div>';
    }

    // Revealed info section (shown after answering)
    if (answeredFlag) {
      html += '<div class="q-reveal">';
      html += '<div class="q-artwork">' + esc(q.artwork) + '</div>';
      if (q.visual_desc) {
        html += '<div class="q-visual-desc">' + esc(q.visual_desc) + '</div>';
      }
      if (q.description) {
        html += '<div class="q-desc">' + esc(q.description.slice(0, 250)) + '</div>';
      }
      if (q.story) {
        html += '<div class="q-story">' + esc(q.story) + '</div>';
      }
      html += '<div class="q-explanation">' + esc(q.explanation) + '</div>';
      if (q.reference) html += '<div class="ref">出处: ' + esc(q.reference) + '</div>';
      html += '</div>';
    }

    // Reveal button
    if (!answeredFlag) {
      html += '<button class="reveal-btn" data-q="' + i + '">显示答案</button>';
    }

    html += '</div>';
  });
  document.getElementById('quiz').innerHTML = html;
  updateScore();
}

function typeLabel(t) {
  return {'artwork_character':'角色识别','artwork_tf':'判断'}[t]||t;
}

function handleQuizClick(e) {
  var target = e.target;
  if (target.classList.contains('q-img')) {
    target.classList.toggle('q-img-expanded');
    return;
  }
  var qIdx = target.getAttribute('data-q');
  if (qIdx === null) return;
  qIdx = parseInt(qIdx);
  var val = target.getAttribute('data-val');

  if (target.tagName === 'LABEL' && val !== null && answered[qIdx] === undefined) {
    answered[qIdx] = val;
    if (val === questions[qIdx].correct) score.correct++;
    score.answered++;
    render();
    document.getElementById('expl-' + qIdx).style.display = 'block';
    return;
  }

  if (target.tagName === 'BUTTON' && target.classList.contains('tf-btn') && val !== null && answered[qIdx] === undefined) {
    answered[qIdx] = val;
    if ((val === 'True') === questions[qIdx].correct) score.correct++;
    score.answered++;
    render();
    document.getElementById('expl-' + qIdx).style.display = 'block';
    return;
  }

  if (target.classList.contains('reveal-btn')) {
    var expl = document.getElementById('expl-' + qIdx);
    if (expl) expl.style.display = expl.style.display === 'none' ? 'block' : 'none';
  }
}

function updateScore() {
  document.getElementById('scoreDisplay').textContent = '已答: ' + score.answered + ' / ' + questions.length + ' 正确: ' + score.correct;
}

function filterType(type, btn) {
  document.querySelectorAll('.q-card').forEach(function(el) {
    el.style.display = el.getAttribute('data-type') === type ? 'block' : 'none';
  });
  document.querySelectorAll('.controls button').forEach(function(b) { b.classList.remove('primary'); });
  btn.classList.add('primary');
}

function showAll() {
  document.querySelectorAll('.q-card').forEach(function(el) { el.style.display = 'block'; });
  document.querySelectorAll('.controls button').forEach(function(b) { b.classList.remove('primary'); });
  document.querySelector('.controls button:first-child').classList.add('primary');
}

document.getElementById('quiz').addEventListener('click', handleQuizClick);
render();
</script>
</body>
</html>"""
    return html


def main():
    print("=" * 60)
    print("Mythos AI — 艺术品识别模块")
    print("=" * 60)

    kg = load_kg()
    print(f"艺术品总数: {kg['metadata']['total_artworks']}")
    print(f"关系总数: {kg['metadata']['total_relationships']}")

    questions = build_artwork_questions(kg)
    print(f"生成题目: {len(questions)} 道")

    for t in set(q["type"] for q in questions):
        count = sum(1 for q in questions if q["type"] == t)
        print(f"  {t}: {count}")

    html = generate_html(questions)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[OK] 艺术品测验已生成: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
