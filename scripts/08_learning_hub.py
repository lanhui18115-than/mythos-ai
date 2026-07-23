"""
Mythos AI — Learning Hub (08_learning_hub.py)

Unified entry point for all Layer 3 learning activities.
Generates an index page linking to all learning modules.

Also runs all generators to produce fresh content.

Usage:
    py -3 scripts/08_learning_hub.py

Output: output/index.html (main hub page)
"""

import json
from pathlib import Path
import subprocess
import sys
import webbrowser

SCRIPTS_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent / "output"
GRAPH_FILE = Path(__file__).parent.parent / "data" / "knowledge_graph.json"

MODULES = [
    {
        "id": "character_index",
        "title": "角色索引",
        "subtitle": "Character Index",
        "desc": "希腊罗马神话角色大全，支持搜索、分类浏览。每个角色包含希腊名/罗马名、异体拼名、称号、家族关系、相关神话与艺术品。",
        "file": "character_index.html",
        "icon": "index",
        "script": "12_character_index.py",
        "features": ["搜索角色", "按类型筛选", "家族关系", "神话摘要", "艺术品图片", "教材出处"],
    },
    {
        "id": "family_tree",
        "title": "家族树",
        "subtitle": "Family Tree",
        "desc": "交互式家族关系图谱，展示神祇、英雄、凡人之间的父母、配偶、子女、情人关系。支持搜索和分类浏览。",
        "file": "family_tree.html",
        "icon": "tree",
        "script": "04_family_tree.py",
        "features": ["按类型分类浏览", "搜索角色", "父母/配偶/子女/孙辈关系", "证据来源标注"],
    },
    {
        "id": "quiz",
        "title": "知识测验",
        "subtitle": "Quiz",
        "desc": "基于教材的多题型知识测验，包括选择题、判断题、匹配题和简答题。所有题目均来自知识图谱中的可靠信息。",
        "file": "quiz.html",
        "icon": "quiz",
        "script": "05_quiz_generator.py",
        "features": ["选择题", "判断题", "匹配题", "简答题", "教材出处标注"],
    },
    {
        "id": "crossword",
        "title": "填字游戏",
        "subtitle": "Crossword",
        "desc": "基于神话角色名、罗马名、称号和地点的填字游戏。线索均关联教材内容，寓教于乐。",
        "file": "crossword.html",
        "icon": "crossword",
        "script": "06_crossword_generator.py",
        "features": ["自动生成网格", "键盘导航", "检查答案", "提示功能"],
    },
    {
        "id": "artwork",
        "title": "艺术品识别",
        "subtitle": "Artwork Identification",
        "desc": "基于教材中描述的艺术品，识别其中描绘的角色、故事类型和象征意义。连接视觉艺术与文学知识。",
        "file": "artwork_quiz.html",
        "icon": "artwork",
        "script": "07_artwork_quiz.py",
        "features": ["角色识别", "类型判断", "描述匹配", "出处追溯"],
    },
]


def get_graph_stats():
    """Get basic stats from knowledge graph"""
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            kg = json.load(f)
        m = kg["metadata"]
        return m
    except Exception:
        return {
            "total_characters": 0, "total_myths": 0, "total_places": 0,
            "total_concepts": 0, "total_artworks": 0, "total_relationships": 0,
            "chapters_processed": 0,
        }


def check_outputs():
    """Check which output files exist"""
    results = {}
    for mod in MODULES:
        fpath = OUTPUT_DIR / mod["file"]
        results[mod["id"]] = {
            "exists": fpath.exists(),
            "size": fpath.stat().st_size if fpath.exists() else 0,
        }
    return results


