"""
Mythos AI — 家族树可视化 v2 (04_family_tree.py)

交互式家族树，支持：
- 左侧分类列表（神祇/女神/英雄/凡人/泰坦/宁芙/怪物）
- 搜索角色后聚焦展示其父母、配偶、情人、子女、孙子
- 父/母区分标注
- 证据来源（章节+页码）

用法：双击运行 或 py -3 scripts/04_family_tree.py
输出：output/family_tree.html（浏览器打开）
"""

import json
from pathlib import Path
from collections import defaultdict

GRAPH_FILE = Path("data/knowledge_graph.json")
OUTPUT_FILE = Path("output/family_tree.html")

TYPE_LABELS = {
    "god": "主神", "goddess": "主神",
    "hero": "英雄", "mortal": "凡人",
    "titan": "泰坦", "nymph": "宁芙",
    "monster": "怪物", "creature": "怪物",
    "cyclops": "巨人", "giant": "巨人", "hecatonchire": "巨人",
    "centaur": "半兽", "satyr": "半兽",
    "concept": "概念", "place": "概念",
    "muse": "团体/其他", "goddesses": "团体/其他",
    "race": "团体/其他", "group": "团体/其他", "other": "团体/其他",
}
TYPE_ORDER = ["主神", "泰坦", "宁芙", "英雄", "凡人", "怪物", "巨人", "半兽", "概念", "团体/其他"]

NODE_COLORS = {
    "god": "#F5D742", "goddess": "#F5D742",
    "hero": "#E74C3C", "mortal": "#95A5A6",
    "titan": "#D35400", "nymph": "#2ECC71",
    "monster": "#8E44AD", "creature": "#8E44AD",
    "cyclops": "#E67E22", "giant": "#E67E22", "hecatonchire": "#E67E22",
    "centaur": "#1ABC9C", "satyr": "#1ABC9C",
    "concept": "#3498DB", "place": "#3498DB",
    "muse": "#7F8C8D", "goddesses": "#7F8C8D",
    "race": "#7F8C8D", "group": "#7F8C8D", "other": "#7F8C8D",
}


