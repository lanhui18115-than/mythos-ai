"""
Mythos AI — 角色索引生成器 (12_character_index.py)
Output: output/character_index.html + data/char_index_data.js
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
GRAPH_FILE = DATA_DIR / "knowledge_graph.json"
ALT_NAMES_FILE = DATA_DIR / "alternate_names.json"
ENHANCED_MYTHS_FILE = DATA_DIR / "enhanced_myth_summaries.json"
ARTWORK_IMAGES_FILE = DATA_DIR / "artwork_image_map.json"
OUTPUT_FILE = OUTPUT_DIR / "character_index.html"
DATA_OUTPUT_FILE = DATA_DIR / "char_index_data.js"

TYPE_COLORS = {
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

REL_MAP = {
    "parent_of": "children", "child_of": "parents", "spouse_of": "spouses",
    "lover_of": "lovers", "sibling_of": "siblings", "brother_of": "siblings",
    "sister_of": "siblings", "cousin_of": "cousins", "grandchild_of": "grandparents",
    "grandparent_of": "grandchildren", "grandfather_of": "grandchildren",
    "uncle_of": "uncles", "nephew_of": "nephews", "daughter_of": "parents",
    "son_of": "parents", "mother_of": "children", "father_of": "children",
    "killed_by": "killed_by", "killed": "killed",
}


def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_character_data():
    kg = load_json(GRAPH_FILE)
    alt_names = load_json(ALT_NAMES_FILE)
    enhanced_myths = load_json(ENHANCED_MYTHS_FILE)
    myth_map = {m["name"]: m for m in kg.get("myths", [])}
    artwork_map = {a["name"]: a for a in kg.get("artworks", [])}
    artwork_images = load_json(ARTWORK_IMAGES_FILE)

    char_rels = defaultdict(lambda: defaultdict(list))
    char_artworks = defaultdict(list)
    char_participates = defaultdict(set)
    char_myths_set = defaultdict(set)

    for rel in kg.get("relationships", []):
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        rtype = rel.get("type", "")
        for key, val in REL_MAP.items():
            if rtype == key:
                char_rels[src][val].append(tgt)
                rev = None
                if val == "parents": rev = "children"
                elif val == "children": rev = "parents"
                elif val == "spouses": rev = "spouses"
                elif val == "siblings": rev = "siblings"
                if rev:
                    char_rels[tgt][rev].append(src)
                break
        if rtype == "depicted_in" and tgt in artwork_map:
            art = artwork_map[tgt]
            char_artworks[src].append({
                "name": tgt,
                "description": art.get("description", ""),
                "type": art.get("type", ""),
                "images": artwork_images.get(art.get("id", ""), []),
            })
        if rtype == "participates_in":
            char_participates[src].add(tgt)

    for m in kg.get("myths", []):
        for kc in m.get("key_characters", []):
            char_myths_set[kc].add(m["name"])

    name_map = load_json(DATA_DIR / "name_map.json")

    # Build flat list of (chinese_name, english_name) pairs sorted by length desc
    name_pairs = []
    for en, cn_list in name_map.items():
        if isinstance(cn_list, str):
            cn_list = [cn_list]
        for cn in cn_list:
            if cn:
                name_pairs.append((cn, en))
    name_pairs.sort(key=lambda x: -len(x[0]))

    def annotate_all(text):
        """Annotate ALL character Chinese names in the text with English."""
        if not text:
            return text
        result = ""
        i = 0
        while i < len(text):
            matched = False
            for cn, en in name_pairs:
                if text[i:i+len(cn)] == cn:
                    after = text[i+len(cn):i+len(cn)+len(en)+2]
                    if after == f"({en})":
                        result += text[i:i+len(cn)+len(en)+2]
                        i += len(cn) + len(en) + 2
                        matched = True
                        break
                    # Avoid matching inside existing annotation parens
                    if i > 0 and text[i-1] == "(" and text[i+len(cn):i+len(cn)+1] == ")":
                        i += len(cn)
                        matched = True
                        break
                    result += f"{cn}({en})"
                    i += len(cn)
                    matched = True
                    break
            if not matched:
                result += text[i]
                i += 1
        return result

    # Pre-annotate all myth summaries
    annotate_cache = {}
    for mname, summary in enhanced_myths.items():
        annotate_cache[mname] = annotate_all(summary)

    def myth_relevance(name, mname, mi):
        if name.lower() in mname.lower():
            return 1
        kc_list = mi.get("key_characters", [])
        try:
            return 1 if kc_list.index(name) < 3 else 0
        except ValueError:
            return 0

    characters = kg.get("characters", [])
    char_list = []
    type_groups = defaultdict(list)

    for c in characters:
        name = c["name"]
        ctype = c.get("type", "other")
        label = TYPE_LABELS.get(ctype, "团体/其他")
        type_groups[label].append(name)

        myths_data = []
        seen = set()
        for mname in c.get("major_myths", []):
            if mname not in seen:
                seen.add(mname)
                mi = myth_map.get(mname, {})
                myths_data.append({
                    "n": mname,
                    "s": annotate_cache.get(mname, mi.get("summary", "")),
                    "rl": myth_relevance(name, mname, mi),
                })
        for mname in char_participates.get(name, set()):
            if mname not in seen and mname in myth_map:
                seen.add(mname)
                mi = myth_map[mname]
                myths_data.append({
                    "n": mname,
                    "s": annotate_cache.get(mname, mi.get("summary", "")),
                    "rl": 1,
                })
        for mname in char_myths_set.get(name, set()):
            if mname not in seen:
                seen.add(mname)
                mi = myth_map.get(mname, {})
                myths_data.append({
                    "n": mname,
                    "s": annotate_cache.get(mname, mi.get("summary", "")),
                    "rl": myth_relevance(name, mname, mi),
                })

        rels = char_rels.get(name, {})
        def uniq(items):
            r, seen = [], set()
            for x in items:
                if x not in seen:
                    seen.add(x); r.append(x)
            return r

        char_list.append({
            "n": name,
            "r": c.get("roman_name", ""),
            "a": alt_names.get(name, []),
            "e": c.get("epithets", []),
            "t": ctype,
            "tl": TYPE_LABELS.get(ctype, ctype),
            "co": TYPE_COLORS.get(ctype, "#7F8C8D"),
            "d": c.get("domains", []),
            "sy": c.get("symbols", []),
            "de": c.get("description", ""),
            "m": myths_data,
            "ar": char_artworks.get(name, []),
            "ev": c.get("evidence", []),
            "pc": c.get("primary_chapter", 0),
            "p": uniq(rels.get("parents", [])),
            "ch": uniq(rels.get("children", [])),
            "sp": uniq(rels.get("spouses", [])),
            "l": uniq(rels.get("lovers", [])),
            "si": uniq(rels.get("siblings", [])),
        })

    return char_list, dict(type_groups)


def main():
    print("构建角色数据...")
    characters, type_groups = build_character_data()
    print(f"已处理 {len(characters)} 个角色, {len(type_groups)} 个分组")

    print("保存数据文件...")
    js_data = "var CD=" + json.dumps(characters, ensure_ascii=False) + ";"
    DATA_OUTPUT_FILE.write_text(js_data, encoding="utf-8")

    # Build filter buttons
    fb = '<button class="on" data-t="all" onclick="fil(\'all\')">全部 <span>'+str(len(characters))+'</span></button>'
    for ct in TYPE_ORDER:
        if ct in type_groups:
            fb += '<button data-t="'+ct+'" onclick="fil(\''+ct+'\')">'+ct+' <span>'+str(len(type_groups[ct]))+'</span></button>'

    html_pre = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mythos AI - \u89d2\u8272\u7d22\u5f15</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Segoe UI,sans-serif;background:#0a0a1a;color:#eee}
.c{max-width:1400px;margin:0 auto;padding:20px}
h1{color:#F5D742;font-size:28px;text-align:center}
.hd{color:#666;font-size:13px;text-align:center;margin-bottom:16px}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:#111128;border:1px solid #2a2a4a;border-radius:8px;padding:10px 14px;margin-bottom:10px}
.bar input{flex:1;min-width:160px;padding:8px 12px;border-radius:6px;border:1px solid #333;background:#1a1a3e;color:#eee;font-size:14px;outline:none}
.bar input:focus{border-color:#F5D742}
.bar .st{font-size:12px;color:#888}
.fb{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:10px}
.fb button{padding:4px 10px;border:1px solid #2a2a4a;border-radius:5px;background:transparent;color:#888;cursor:pointer;font-size:12px}
.fb button:hover{border-color:#F5D742;color:#ddd}
.fb button.on{background:#F5D742;color:#111;font-weight:bold}
.fb button span{color:#555;font-size:10px;margin-left:2px}
.fb button.on span{color:#111}
.gr{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.cd{background:#111128;border:1px solid #2a2a4a;border-radius:8px;padding:12px;cursor:pointer;transition:all 0.15s;position:relative;overflow:hidden}
.cd:hover{border-color:#F5D742;transform:translateY(-1px)}
.cd .tp{position:absolute;top:0;left:0;right:0;height:3px}
.cd .nm{font-size:15px;font-weight:bold;color:#eee}
.cd .rm{font-size:11px;color:#666;margin-top:1px}
.cd .al{font-size:11px;color:#555}
.cd .tg{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;margin-top:4px;background:rgba(255,255,255,0.05);color:#888;border:1px solid #2a2a4a}
.cd .ds{font-size:11px;color:#777;margin-top:4px;line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.mv{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:100;overflow-y:auto;padding:30px 16px}
.mv.s{display:block}
.mo{max-width:860px;margin:0 auto;background:#0e0e2a;border:1px solid #2a2a4a;border-radius:12px;overflow:hidden}
.mh{display:flex;gap:12px;padding:16px 20px;background:#111128;border-bottom:1px solid #2a2a4a}
.mh .mi{flex:1;min-width:0}
.mh .cl{cursor:pointer;font-size:22px;color:#555;flex-shrink:0}
.mh .cl:hover{color:#e74c3c}
.mh h2{font-size:22px;color:#F5D742;word-break:break-all}
.mh .s1{font-size:12px;color:#888}
.mh .s2{font-size:12px;color:#666}
.mh .ty{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;margin-top:3px}
.mb{padding:0 20px 16px}
.ms{margin-top:14px}
.ms h3{font-size:14px;color:#F5D742;margin-bottom:6px;padding-bottom:3px;border-bottom:1px solid #1a1a3e;word-break:break-all}
.ms .ts{display:flex;flex-wrap:wrap;gap:4px}
.ms .ts span{padding:2px 8px;border-radius:4px;font-size:11px;background:#1a1a3e;border:1px solid #2a2a4a;color:#bbb}
.fm{margin-top:6px;font-size:12px}
.fm b{color:#666;font-weight:normal}
.fm .fi{display:inline-flex;flex-wrap:wrap;gap:4px;margin-left:4px}
.fm .fi span{padding:2px 7px;border-radius:3px;background:#1a1a3e;border:1px solid #2a2a4a;color:#bbb;cursor:pointer;font-size:11px}
.fm .fi span:hover{border-color:#F5D742}
.my{background:#111128;border:1px solid #2a2a4a;border-radius:6px;padding:8px 12px;margin-bottom:5px}
.my .mn{font-size:12px;font-weight:bold;color:#F5D742;cursor:pointer}
.my .mn:hover{text-decoration:underline}
.my .msu{font-size:11px;color:#888;line-height:1.5;margin-top:3px;display:none}
.my .msu.s{display:block}
.myi{opacity:0.5}
.myi .mn{color:#777}
.myt{font-size:10px;color:#555;font-weight:normal;margin-left:3px}
.mer{font-size:11px;color:#F5D742;margin-bottom:3px;padding-bottom:2px;border-bottom:1px solid #2a2a4a}
.aw{background:#111128;border:1px solid #2a2a4a;border-radius:6px;padding:10px;margin-bottom:6px}
.aw .awr{text-align:center;margin-bottom:4px;background:#0a0a1a;border-radius:4px;padding:4px;min-height:36px}
.aw .awr img{max-width:100%;max-height:160px;border-radius:3px;cursor:zoom-in}
.aw .awr img.f{max-height:none;cursor:zoom-out}
.aw .an{font-size:12px;font-weight:bold;color:#ddd}
.aw .ad{font-size:11px;color:#777;margin-top:2px;line-height:1.4}
.rf{font-size:11px;color:#555;line-height:1.5}
.nf{text-align:center;padding:40px 20px;color:#444;font-size:14px}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#111128}
::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
</style>
</head>
<body>
<div class="c">
<h1>Mythos AI \u2014 \u89d2\u8272\u7d22\u5f15</h1>
<div class="hd">Greek &amp; Roman Mythological Character Index</div>
<div class="bar">
<input id="q" type="text" placeholder="\u641c\u7d22\u540d\u79f0/\u79f0\u53f7/\u5f02\u4f53..." oninput="sch()">
<span class="st" id="st">\u52a0\u8f7d\u4e2d...</span>
</div>
<div class="fb" id="fb">''' + fb + '''</div>
<div class="gr" id="gr"></div>
<div class="nf" id="nf" style="display:none">\u672a\u627e\u5230\u5339\u914d\u89d2\u8272</div>
</div>
<div class="mv" id="mv" onclick="if(event.target===this)cls()"><div class="mo" id="mc"></div></div>
<script src="../data/char_index_data.js"></script>
<script>
var D=typeof CD!=='undefined'?CD:[],ct='all',sq='',DD=document;

function es(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}

function fl(){var l=D;if(ct!='all')l=l.filter(function(x){return x.tl==ct});if(sq){var q=sq.toLowerCase();l=l.filter(function(x){return x.n.toLowerCase().indexOf(q)>=0||(x.r&&x.r.toLowerCase().indexOf(q)>=0)||(x.a&&x.a.some(function(v){return v.toLowerCase().indexOf(q)>=0}))||(x.e&&x.e.some(function(v){return v.toLowerCase().indexOf(q)>=0}))||(x.d&&x.d.some(function(v){return v.toLowerCase().indexOf(q)>=0}))})}return l}

function rd(){var l=fl(),h='';for(var i=0;i<l.length;i++){var c=l[i];h+='<div class="cd" onclick="om('+i+')"><div class="tp" style="background:'+c.co+'"></div><div class="nm">'+es(c.n)+'</div>';if(c.r)h+='<div class="rm">'+es(c.r)+'</div>';if(c.a&&c.a.length)h+='<div class="al">('+es(c.a.join(', '))+')</div>';h+='<span class="tg">'+es(c.tl)+'</span>';if(c.de)h+='<div class="ds">'+es(c.de)+'</div>';h+='</div>'}DD.getElementById('gr').innerHTML=h||'<div class="nf" style="display:block">\u672a\u627e\u5230\u5339\u914d\u89d2\u8272</div>';DD.getElementById('st').innerHTML='\u663e\u793a <b>'+l.length+'</b> / <b>'+D.length+'</b> \u4e2a\u89d2\u8272'}

function sch(){sq=DD.getElementById('q').value;rd()}
function fil(t){ct=t;DD.querySelectorAll('#fb button').forEach(function(b){b.className=b.getAttribute('data-t')==t?'on':''});rd()}

function om(i){var c=fl()[i];if(!c)return
var ro=c.r&&c.r!=c.n?'<div class="s1">Roman: '+es(c.r)+'</div>':''
var al=c.a&&c.a.length?'<div class="s2">Also: '+es(c.a.join(', '))+'</div>':''
var ep=c.e&&c.e.length?'<div class="ms"><h3>Epithets / \u522b\u79f0</h3><div class="ts">'+c.e.map(function(x){return '<span>'+es(x)+'</span>'}).join('')+'</div></div>':''
var dm=c.d&&c.d.length?'<div class="ms"><h3>Domains / \u9886\u57df</h3><div class="ts">'+c.d.map(function(x){return '<span>'+es(x)+'</span>'}).join('')+'</div></div>':''
var sy=c.sy&&c.sy.length?'<div class="ms"><h3>Symbols / \u8c61\u5f81</h3><div class="ts">'+c.sy.map(function(x){return '<span>'+es(x)+'</span>'}).join('')+'</div></div>':''
var fa=''
function mk(l,it){if(!it||!it.length)return '';var x='<div class="fm"><b>'+l+': </b><span class="fi">';for(var k=0;k<it.length;k++){x+='<span class="fn" data-n="'+es(it[k])+'">'+es(it[k])+'</span>'}x+='</span></div>';return x}
if(c.p.length||c.ch.length||c.sp.length||c.l.length||c.si.length){fa='<div class="ms"><h3>Family / \u5bb6\u65cf\u5173\u7cfb <a class="ftl" href="family_tree.html?name='+es(c.n)+'" target="_blank" style="font-size:11px;color:#F5D742;font-weight:normal;float:right;text-decoration:none">\u67e5\u770b\u5bb6\u8c31\u56fe \u2192</a></h3>'+mk('Parents',c.p)+mk('Spouses',c.sp)+mk('Lovers',c.l)+mk('Children',c.ch)+mk('Siblings',c.si)+'</div>'}
var mh='';if(c.m&&c.m.length){var dc=c.m.filter(function(x){return x.rl}).length;mh='<div class="ms"><h3>Myths / \u76f8\u5173\u795e\u8bdd ('+dc+' direct, '+(c.m.length-dc)+' indirect)</h3>';for(var j=0;j<c.m.length;j++){var m=c.m[j];var sid='msu_'+i+'_'+j;mh+='<div class="my'+(m.rl?'':' myi')+'"><div class="mn mtg" data-tid="'+sid+'">'+es(m.n)+(m.rl?'':' <span class="myt">(indirect)</span>')+' &#9660;</div><div class="msu" id="'+sid+'"><div class="mer">'+es(c.n)+(c.r&&c.r!=c.n?' ('+es(c.r)+')':'')+'</div>'+es(m.s)+'</div></div>'}mh+='</div>'}
var ah='';if(c.ar&&c.ar.length){ah='<div class="ms"><h3>Artworks / \u76f8\u5173\u827a\u672f\u54c1 ('+c.ar.length+')</h3>';for(var j=0;j<c.ar.length;j++){var a=c.ar[j];ah+='<div class="aw">';if(a.images&&a.images.length)ah+='<div class="awr"><img src="'+es(a.images[0])+'" alt="'+es(a.name)+'" class="awi" onerror="this.remove()">';ah+='<div class="an">'+es(a.name)+'</div><div class="ad">'+es(a.description)+'</div></div>'}ah+='</div>'}
var eh='';if(c.ev&&c.ev.length){eh='<div class="ms"><h3>Sources / \u51fa\u5904</h3><div class="rf">';for(var j=0;j<c.ev.length;j++){var e=c.ev[j];eh+='<div>Chapter '+e.chapter+' \u00b7 Page '+(e.printed_pages||[]).join(', ')+'</div>'}eh+='</div></div>'}

var co='<div class="mh"><div class="mi"><h2>'+es(c.n)+'</h2>'+ro+al+'<span class="ty" style="background:'+c.co+'20;color:'+c.co+';border:1px solid '+c.co+'40">'+es(c.tl)+'</span>'+(c.pc?'<span style="margin-left:8px;font-size:11px;color:#555">Ch.'+c.pc+'</span>':'')+'</div><span class="cl" onclick="cls()">&times;</span></div><div class="mb">'+(c.de?'<div class="ms"><p style="font-size:13px;color:#999;line-height:1.5">'+es(c.de)+'</p></div>':'')+ep+dm+sy+fa+mh+ah+eh+'</div>'
DD.getElementById('mc').innerHTML=co;DD.getElementById('mv').classList.add('s');document.body.style.overflow='hidden'}

function cls(){DD.getElementById('mv').classList.remove('s');document.body.style.overflow=''}
function nav(n){cls();DD.getElementById('q').value=n;sq=n;rd()}
DD.getElementById('mc').addEventListener('click',function(e){
  var t=e.target;
  if(t.classList.contains('fn')){nav(t.getAttribute('data-n'));e.stopPropagation()}
  if(t.classList.contains('mtg')){var el=DD.getElementById(t.getAttribute('data-tid'));if(el)el.classList.toggle('s');e.stopPropagation()}
  if(t.classList.contains('awi')){t.classList.toggle('f');e.stopPropagation()}
});
document.addEventListener('keydown',function(e){if(e.key==='Escape')cls()});

if(D.length>0)rd();else DD.getElementById('st').textContent='\u6570\u636e\u52a0\u8f7d\u5931\u8d25';
(function(){var p=new URLSearchParams(window.location.search).get('name');if(p){DD.getElementById('q').value=p;sq=p;rd();var arr=fl();for(var i=0;i<arr.length;i++){if(arr[i].n===p){om(i);break}}}})();
</script>
</body>
</html>'''

    OUTPUT_FILE.write_text(html_pre, encoding="utf-8")
    size_kb = OUTPUT_FILE.stat().st_size // 1024
    data_size_kb = DATA_OUTPUT_FILE.stat().st_size // 1024
    old_json = DATA_DIR / "char_index_data.json"
    if old_json.exists():
        old_json.unlink()
    print(f"[OK] HTML: {OUTPUT_FILE.resolve()} ({size_kb} KB)")
    print(f"[OK] Data: {DATA_OUTPUT_FILE.resolve()} ({data_size_kb} KB)")


if __name__ == "__main__":
    main()