def generate_html(stats, outputs):
    cards_html = ""
    for mod in MODULES:
        out = outputs.get(mod["id"], {})
        exists = out.get("exists", False)
        size_kb = out.get("size", 0) // 1024
        status = "ready" if exists else "missing"
        features = "".join(f'<span class="feat">{f}</span>' for f in mod["features"])

        cards_html += f"""
        <a class="card {status}" href="{mod['file']}" target="_blank">
            <div class="card-header">
                <span class="card-icon icon-{mod['icon']}"></span>
                <div>
                    <div class="card-title">{mod['title']}</div>
                    <div class="card-sub">{mod['subtitle']}</div>
                </div>
                <span class="status-badge {status}">{status}</span>
            </div>
            <div class="card-body">
                <p>{mod['desc']}</p>
                <div class="features">{features}</div>
            </div>
            <div class="card-footer">
                <span class="file-info">{mod['file']} ({size_kb} KB)</span>
                <span class="script-info">脚本: {mod['script']}</span>
            </div>
        </a>"""

    kg_stats = f"""
    <div class="stats-grid">
        <div class="stat-item"><span class="stat-n">{stats.get('chapters_processed', 0)}</span><span class="stat-l">章</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_characters', 0)}</span><span class="stat-l">人物</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_myths', 0)}</span><span class="stat-l">神话</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_places', 0)}</span><span class="stat-l">地点</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_concepts', 0)}</span><span class="stat-l">概念</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_artworks', 0)}</span><span class="stat-l">艺术品</span></div>
        <div class="stat-item"><span class="stat-n">{stats.get('total_relationships', 0)}</span><span class="stat-l">关系</span></div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mythos AI — 学习中心</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',sans-serif; background:#0a0a1a; color:#eee; min-height:100vh; }}
  .container {{ max-width:1100px; margin:0 auto; padding:30px 20px; }}
  
  /* Header */
  header {{ text-align:center; margin-bottom:40px; }}
  header h1 {{ color:#F5D742; font-size:32px; letter-spacing:2px; }}
  header .subtitle {{ color:#666; font-size:14px; margin-top:6px; }}
  header .tagline {{ color:#444; font-size:12px; margin-top:4px; }}
  
  /* Stats */
  .stats-grid {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:40px; }}
  .stat-item {{ background:#111128; border:1px solid #2a2a4a; border-radius:8px; padding:12px 20px; text-align:center; min-width:80px; }}
  .stat-n {{ display:block; font-size:22px; font-weight:bold; color:#F5D742; }}
  .stat-l {{ display:block; font-size:11px; color:#888; margin-top:2px; }}
  
  /* Cards */
  .card-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(420px, 1fr)); gap:16px; }}
  .card {{ display:flex; flex-direction:column; background:#111128; border:1px solid #2a2a4a; border-radius:12px; padding:0; text-decoration:none; color:#eee; transition:all 0.2s; overflow:hidden; }}
  .card:hover {{ border-color:#F5D742; transform:translateY(-2px); box-shadow:0 8px 24px rgba(245,215,66,0.08); }}
  .card.missing {{ opacity:0.6; border-color:#333; }}
  .card.missing:hover {{ opacity:0.8; border-color:#555; transform:none; box-shadow:none; }}
  
  .card-header {{ display:flex; align-items:center; gap:12px; padding:16px 20px; background:rgba(255,255,255,0.02); border-bottom:1px solid #1a1a3e; }}
  .card-icon {{ font-size:28px; width:40px; height:40px; display:flex; align-items:center; justify-content:center; border-radius:8px; background:#1a1a3e; flex-shrink:0; }}
  .icon-tree::before {{ content:"🌳"; }}
  .icon-quiz::before {{ content:"📝"; }}
  .icon-crossword::before {{ content:"🧩"; }}
  .icon-artwork::before {{ content:"🎨"; }}
  .card-title {{ font-size:18px; font-weight:bold; color:#eee; }}
  .card-sub {{ font-size:11px; color:#666; }}
  .status-badge {{ margin-left:auto; padding:3px 10px; border-radius:10px; font-size:10px; text-transform:uppercase; letter-spacing:1px; }}
  .status-badge.ready {{ background:rgba(46,204,113,0.15); color:#2ecc71; border:1px solid rgba(46,204,113,0.3); }}
  .status-badge.missing {{ background:rgba(231,76,60,0.15); color:#e74c3c; border:1px solid rgba(231,76,60,0.3); }}
  
  .card-body {{ padding:16px 20px; flex:1; }}
  .card-body p {{ font-size:13px; color:#999; line-height:1.6; }}
  .features {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:10px; }}
  .feat {{ padding:2px 8px; border-radius:3px; font-size:10px; color:#555; background:#0e0e2a; border:1px solid #1a1a3e; }}
  
  .card-footer {{ display:flex; justify-content:space-between; padding:10px 20px; background:rgba(0,0,0,0.15); border-top:1px solid #1a1a3e; font-size:10px; color:#444; }}
  
  /* Regenerate section */
  .tool-section {{ margin-top:40px; padding:20px; background:#111128; border:1px solid #2a2a4a; border-radius:12px; }}
  .tool-section h2 {{ color:#F5D742; font-size:18px; margin-bottom:8px; }}
  .tool-section p {{ font-size:13px; color:#888; margin-bottom:12px; }}
  .tool-section button {{ padding:10px 20px; border:1px solid #F5D742; background:transparent; color:#F5D742; border-radius:6px; cursor:pointer; font-size:13px; margin-right:8px; margin-bottom:8px; }}
  .tool-section button:hover {{ background:#F5D742; color:#111; }}
  .tool-section .log {{ margin-top:12px; padding:12px; background:#0e0e2a; border:1px solid #1a1a3e; border-radius:6px; font-size:12px; color:#666; font-family:monospace; max-height:200px; overflow-y:auto; }}
  
  /* Book info */
  .book-info {{ margin-top:16px; padding:14px 20px; background:rgba(245,215,66,0.03); border:1px solid rgba(245,215,66,0.1); border-radius:8px; font-size:12px; color:#666; text-align:center; }}
  .book-info strong {{ color:#F5D742; }}

  ::-webkit-scrollbar {{ width:5px; }}
  ::-webkit-scrollbar-track {{ background:#111128; }}
  ::-webkit-scrollbar-thumb {{ background:#333; border-radius:3px; }}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Mythos AI — 学习中心</h1>
    <div class="subtitle">Textbook-Grounded Learning Platform for Classical Mythology</div>
    <div class="tagline">Morford · Lenardon · Sham · Oxford University Press</div>
  </header>

  <div class="stats-grid">
    {kg_stats}
  </div>

  <div class="card-grid">
    {cards_html}
  </div>

  <div class="tool-section">
    <h2>重新生成学习活动</h2>
    <p>如果修改了知识图谱或需要刷新题目，可以点击下方按钮重新生成各模块内容。</p>
    <button onclick="runScript('04_family_tree.py')">重新生成家族树</button>
    <button onclick="runScript('05_quiz_generator.py')">重新生成测验</button>
    <button onclick="runScript('06_crossword_generator.py')">重新生成填字游戏</button>
    <button onclick="runScript('07_artwork_quiz.py')">重新生成艺术品测验</button>
    <button onclick="runAll()">全部重新生成</button>
    <div class="log" id="log">就绪</div>
  </div>

  <div class="book-info">
    <strong>Knowledge Source:</strong> Classical Mythology &mdash; Morford, Lenardon, Sham (11th Edition) &middot; Oxford University Press &middot; All learning content derived exclusively from this textbook.
  </div>

</div>

<script>
function appendLog(msg) {{
  var log = document.getElementById('log');
  var time = new Date().toLocaleTimeString();
  log.textContent = '[' + time + '] ' + msg + '\\n' + log.textContent;
}}

function runScript(name) {{
  appendLog('Running ' + name + '...');
  var log = document.getElementById('log');
  log.textContent = 'Running ' + name + '... (see console for details)\\n' + log.textContent;
  
  fetch('/run?script=' + name)
    .then(function(r) {{ return r.text(); }})
    .then(function(text) {{
      appendLog(name + ' done: ' + text.slice(0, 100));
      setTimeout(function() {{ window.location.reload(); }}, 1000);
    }})
    .catch(function(err) {{
      appendLog('Error: ' + err);
    }});
}}

function runAll() {{
  var scripts = ['04_family_tree.py', '05_quiz_generator.py', '06_crossword_generator.py', '07_artwork_quiz.py'];
  var idx = 0;
  function next() {{
    if (idx >= scripts.length) {{
      appendLog('All done! Reloading...');
      setTimeout(function() {{ window.location.reload(); }}, 1000);
      return;
    }}
    runScript(scripts[idx]);
    idx++;
    setTimeout(next, 2000);
  }}
  next();
}}
</script>
</body>
</html>"""
    return html