def load_data():
    with open(GRAPH_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_indices(kg):
    chars = {}
    for c in kg["characters"]:
        chars[c["name"]] = c

    by_src = defaultdict(list)
    by_tgt = defaultdict(list)
    for r in kg["relationships"]:
        by_src[r["source"]].append(r)
        by_tgt[r["target"]].append(r)

    return chars, by_src, by_tgt


MOTHERS = {"Rhea", "Mnemosyne", "Themis", "Tethys", "Phoebe", "Leto", "Maia",
            "Semele", "Dione", "Metis", "Eurynome", "Clymene", "Persephone",
            "Electra", "Taygete", "Alcmene", "Danae", "Antiope", "Leda",
            "Europa", "Io", "Laodamia", "Aegina", "Selene", "Demeter",
            "Aphrodite", "Hera", "Athena", "Artemis", "Hestia"}

def build_aliases(chars_list, relationships):
    """
    用图算法构建别名→主名映射。
    1) roman_name 连接两个角色（A→B：A 的罗马名是 B，B 的罗马名可能是 A 或空）
    2) epithets 也连接角色  
    3) 每个连通分量中，关系数最多的角色为主名，其余为别名
    """
    names_set = {c["name"] for c in chars_list}
    adj = {c["name"]: set() for c in chars_list}

    # roman_name ↔ 双向连接
    for c in chars_list:
        rn = c.get("roman_name")
        if rn and rn in names_set and rn != c["name"]:
            adj[c["name"]].add(rn)
            adj[rn].add(c["name"])

    # epithet → 被映射方为别名（单向：epithet → 拥有者）
    for c in chars_list:
        for ep in c.get("epithets", []):
            if ep in names_set and ep != c["name"]:
                adj[c["name"]].add(ep)
                adj[ep].add(c["name"])

    # 计算每个角色的关系数量（用于挑选主名）
    rel_count = {}
    for r in relationships:
        rel_count[r["source"]] = rel_count.get(r["source"], 0) + 1
        rel_count[r["target"]] = rel_count.get(r["target"], 0) + 1

    # DFS 找连通分量
    visited = set()
    alias_to_primary = {}
    for name in adj:
        if name in visited:
            continue
        # BFS/DFS 找分量
        stack = [name]
        comp = []
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            comp.append(n)
            for nb in adj[n]:
                if nb not in visited:
                    stack.append(nb)
        # 分量中选关系数最多的为主名
        if len(comp) > 1:
            primary = max(comp, key=lambda n: rel_count.get(n, 0))
            for n in comp:
                if n != primary:
                    alias_to_primary[n] = primary

    # 按主名分组
    primary_to_aliases = {}
    for a, p in alias_to_primary.items():
        primary_to_aliases.setdefault(p, []).append(a)

    return alias_to_primary, primary_to_aliases




def resolve_name(name, alias_map):
    return alias_map.get(name, name)


def precompute_families(chars, by_src, by_tgt, alias_map=None):
    """为每个角色预计算家族数据"""
    if alias_map is None:
        alias_map = {}
    fam = {}
    for raw_name in chars:
        name = resolve_name(raw_name, alias_map)
        # 如果本名是别人的别名，跳过（会在主名下统一生成）
        if name != raw_name:
            continue

        def get_pg(r):
            if "pages" in r and r["pages"]:
                return sorted(r["pages"])
            if "page" in r and r["page"] != "":
                return [r["page"]]
            return []

        parents = []
        seen_parents = set()

        def add_parent(pname, r):
            p = resolve_name(pname, alias_map)
            if p not in seen_parents:
                seen_parents.add(p)
                par = chars.get(p)
                parents.append({
                    "name": p,
                    "label": "",
                    "ch": r.get("chapter", ""),
                    "pages": get_pg(r),
                })

        for r in by_tgt.get(raw_name, []):
            if r["type"] == "parent_of":
                add_parent(r["source"], r)
        for r in by_src.get(raw_name, []):
            if r["type"] == "child_of":
                add_parent(r["target"], r)
        for r in by_tgt.get(raw_name, []):
            if r["type"] == "father_of":
                add_parent(r["source"], r)

        spouses = []
        seen_sp = set()
        for r in by_src.get(raw_name, []) + by_tgt.get(raw_name, []):
            if r["type"] == "spouse_of":
                other = r["target"] if r["source"] == raw_name else r["source"]
                other_p = resolve_name(other, alias_map)
                if other_p not in seen_sp and other_p != name:
                    seen_sp.add(other_p)
                    spouses.append({"name": other_p, "ch": r.get("chapter", ""), "pages": get_pg(r)})

        lovers = []
        seen_lo = set()
        for r in by_src.get(raw_name, []) + by_tgt.get(raw_name, []):
            if r["type"] == "lover_of":
                other = r["target"] if r["source"] == raw_name else r["source"]
                other_p = resolve_name(other, alias_map)
                if other_p not in seen_lo and other_p != name:
                    seen_lo.add(other_p)
                    lovers.append({"name": other_p, "ch": r.get("chapter", ""), "pages": get_pg(r)})

        children = []
        seen_children = set()

        def find_other_parent(child_name, known_parent):
            candidates = []
            for r2 in by_tgt.get(child_name, []):
                if r2["type"] == "parent_of" and r2["source"] != known_parent:
                    candidates.append(resolve_name(r2["source"], alias_map))
            for r2 in by_src.get(child_name, []):
                if r2["type"] == "child_of" and r2["target"] != known_parent:
                    candidates.append(resolve_name(r2["target"], alias_map))
            for r2 in by_tgt.get(child_name, []):
                if r2["type"] == "father_of" and r2["source"] != known_parent:
                    candidates.append(resolve_name(r2["source"], alias_map))
            if not candidates:
                return ""
            # 优先选在当前角色的配偶/情人的
            partner_names = {s["name"] for s in spouses} | {l["name"] for l in lovers}
            for c in candidates:
                if c in partner_names:
                    return c
            return candidates[0]

        def add_child(cname, r):
            cp = resolve_name(cname, alias_map)
            if cp not in seen_children:
                seen_children.add(cp)
                children.append({
                    "name": cp,
                    "other_parent": find_other_parent(cname, raw_name),
                    "ch": r.get("chapter", ""),
                    "pages": get_pg(r),
                })

        for r in by_src.get(raw_name, []):
            if r["type"] == "parent_of":
                add_child(r["target"], r)
        for r in by_tgt.get(raw_name, []):
            if r["type"] == "child_of":
                add_child(r["source"], r)
        for r in by_src.get(raw_name, []):
            if r["type"] == "father_of":
                add_child(r["target"], r)

        grandchildren = []
        seen_grand = set()

        def add_grandchild(gname, parent_name, r):
            gp = resolve_name(gname, alias_map)
            pp = resolve_name(parent_name, alias_map)
            key = (gp, pp)
            if key not in seen_grand:
                seen_grand.add(key)
                grandchildren.append({
                    "name": gp,
                    "parent": pp,
                    "ch": r.get("chapter", ""),
                    "pages": get_pg(r),
                })

        for c in children:
            cn = c["name"]
            # 用原始名查关系，但用主名去重
            raw_child_names = [k for k, v in alias_map.items() if v == cn] or [cn]
            for rc in raw_child_names:
                for r in by_src.get(rc, []):
                    if r["type"] == "parent_of":
                        add_grandchild(r["target"], cn, r)
                for r in by_tgt.get(rc, []):
                    if r["type"] == "child_of":
                        add_grandchild(r["source"], cn, r)
                for r in by_src.get(rc, []):
                    if r["type"] == "father_of":
                        add_grandchild(r["target"], cn, r)

        fam[name] = {
            "parents": parents,
            "spouses": spouses,
            "lovers": lovers,
            "children": children,
            "grandchildren": grandchildren,
        }
    return fam


def generate_html(kg, families, aliases_json=None):
    chars = kg["characters"]

    # 分类列表
    categorized = defaultdict(list)
    for c in chars:
        t = TYPE_LABELS.get(c.get("type", "other"), "其他")
        categorized[t].append(c["name"])
    for v in categorized.values():
        v.sort()
    cats_json = [{"label": cat, "count": len(categorized.get(cat, [])),
                   "names": categorized.get(cat, [])} for cat in TYPE_ORDER if cat in categorized]

    # 角色详情
    chars_json = {}
    for c in chars:
        name = c["name"]
        pages = set()
        for ev in c.get("evidence", []):
            for pp in ev.get("printed_pages", []):
                pages.add(pp)
        chars_json[name] = {
            "type": TYPE_LABELS.get(c.get("type", ""), ""),
            "desc": c.get("description", "")[:120],
            "ch": c.get("primary_chapter", ""),
            "pages": sorted(pages),
        }

    families_json = families

    # Build ALIASES JS code: embed as JSON string and parse to avoid f-string brace issues
    aliases_raw = json.dumps(aliases_json if aliases_json else {}, ensure_ascii=False)
    # wrap in JSON.parse to avoid '{}' inside f-string
    aliases_js_code = "JSON.parse('" + aliases_raw.replace("\\", "\\\\").replace("'", "\\'") + "')"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Mythos AI — 家族树</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',sans-serif; background:#0a0a1a; color:#eee; overflow:hidden; height:100vh; }}
  #app {{ display:flex; height:100vh; }}
  
  #sidebar {{ width:280px; min-width:280px; background:#111128; border-right:1px solid #2a2a4a; display:flex; flex-direction:column; }}
  #sidebar h1 {{ padding:16px 16px 8px; font-size:18px; color:#F5D742; }}
  #search {{ padding:0 16px 8px; }}
  #search input {{ width:100%; padding:8px 12px; border-radius:6px; border:1px solid #333; background:#1a1a3e; color:#eee; font-size:13px; outline:none; }}
  #search input:focus {{ border-color:#F5D742; }}
  #search .hint {{ font-size:11px; color:#555; margin-top:4px; }}
  #legend {{ padding:8px 16px 4px; display:flex; flex-wrap:wrap; gap:4px 10px; font-size:11px; color:#999; border-bottom:1px solid #2a2a4a; }}
  #legend .dot {{ display:inline-block; width:12px; height:12px; border-radius:2px; vertical-align:middle; margin-right:3px; border:1px solid #333; }}
  #cat-list {{ flex:1; overflow-y:auto; padding-bottom:16px; }}
  .cat {{ margin-bottom:2px; }}
  .cat-hd {{ padding:6px 16px; cursor:pointer; display:flex; justify-content:space-between; font-size:13px; color:#999; }}
  .cat-hd:hover {{ color:#F5D742; background:rgba(245,215,66,0.05); }}
  .cat-hd .n {{ color:#555; font-size:11px; }}
  .cat-bd {{ display:none; padding:2px 8px 6px 20px; flex-wrap:wrap; gap:3px; }}
  .cat-bd.open {{ display:flex; }}
  .btn {{ padding:2px 8px; border-radius:3px; border:none; cursor:pointer; font-size:11px; color:#bbb; background:#1a1a3e; white-space:nowrap; }}
  .btn:hover {{ background:#F5D742; color:#111; }}
  .btn.act {{ background:#F5D742; color:#111; font-weight:bold; }}
  
  #main {{ flex:1; display:flex; flex-direction:column; }}
  #bar {{ padding:8px 20px; background:#111128; border-bottom:1px solid #2a2a4a; display:flex; align-items:center; gap:10px; min-height:40px; flex-wrap:wrap; }}
  #bar .nm {{ color:#F5D742; font-weight:bold; font-size:15px; }}
  #bar .tp {{ color:#888; font-size:12px; }}
  #bar .ds {{ color:#777; font-size:12px; flex:1; min-width:100px; }}
  #bar .sc {{ color:#555; font-size:11px; }}
  .bk {{ font-size:12px; color:#F5D742; text-decoration:none; flex-shrink:0; }}
  .bk:hover {{ color:#fff; }}
  
  #tab-bar {{ display:flex; flex-wrap:wrap; gap:2px; background:#0e0e2a; border-bottom:1px solid #2a2a4a; padding:4px 8px; flex-shrink:0; }}
  #tab-bar::-webkit-scrollbar {{ height:3px; }}
  #tab-bar::-webkit-scrollbar-thumb {{ background:#333; border-radius:2px; }}
  .tab {{ padding:4px 12px; cursor:pointer; font-size:11px; color:#666; border-radius:4px; flex-shrink:0; }}
  .tab:hover {{ color:#F5D742; background:rgba(245,215,66,0.08); }}
  .tab.tab-act {{ color:#F5D742; background:rgba(245,215,66,0.15); font-weight:bold; }}
  
  #net {{ flex:1; }}
  #plh {{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#444; gap:8px; }}
  #plh .i {{ font-size:48px; }}
  
  ::-webkit-scrollbar {{ width:5px; }}
  ::-webkit-scrollbar-track {{ background:#111128; }}
  ::-webkit-scrollbar-thumb {{ background:#333; border-radius:3px; }}
  .vis-tooltip {{ display:inline-block !important; background:#1a1a3e; border:1px solid #F5D742; color:#eee; font-size:12px; padding:4px 8px; border-radius:4px; line-height:1.5; white-space:pre-wrap; }}
</style>
</head>
<body>
<div id="app">

<div id="sidebar">
  <h1>🏛️ 家族树</h1>
  <div id="search">
    <input id="q" type="text" placeholder="搜角色..." oninput="doSearch()" />
    <div class="hint" id="status"></div>
  </div>
  <div id="legend">
    <span><span class="dot" style="background:#F5D742"></span>主神</span>
    <span><span class="dot" style="background:#D35400"></span>泰坦</span>
    <span><span class="dot" style="background:#2ECC71"></span>宁芙</span>
    <span><span class="dot" style="background:#E74C3C"></span>英雄</span>
    <span><span class="dot" style="background:#95A5A6"></span>凡人</span>
    <span><span class="dot" style="background:#8E44AD"></span>怪物</span>
    <span><span class="dot" style="background:#E67E22"></span>巨人</span>
    <span><span class="dot" style="background:#1ABC9C"></span>半兽</span>
    <span><span class="dot" style="background:#3498DB"></span>概念</span>
    <span><span class="dot" style="background:#7F8C8D"></span>其他</span>
  </div>
  <div id="cat-list"></div>
</div>

<div id="main">
  <div id="bar">
    <a class="bk" id="bkl" href="character_index.html">&larr; 角色索引</a>
    <span class="nm" id="fn">—</span>
    <span class="tp" id="ft"></span>
    <span class="ds" id="fd"></span>
    <span class="sc" id="fs"></span>
  </div>
  <div id="tab-bar"></div>
  <div id="net">
    <div id="plh">
      <div class="i">🏛️</div>
      <div>在左侧选择一个角色</div>
      <div style="font-size:12px;color:#444">支持 · 父母 · 配偶 · 情人 · 子女 · 孙子</div>
    </div>
  </div>
</div>

</div>

<script src="vis-network.min.js"></script>
<script>
var CATS = {json.dumps(cats_json, ensure_ascii=False)};
var CHARS = {json.dumps(chars_json, ensure_ascii=False)};
var FAMILIES = {json.dumps(families_json, ensure_ascii=False)};
var ALIASES = {aliases_js_code};
var ALIAS_REV = {{}};
for (var pk in ALIASES) {{ ALIASES[pk].forEach(function(a){{ ALIAS_REV[a] = pk; }}); }}
var net = null;
var curName = null;
var activeTab = 'core';

// --- 初始化左侧分类列表 ---
var listEl = document.getElementById('cat-list');
CATS.forEach(function(c){{
  var d = document.createElement('div'); d.className='cat';
  d.innerHTML = '<div class="cat-hd" onclick="toggle(this)"><span>'+c.label+'</span><span class="n">'+c.count+'</span></div>'+
    '<div class="cat-bd">'+c.names.map(function(n){{
      var prim = ALIAS_REV[n];
      if (prim) {{
        return '<button class="btn" data-name="'+n+'" data-primary="'+prim+'">'+n+'</button>';
      }}
      return '<button class="btn" data-name="'+n+'">'+n+'</button>';
    }}).join('')+'</div>';
  listEl.appendChild(d);
}});

// --- 点击代理：按钮点击 -> selectChar ---
listEl.addEventListener('click', function(e){{
  var el = e.target;
  while (el && el !== listEl) {{
    if (el.classList && el.classList.contains('btn')) {{
      selectChar(el.getAttribute('data-primary') || el.getAttribute('data-name'));
      return;
    }}
    el = el.parentNode;
  }}
}});

function toggle(h){{ h.nextElementSibling.classList.toggle('open'); }}
function doSearch(){{
  var q = document.getElementById('q').value.trim().toLowerCase();
  var c=0; document.querySelectorAll('.btn').forEach(function(b){{
    var nm = b.textContent.toLowerCase();
    var pk = b.getAttribute('data-primary');
    if (!nm.includes(q)) {{
      if (pk && ALIASES[pk] && ALIASES[pk].some(function(a){{ return a.toLowerCase().includes(q); }})) {{
        b.style.display=''; c++;
      }} else {{
        b.style.display='none';
      }}
    }} else {{
      b.style.display=''; c++;
    }}
    if(q) b.closest('.cat-bd').classList.add('open');
  }});
  document.getElementById('status').textContent=q?'找到 '+c+' 个角色':'';
}}



// --- 选择角色 + 配偶/情人分支标签页 ---
var activeTab = 'core';
var tabData = [];
var expandedKids = {{}};

function selectChar(name){{
  var dbg = document.getElementById("bar");
  if (!name) {{ dbg.innerHTML += " | name empty"; return; }}
  // 别名重定向
  if (ALIAS_REV[name]) {{
    name = ALIAS_REV[name];
  }}
  if (!CHARS[name]) {{ dbg.innerHTML += " | no CHARS: "+name; return; }}
  if (!FAMILIES[name]) {{ dbg.innerHTML += " | no FAMILIES: "+name; return; }}
  activeTab = 'core';
  expandedKids = {{}};
  curName = name;
  document.querySelectorAll(".btn.act").forEach(function(b){{b.classList.remove("act");}});
  document.querySelectorAll(".btn").forEach(function(b){{
    var pk = b.getAttribute('data-primary') || b.textContent;
    if (pk === name) b.classList.add("act");
  }});
  var ph = document.getElementById("plh");
  if (ph) ph.style.display="none";
  var d=CHARS[name];
  document.getElementById("fn").textContent=name;
  document.getElementById("ft").textContent=d.type||"";
  var aliases = ALIASES[name];
  var aliasTxt = aliases ? ' [' + aliases.join('/') + ']' : '';
  document.getElementById("fd").textContent=(d.desc||"") + aliasTxt;
  document.getElementById("fs").textContent=d.ch?"ch:"+d.ch:"";
  buildTabs();
  drawFamily(name);
}}

function buildTabs(){{
  var fam = FAMILIES[curName];
  if (!fam) return;
  tabData = [{{id:"core", label:"直系"}}];
  var seen = {{}};
  fam.spouses.forEach(function(s){{
    if (!seen[s.name]) {{ seen[s.name]=true; tabData.push({{id:"sp_"+s.name, label:s.name, type:"spouse", partner:s.name, ch:s.ch, pages:s.pages}}); }}
  }});
  fam.lovers.forEach(function(l){{
    if (!seen[l.name]) {{ seen[l.name]=true; tabData.push({{id:"lv_"+l.name, label:l.name, type:"lover", partner:l.name, ch:l.ch, pages:l.pages}}); }}
  }});
  var bar = document.getElementById("tab-bar");
  bar.innerHTML = tabData.map(function(t){{
    var act = t.id === activeTab ? " tab-act" : "";
    return '<span class="tab'+act+'" data-tab="'+t.id+'">'+t.label+'</span>';
  }}).join("");
  // Ensure default core tab is active
  var def = document.getElementById("tab-bar").querySelector('[data-tab="core"]');
  if (def) def.classList.add("tab-act");
}}

function switchTab(tid){{
  activeTab = tid;
  document.querySelectorAll(".tab").forEach(function(t){{t.classList.remove("tab-act");}});
  var el = document.querySelector('.tab[data-tab="'+tid+'"]');
  if (el) el.classList.add("tab-act");
  if (curName) drawFamily(curName);
}}

// Tab bar click delegation
document.getElementById("tab-bar").addEventListener("click", function(e){{
  var el = e.target;
  while (el && el !== this) {{
    if (el.classList && el.classList.contains("tab")) {{
      switchTab(el.getAttribute("data-tab"));
      return;
    }}
    el = el.parentNode;
  }}
}});

function drawFamily(name){{
  try {{
    if (typeof vis === "undefined") {{ document.getElementById("net").innerHTML = "<div>vis.js not loaded</div>"; return; }}
    var fam = FAMILIES[name];
    if (!fam) {{ document.getElementById("net").innerHTML = "<div>no data</div>"; return; }}
    var nodes=[], edges=[];
    var added={{}};
    var CCMAP = {{"主神":"#F5D742","泰坦":"#D35400","宁芙":"#2ECC71","英雄":"#E74C3C","凡人":"#95A5A6","怪物":"#8E44AD","巨人":"#E67E22","半兽":"#1ABC9C","概念":"#3498DB","团体/其他":"#7F8C8D"}};
    function col(n){{ var c = CHARS[n]; return c ? (CCMAP[c.type]||"#BDC3C7") : "#BDC3C7"; }}
    function fmtEv(ch, pages){{
      if ((!ch || ch==="") && (!pages || !pages.length)) return "";
      var a = [];
      if (ch && ch!=="") a.push("第" + ch + "章");
      if (pages && pages.length) a.push("p." + pages.slice().sort(function(x,y){{return x-y;}}).join(","));
      return a.join(" ");
    }}
    function nodeTitle(nm){{
      var c = CHARS[nm];
      if (!c) return nm;
      var txt = c.desc || nm;
      if (c.ch) txt += "\\n【第" + c.ch + "章】";
      if (c.pages && c.pages.length) txt += "\\np." + c.pages.sort(function(a,b){{return a-b;}}).join(",");
      return txt;
    }}
    function addNode(id,label,level,color){{
      if(added[id]) return; added[id]=true;
      var bg = color || "#BDC3C7";
      var isBig = level <= 1;
      nodes.push({{id:id,label:label,level:level,shape:"box",color:{{background:bg,border:"#333"}},font:{{size:isBig?13:11,color:"#111",face:"Verdana,sans-serif"}},borderWidth:isBig?2:1.5,widthConstraint:{{minimum:isBig?80:60,maximum:200}},title:nodeTitle(id)}});
    }}
    function addEdge(fr,to,label,color,dash,title){{
      edges.push({{from:fr,to:to,label:label,color:color||"#666",dashes:dash||false,title:title||"",width:2,font:{{size:9,color:"#aaa"}}}});
    }}

    // Level 0: Parents (always shown)
    fam.parents.forEach(function(p){{
      addNode(p.name, p.name, 0, col(p.name), p.name);
      addEdge(p.name, name, "", "#4a90d9", false, fmtEv(p.ch, p.pages));
    }});

    // Level 1: Self (always shown)
    addNode(name, name, 1, col(name), name);

    if (activeTab === "core") {{
      // 直系：显示父母+自己+所有子女
      fam.children.forEach(function(c){{
        var cHasKids = (fam.grandchildren||[]).some(function(g){{return g.parent === c.name;}});
        var cLabel = c.name + (cHasKids ? (expandedKids[c.name] ? " ▼" : " ▶") : "");
        addNode(c.name, cLabel, 2, col(c.name), c.name);
        addEdge(name, c.name, "", "#2ecc71", false, fmtEv(c.ch, c.pages));
        if (expandedKids[c.name]) {{
          var grandkids = (fam.grandchildren||[]).filter(function(g){{return g.parent === c.name;}});
          grandkids.forEach(function(g){{
            var glabel = g.name;
            var gpar = FAMILIES[g.name] && FAMILIES[g.name].parents;
            if (gpar && gpar.length > 0) {{
              glabel += " (" + gpar.map(function(p){{return p.name;}}).join("&") + ")";
            }}
            addNode(g.name, glabel, 3, col(g.name), g.name);
            addEdge(c.name, g.name, "", "#2ecc71", false, fmtEv(g.ch, g.pages));
          }});
        }}
      }});
    }} else {{
      // 找到当前选中的配偶/情人
      var tab = tabData.find(function(t){{return t.id === activeTab;}});
      if (!tab) {{ document.getElementById("net").innerHTML = "<div>tab not found</div>"; return; }}
      var pname = tab.partner;
      var isSp = tab.type === "spouse";

      // Level 1: 本人 + 配偶/情人 + 聚合节点 ⚤
      addNode(name, name, 1, col(name), name);
      addNode(pname, pname, 1, col(pname), pname);
      var cpMainId = "__cp__" + name + "__" + pname;
      if (!added[cpMainId]) {{
        added[cpMainId] = true;
        nodes.push({{id:cpMainId, label:"⚤", level:1, color:{{background:"#555",border:"#333"}}, shape:"diamond", size:22, font:{{size:12,color:"#eee"}}, borderWidth:1}});
        addEdge(name, cpMainId, "", isSp ? "#e74c3c" : "#e67e22", !isSp, fmtEv(tab.ch, tab.pages));
        addEdge(cpMainId, pname, "", "#666", false, "");
      }}

      // Level 2: 共同的子女（从聚合节点 ⚤ 出线）
      var mutual = fam.children.filter(function(c){{return c.other_parent === pname;}});
      // 共同生育孙辈的子女挨在一起排列
      var coNext = {{}};
      mutual.forEach(function(a, ai) {{
        mutual.forEach(function(b, bi) {{
          if (ai >= bi) return;
          var share = (fam.grandchildren||[]).some(function(g) {{
            var gp = FAMILIES[g.name] && FAMILIES[g.name].parents;
            return gp && gp.some(function(p){{return p.name === a.name;}}) &&
                   gp.some(function(p){{return p.name === b.name;}});
          }});
          if (share) {{
            (coNext[a.name] || (coNext[a.name] = [])).push(b.name);
            (coNext[b.name] || (coNext[b.name] = [])).push(a.name);
          }}
        }});
      }});
      var sorted = [];
      var remain = mutual.map(function(c){{return c.name;}});
      while (remain.length > 0) {{
        if (sorted.length === 0) {{
          sorted.push(remain.shift());
        }} else {{
          var last = sorted[sorted.length - 1];
          var idx = -1;
          if (coNext[last]) {{
            for (var ri = 0; ri < remain.length; ri++) {{
              if (coNext[last].indexOf(remain[ri]) >= 0) {{ idx = ri; break; }}
            }}
          }}
          if (idx >= 0) {{
            sorted.push(remain.splice(idx, 1)[0]);
          }} else {{
            sorted.push(remain.shift());
          }}
        }}
      }}
      var rank = {{}};
      sorted.forEach(function(n, i){{rank[n] = i;}});
      mutual.sort(function(a, b){{return rank[a.name] - rank[b.name];}});
      // 夫妇聚合节点：共同生育孙辈的家长之间放一个中间点
      var cpNodes = {{}};
      mutual.forEach(function(a) {{
        mutual.forEach(function(b) {{
          if (a.name >= b.name) return;
          var share = (fam.grandchildren||[]).some(function(g) {{
            var gp = FAMILIES[g.name] && FAMILIES[g.name].parents;
            return gp && gp.some(function(p){{return p.name === a.name;}}) &&
                   gp.some(function(p){{return p.name === b.name;}});
          }});
          if (share) {{
            var key = a.name + "__" + b.name;
            if (!cpNodes[key]) {{
              var kidNames = (fam.grandchildren||[]).filter(function(g) {{
                var gp = FAMILIES[g.name] && FAMILIES[g.name].parents;
                return gp && gp.some(function(p){{return p.name === a.name;}}) &&
                       gp.some(function(p){{return p.name === b.name;}});
              }}).map(function(g){{return g.name;}});
              cpNodes[key] = {{id: "__cp__" + key, a: a.name, b: b.name, kids: kidNames}};
            }}
          }}
        }});
      }});
      mutual.forEach(function(c){{
        var cHasKids = (fam.grandchildren||[]).some(function(g){{return g.parent === c.name;}});
        var cLabel = c.name + (cHasKids ? (expandedKids[c.name] ? " ▼" : " ▶") : "");
        addNode(c.name, cLabel, 2, col(c.name), c.name);
        addEdge(cpMainId, c.name, "", "#2ecc71", false, fmtEv(c.ch, c.pages));

        // 子女的配偶（已隐藏）

        if (expandedKids[c.name]) {{
        // Level 3: 孙辈 — 通过夫妇聚合节点连线
        var grandkids = (fam.grandchildren||[]).filter(function(g){{return g.parent === c.name;}});
        var cpEdge = {{}};
        grandkids.forEach(function(g){{
          var myCp = null;
          for (var cpk in cpNodes) {{
            if (cpNodes[cpk].kids.indexOf(g.name) >= 0) {{ myCp = cpNodes[cpk]; break; }}
          }}
          if (myCp) {{
            if (!added[myCp.id]) {{
              added[myCp.id] = true;
              nodes.push({{id:myCp.id, label:"⚤", level:2, color:{{background:"#555",border:"#333"}}, shape:"diamond", size:22, font:{{size:12,color:"#eee"}}, borderWidth:1}});
              addEdge(myCp.a, myCp.id, "", "#888", false, "");
              addEdge(myCp.id, myCp.b, "", "#888", false, "");
            }}
            if (!added[g.name]) {{
              var glabel = g.name;
              var gpar = FAMILIES[g.name] && FAMILIES[g.name].parents;
              if (gpar && gpar.length > 0) {{
                glabel += " (" + gpar.map(function(p){{return p.name;}}).join("&") + ")";
              }}
              addNode(g.name, glabel, 3, col(g.name), g.name);
            }}
            var ek = myCp.id + "->" + g.name;
            if (!cpEdge[ek]) {{ cpEdge[ek] = true; addEdge(myCp.id, g.name, "", "#2ecc71", false, fmtEv(g.ch, g.pages)); }}
          }} else {{
            if (!added[g.name]) {{
              var glabel = g.name;
              var gpar = FAMILIES[g.name] && FAMILIES[g.name].parents;
              if (gpar && gpar.length > 0) {{
                glabel += " (" + gpar.map(function(p){{return p.name;}}).join("&") + ")";
              }}
              addNode(g.name, glabel, 3, col(g.name), g.name);
            }}
            addEdge(c.name, g.name, "", "#2ecc71", false, fmtEv(g.ch, g.pages));
          }}          // 孙辈配偶
          var gfam = FAMILIES[g.name];
          if (gfam && gfam.spouses) {{
            gfam.spouses.forEach(function(s){{
              if (!added[s.name]) {{ addNode(s.name, s.name, 3, col(s.name), s.name); }}
              addEdge(g.name, s.name, "", "#e74c3c", false, fmtEv(s.ch, s.pages));
            }});
          }}
        }});
        }}
      }});
    }}

    // --- Manual position calculation (no hierarchical layout) ---
    var xSp=160;
    var byLv=[]; nodes.forEach(function(n){{if(!byLv[n.level])byLv[n.level]=[];byLv[n.level].push(n);}});
    // Dynamic vertical spacing: count edges between adjacent levels, increase gap when dense
    var baseGap=200, extraPerEdge=15, edgeThresh=4;
    var edgeCnt={{}};
    edges.forEach(function(e){{
      var fl=-1,tl=-1;
      nodes.forEach(function(n){{
        if(n.id===e.from)fl=n.level;
        if(n.id===e.to)tl=n.level;
      }});
      if(fl>=0&&tl>=0&&fl<tl){{var k=fl+'-'+tl;edgeCnt[k]=(edgeCnt[k]||0)+1;}}
    }});
    var yB=[60];
    for(var lv=1;lv<=3;lv++){{
      var k=(lv-1)+'-'+lv,c=edgeCnt[k]||0;
      yB[lv]=yB[lv-1]+baseGap+Math.max(0,(c-edgeThresh))*extraPerEdge;
    }}
    // Level 0: parents centered around x=0
    if(byLv[0])byLv[0].forEach(function(n,i){{n.x=(i-(byLv[0].length-1)/2)*120;n.y=yB[0];}});
    // Level 1: self ◆ partner — ◆ at exact midpoint
    var sN=nodes.find(function(n){{return n.id===name;}});
    var cP=nodes.find(function(n){{return(''+n.id).indexOf('__cp__')===0;}});
    var pN=nodes.find(function(n){{return n.id===pname;}});
    if(sN){{sN.x=-xSp;sN.y=yB[1];}}
    if(cP){{cP.x=0;cP.y=yB[1];}}
    if(pN){{pN.x=xSp;pN.y=yB[1];}}
    // Level 2: children first, then ◆ at midpoint between co-parents
    if(byLv[2]&&typeof mutual!=='undefined'){{
      var cNms=mutual.map(function(c){{return c.name;}});
      var cSp=xSp*1.1,cTw=(cNms.length-1)*cSp,cSx=-cTw/2;
      cNms.forEach(function(cn,i){{var n=nodes.find(function(nn){{return nn.id===cn;}});if(n){{n.x=cSx+i*cSp;n.y=yB[2];}}}});
      for(var k in cpNodes){{
        var p=k.split('__');
        var aN=nodes.find(function(nn){{return nn.id===p[0];}});
        var bN=nodes.find(function(nn){{return nn.id===p[1];}});
        var cp2=nodes.find(function(nn){{return nn.id===cpNodes[k].id;}});
        if(aN&&bN&&cp2){{cp2.x=(aN.x+bN.x)/2;cp2.y=yB[2];}}
      }}
    }}
    if(byLv[2])byLv[2].forEach(function(n,i){{if(typeof n.x==='undefined'){{n.x=(i-(byLv[2].length-1)/2)*xSp;n.y=yB[2];}}}});
    // Level 3: grandchildren evenly distributed
    if(byLv[3])byLv[3].forEach(function(n,i){{n.x=(i-(byLv[3].length-1)/2)*xSp*0.9;n.y=yB[3];}});
    nodes.forEach(function(n){{delete n.level;}});
    // DataSet
    var nodeDS = new vis.DataSet(nodes);
    var edgeDS = new vis.DataSet(edges);

    // Render vis.js network
    var bar = document.getElementById("bar");
    var tabBar = document.getElementById("tab-bar");
    var container = document.getElementById("net");
    var mainEl = container.parentNode;
    var containerH = mainEl.offsetHeight - bar.offsetHeight - (tabBar ? tabBar.offsetHeight : 0);
    var containerW = mainEl.offsetWidth;
    container.style.width = containerW + "px";
    container.style.height = containerH + "px";
    container.style.position = "relative";
    container.style.overflow = "hidden";
    var ph = document.getElementById("plh");
    if (ph) ph.style.display="none";
    if (net) {{ try {{ net.destroy(); }} catch(e) {{}} net = null; }}
    container.innerHTML = "";
    if (nodes.length === 0) {{ container.innerHTML = "<div style='padding:20px;color:#666'>直系视图：仅显示父母</div>"; return; }}
    net = new vis.Network(container,
      {{nodes:nodeDS, edges:edgeDS}},
      {{
        layout: {{improvedLayout:false}},
        interaction: {{hover:true, tooltipDelay:100, navigationButtons:true, keyboard:true}},
        nodes: {{borderWidth:2}},
        edges: {{smooth:true, font: {{size:9, color:"#aaa"}}}},
        physics: false
      }}
    );

    // 点击子女节点展开/收起孙辈
    net.on("click",function(p){{
      var id = net.getNodeAt(p.pointer.DOM);
      if (!id) return;
      if (fam.grandchildren && fam.grandchildren.some(function(g){{return g.parent === id;}})) {{
        expandedKids[id] = !expandedKids[id];
        drawFamily(curName);
      }}
    }});
    document.getElementById("fs").textContent += " | 节点:"+nodes.length+" 连线:"+edges.length;
  document.getElementById("bkl").href = "character_index.html?name="+encodeURIComponent(curName);
  }} catch(e) {{
    document.getElementById("net").innerHTML = "Error: " + e.message;
    net = null;
  }}
}}

// URL参数: ?name=X 自动选择角色
(function(){{
  var p = new URLSearchParams(window.location.search).get('name');
  if (p) {{
    var target = ALIAS_REV[p] || p;
    if (CHARS[target]) {{ setTimeout(function(){{ selectChar(target); }}, 100); }}
  }}
}})();
</script>
</body>
</html>"""
    return html


def main():
    print("Mythos AI — 家族树 v2")
    print("=" * 50)
    kg = load_data()
    chars, by_src, by_tgt = build_indices(kg)
    print(f"加载: {len(chars)} 角色, {len(kg['relationships'])} 关系")
    alias_map, aliases_json = build_aliases(kg["characters"], kg["relationships"])
    if alias_map:
        print(f"别名映射: {len(alias_map)} 个别名 → 主名")
    families = precompute_families(chars, by_src, by_tgt, alias_map)
    print(f"预计算: {len(families)} 个角色的家族数据")
    html = generate_html(kg, families, aliases_json)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[OK] generated: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