def run_generators():
    """Run all learning activity generators"""
    scripts = ["04_family_tree.py", "05_quiz_generator.py", "06_crossword_generator.py", "07_artwork_quiz.py"]
    results = {}
    for script in scripts:
        path = SCRIPTS_DIR / script
        if not path.exists():
            results[script] = "NOT FOUND"
            print(f"  [跳过] {script} 未找到")
            continue
        print(f"  [运行] {script}...")
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, timeout=300,
                cwd=path.parent.parent,
            )
            if result.returncode == 0:
                results[script] = "OK"
                print(f"    OK")
            else:
                results[script] = f"ERROR: {result.stderr[:200]}"
                print(f"    [错误] {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            results[script] = "TIMEOUT"
            print(f"    [超时]")
        except Exception as e:
            results[script] = f"ERROR: {e}"
            print(f"    [错误] {e}")
    return results


def main():
    print("=" * 60)
    print("Mythos AI — 学习中心")
    print("=" * 60)

    import argparse
    parser = argparse.ArgumentParser(description="Mythos AI Learning Hub")
    parser.add_argument("--generate", action="store_true", help="Re-run all generators before building hub")
    parser.add_argument("--open", action="store_true", help="Open hub in browser after generation")
    args = parser.parse_args()

    if args.generate:
        print("\n重新生成所有学习活动...")
        results = run_generators()
        ok = sum(1 for v in results.values() if v == "OK")
        total = len(results)
        print(f"结果: {ok}/{total} 成功")
    else:
        print("\n使用已有输出文件生成中心页面...")
        print("提示: 加 --generate 参数可重新生成所有学习活动")

    print("\n构建学习中心页面...")
    stats = get_graph_stats()
    outputs = check_outputs()

    ready = sum(1 for o in outputs.values() if o["exists"])
    total = len(outputs)
    print(f"输出文件: {ready}/{total} 就绪")

    html = generate_html(stats, outputs)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")

    hub_path = OUTPUT_DIR / "index.html"
    print(f"[OK] 学习中心已生成: {hub_path.resolve()}")

    if args.open:
        webbrowser.open(str(hub_path))
        print("  已在浏览器中打开")

    print("\n" + "=" * 60)
    print("可用学习活动:")
    for mod in MODULES:
        fpath = OUTPUT_DIR / mod["file"]
        status = "✅" if fpath.exists() else "❌"
        indicator = "OK" if status == "ready" else "MISSING"
    print(f"  [{indicator}] {mod['title']:8s} -> {mod['file']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
