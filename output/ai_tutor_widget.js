(function () {
  'use strict';

  var INDEX_URL = '../data/ai_tutor_index.json';
  var NAME_MAP_URL = '../data/name_map.json';
 var API_BASE = 'https://mythos-ai-o8kd.onrender.com';

  var STOP_WORDS = {
    "what":1,"is":1,"the":1,"of":1,"a":1,"an":1,"in":1,"on":1,"at":1,"to":1,"for":1,
    "with":1,"by":1,"about":1,"does":1,"do":1,"can":1,"tell":1,"me":1,"give":1,"name":1,
    "list":1,"find":1,"show":1,"are":1,"was":1,"were":1,"be":1,"been":1,"being":1,
    "have":1,"has":1,"had":1,"not":1,"no":1,"nor":1,"but":1,"or":1,"and":1,"if":1,
    "so":1,"as":1,"all":1,"any":1,"each":1,"every":1,"some":1,"many":1,"much":1,
    "more":1,"most":1,"other":1,"own":1,"same":1,"too":1,"very":1,"just":1,"also":1,
    "well":1,"even":1,"still":1,"already":1,"now":1,"then":1,"here":1,"there":1,
    "only":1,"really":1,"quite":1,"who":1,"whom":1,"whose":1,"which":1,"that":1,
    "this":1,"these":1,"those":1,"it":1,"its":1,"you":1,"your":1,"they":1,"them":1,
    "their":1,"he":1,"him":1,"his":1,"she":1,"her":1,"we":1,"us":1,"our":1,"my":1
  };

  var TERM_DICT = {
    "称号":"epithet","别名":"epithet","别称":"epithet","头衔":"epithet",
    "管辖":"domain","掌管":"domain","主管":"domain","司掌":"domain","领域":"domain",
    "象征":"symbol","符号":"symbol","标志":"symbol",
    "神话":"myth","故事":"myth","传说":"myth",
    "关系":"relationship","关联":"relationship",
    "父母":"parent","父亲":"father","母亲":"mother","儿子":"son","女儿":"daughter",
    "配偶":"spouse","丈夫":"husband","妻子":"wife",
    "兄弟":"brother","姐妹":"sister",
    "地点":"place","地方":"place",
    "艺术品":"artwork","作品":"artwork",
    "概念":"concept","定义":"definition",
    "罗马名":"roman","罗马":"roman","希腊名":"name"
  };

  var SYNONYM_MAP = {
    "priest":["priest","patron","hierophant","minister","priestess"],
    "led":["led","guided","conducted","lead"],
    "guide":["guide","lead","escort"],
    "novices":["novices","initiate","beginner","neophyte"],
    "novice":["novice","initiate","beginner"],
    "initiate":["initiate","novice","beginner"],
    "rites":["rites","ritual","ceremony","mysteries","rite"],
    "rite":["rite","ritual","ceremony","mystery"],
    "ritual":["ritual","ceremony","rite","mystery"],
    "king":["king","ruler","monarch","lord"],
    "queen":["queen","wife","lady","ruler"],
    "father":["father","parent","sire"],
    "mother":["mother","parent"],
    "son":["son","child","boy"],
    "daughter":["daughter","child","girl"],
    "killed":["killed","slain","murdered","died","slew","slay"],
    "fought":["fought","battled","warred","combat"],
    "battle":["battle","war","combat","fight"],
    "city":["city","state","capital","kingdom","town"],
    "destroyed":["destroyed","ruined","sacked","fell"],
    "loved":["loved","beloved","desired"],
    "story":["story","myth","tale","legend"],
    "god":["god","goddess","deity","divine"],
    "goddess":["goddess","god","deity","divine"],
    "oracle":["oracle","prophecy","prophet","seer"],
    "capital":["capital","city","seat"],
    "war":["war","battle","conflict","combat"],
    "symbol":["symbol","emblem","sign","attribute"],
    "domain":["domain","realm","sphere","province"]
  };

  var nameMapData = null;

  function hasChinese(text) {
    return /[\u4e00-\u9fff]/.test(text);
  }

  function expandChineseQuery(query) {
    if (!hasChinese(query)) return query;
    var terms = [];
    var chineseSegs = query.match(/[\u4e00-\u9fff]+/g) || [];
    for (var ci = 0; ci < chineseSegs.length; ci++) {
      var seg = chineseSegs[ci];
      if (TERM_DICT[seg]) terms.push(TERM_DICT[seg]);
    }
    if (nameMapData) {
      for (var ci = 0; ci < chineseSegs.length; ci++) {
        var seg = chineseSegs[ci];
        for (var eng in nameMapData) {
          var list = nameMapData[eng];
          for (var li = 0; li < list.length; li++) {
            if (list[li].indexOf(seg) !== -1) {
              terms.push(eng);
              var engParts = eng.toLowerCase().split(/\s+/);
              for (var ei = 0; ei < engParts.length; ei++) {
                if (engParts[ei].length >= 2) terms.push(engParts[ei]);
              }
              break;
            }
          }
        }
      }
    }
    var engParts = query.match(/[a-zA-Z]+/g) || [];
    for (var ei = 0; ei < engParts.length; ei++) {
      if (engParts[ei].length >= 2) terms.push(engParts[ei].toLowerCase());
    }
    if (terms.length) return query + ' ' + terms.join(' ');
    return query;
  }

  function loadNameMap() {
    if (nameMapData) return Promise.resolve(nameMapData);
    return fetch(NAME_MAP_URL).then(function (r) {
      if (!r.ok) throw new Error('Failed to load name_map');
      return r.json();
    }).then(function (data) {
      nameMapData = data;
      return data;
    }).catch(function () {
      nameMapData = {};
      return {};
    });
  }
  var STORAGE_KEY = 'mythos_ai_tutor_messages';
  var THEME_KEY = 'mythos_ai_theme';
  var MAX_HISTORY = 50;

  var tutorIndex = null;
  var messages = [];
  var isOpen = false;
  var isLoading = false;

  var STYLES_ID = 'mythos-tutor-styles';

  var CSS = `
:root {
  --mtw-bg-body:#0a0a1a; --mtw-bg-surface:#111128; --mtw-bg-alt:#0e0e2a;
  --mtw-bg-elevated:#1a1a3e; --mtw-bg-highlight:#1a1a5e;
  --mtw-bg-card-header:rgba(255,255,255,0.02); --mtw-bg-card-footer:rgba(0,0,0,0.15);
  --mtw-border:#2a2a4a; --mtw-border-alt:#1a1a3e; --mtw-border-input:#333;
  --mtw-text:#eee; --mtw-text-secondary:#ddd; --mtw-text-tertiary:#bbb;
  --mtw-text-muted:#999; --mtw-text-dim:#888; --mtw-text-faint:#777;
  --mtw-text-dark:#666; --mtw-text-darker:#555; --mtw-text-darkest:#444;
  --mtw-accent:#F5D742; --mtw-accent-dim:rgba(245,215,66,0.1);
  --mtw-scrollbar-track:#111128; --mtw-scrollbar-thumb:#333;
  --mtw-correct:#2ecc71; --mtw-wrong:#e74c3c;
}
[data-theme="light"] {
  --mtw-bg-body:#f5f0eb; --mtw-bg-surface:#ffffff; --mtw-bg-alt:#fafafa;
  --mtw-bg-elevated:#f0ece6; --mtw-bg-highlight:#e8e4de;
  --mtw-bg-card-header:rgba(0,0,0,0.02); --mtw-bg-card-footer:rgba(0,0,0,0.04);
  --mtw-border:#d4cfc8; --mtw-border-alt:#e0dbd4; --mtw-border-input:#ccc;
  --mtw-text:#2c2c2c; --mtw-text-secondary:#333; --mtw-text-tertiary:#555;
  --mtw-text-muted:#666; --mtw-text-dim:#777; --mtw-text-faint:#888;
  --mtw-text-dark:#999; --mtw-text-darker:#aaa; --mtw-text-darkest:#bbb;
  --mtw-accent:#b8860b; --mtw-accent-dim:rgba(184,134,11,0.1);
  --mtw-scrollbar-track:#f0ece6; --mtw-scrollbar-thumb:#ccc;
  --mtw-correct:#27ae60; --mtw-wrong:#c0392b;
}
body{background:var(--mtw-bg-body);color:var(--mtw-text)}
h1{color:var(--mtw-accent)!important}
::-webkit-scrollbar-track{background:var(--mtw-scrollbar-track)!important}
::-webkit-scrollbar-thumb{background:var(--mtw-scrollbar-thumb)!important}
[data-theme="light"] .card,[data-theme="light"] .stat-item,[data-theme="light"] .tool-section,[data-theme="light"] .book-info,
[data-theme="light"] .q,[data-theme="light"] .help-section,[data-theme="light"] .current-clue,[data-theme="light"] .q-card,
[data-theme="light"] #sidebar,[data-theme="light"] #bar,[data-theme="light"] .top-bar,[data-theme="light"] .reader-sidebar,
[data-theme="light"] .reader-toolbar,[data-theme="light"] .reader-main .pdf-info,
[data-theme="light"] .cd,[data-theme="light"] .aw,[data-theme="light"] .my,[data-theme="light"] .fm .fi span,
[data-theme="light"] .controls button,[data-theme="light"] .mode-bar select,[data-theme="light"] .mode-bar .mode-btn,
[data-theme="light"] .ctrls button,[data-theme="light"] .stat{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .card-icon{background:var(--mtw-bg-elevated)!important}
[data-theme="light"] .card-header{background:var(--mtw-bg-card-header)!important;border-color:var(--mtw-border-alt)!important}
[data-theme="light"] .card-footer,[data-theme="light"] .book-info{background:var(--mtw-bg-card-footer)!important;border-color:var(--mtw-border-alt)!important}
[data-theme="light"] .card-body p,[data-theme="light"] .clue{color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .card-title,[data-theme="light"] .nm,[data-theme="light"] .an{color:var(--mtw-text)!important}
[data-theme="light"] .card-sub,[data-theme="light"] .qh,[data-theme="light"] .cat-hd,[data-theme="light"] .st,
[data-theme="light"] .subtitle,[data-theme="light"] .feat,[data-theme="light"] .tagline,
[data-theme="light"] .help-toggle,[data-theme="light"] .score-bar,
[data-theme="light"] .num,[data-theme="light"] header .subtitle,[data-theme="light"] .stat .l,
[data-theme="light"] #bar .tp{color:var(--mtw-text-dim)!important}
[data-theme="light"] .stat-n{color:var(--mtw-accent)!important}
[data-theme="light"] .feat{background:var(--mtw-bg-alt)!important;border-color:var(--mtw-border-alt)!important;color:var(--mtw-text-dark)!important}
[data-theme="light"] .tool-section h2,[data-theme="light"] #sidebar h1,
[data-theme="light"] #bar .nm,[data-theme="light"] .current-clue .clue-num{color:var(--mtw-accent)!important}
[data-theme="light"] .tool-section p,[data-theme="light"] .book-info{color:var(--mtw-text-dark)!important}
[data-theme="light"] .tool-section button,[data-theme="light"] .controls button.primary,
[data-theme="light"] .reader-toolbar .open-btn{border-color:var(--mtw-accent)!important;color:var(--mtw-accent)!important}
[data-theme="light"] .tool-section button:hover,[data-theme="light"] .controls button:hover,
[data-theme="light"] .reader-toolbar .open-btn:hover{background:var(--mtw-accent)!important;color:var(--mtw-bg-surface)!important}
[data-theme="light"] .tool-section .log,[data-theme="light"] .tab-bar,
[data-theme="light"] .q-img-wrap,[data-theme="light"] #tab-bar,
[data-theme="light"] .q-reveal .q-desc,[data-theme="light"] .aw .awr,
[data-theme="light"] .summary-wrap .ctrl select,[data-theme="light"] .quiz-wrap select,
[data-theme="light"] .reader-sidebar .rch.active{background:var(--mtw-bg-alt)!important}
[data-theme="light"] .tool-section .log{color:var(--mtw-text-dark)!important;border-color:var(--mtw-border-alt)!important}
[data-theme="light"] .tab-bar,[data-theme="light"] #tab-bar{border-color:var(--mtw-border)!important}
[data-theme="light"] .tab-btn,[data-theme="light"] .tab{color:var(--mtw-text-dark)!important}
[data-theme="light"] .tab-btn:hover,[data-theme="light"] .tab-btn.active,
[data-theme="light"] .tab:hover,[data-theme="light"] .tab.tab-act{color:var(--mtw-accent)!important}
[data-theme="light"] .reader-toolbar,[data-theme="light"] .reader-main .pdf-info,
[data-theme="light"] #bar,[data-theme="light"] #legend{border-color:var(--mtw-border)!important}
[data-theme="light"] #search input,[data-theme="light"] .bar input,
[data-theme="light"] .btn,[data-theme="light"] .mi,[data-theme="light"] .tfs button,
[data-theme="light"] .sai,[data-theme="light"] .mode-bar select,
[data-theme="light"] .vis-tooltip{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-border-input)!important;color:var(--mtw-text)!important}
[data-theme="light"] #search input:focus,[data-theme="light"] .bar input:focus,
[data-theme="light"] .sai:focus,[data-theme="light"] .mode-bar select:focus{border-color:var(--mtw-accent)!important}
[data-theme="light"] #search .hint,[data-theme="light"] .cat-hd .n,
[data-theme="light"] #bar .sc{color:var(--mtw-text-darker)!important}
[data-theme="light"] .cat-hd:hover{color:var(--mtw-accent)!important;background:var(--mtw-accent-dim)!important}
[data-theme="light"] .btn{color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .btn:hover,[data-theme="light"] .btn.act,
[data-theme="light"] .controls button.primary,
[data-theme="light"] .mode-bar .mode-btn.active{background:var(--mtw-accent)!important;color:var(--mtw-bg-surface)!important}
[data-theme="light"] .btn.act{font-weight:bold!important}
[data-theme="light"] #legend,[data-theme="light"] .sb,[data-theme="light"] .summary-wrap .sec h3,
[data-theme="light"] .reader-sidebar .rch.active{color:var(--mtw-text-muted)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .sb{color:var(--mtw-text-dim)!important}
[data-theme="light"] .qt,[data-theme="light"] .q-text{color:var(--mtw-text)!important}
[data-theme="light"] .opts label{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-border)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .opts label:hover{border-color:var(--mtw-text-dark)!important}
[data-theme="light"] .opts label.ok,[data-theme="light"] .tfs button.ok{border-color:var(--mtw-correct)!important;background:rgba(39,174,96,0.1)!important}
[data-theme="light"] .opts label.no,[data-theme="light"] .tfs button.no{border-color:var(--mtw-wrong)!important;background:rgba(192,57,43,0.1)!important}
[data-theme="light"] .exp,[data-theme="light"] .q-reveal{background:var(--mtw-accent-dim)!important;border-color:rgba(184,134,11,0.2)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .exp .rf,[data-theme="light"] .q-reveal .ref{color:var(--mtw-text-darker)!important}
[data-theme="light"] .mi:hover{border-color:var(--mtw-accent)!important}
[data-theme="light"] .mi.sel{border-color:var(--mtw-accent)!important;background:var(--mtw-accent-dim)!important}
[data-theme="light"] .clue.done{color:var(--mtw-text-darker)!important}
[data-theme="light"] .clue .cn,[data-theme="light"] .q-artwork,[data-theme="light"] .summary-wrap .ch-title,
[data-theme="light"] .summary-wrap .sec h3,[data-theme="light"] .summary-wrap .myth-item .mn,
[data-theme="light"] .summary-wrap .concept-item .cn,[data-theme="light"] .summary-wrap .art-item .an,
[data-theme="light"] .ms h3,[data-theme="light"] .mer,[data-theme="light"] .bk,
[data-theme="light"] .current-clue .dir-badge.across,
[data-theme="light"] .current-clue .dir-badge.down{color:var(--mtw-accent)!important}
[data-theme="light"] .summary-wrap .char-chip{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .summary-wrap .char-chip .cn{color:var(--mtw-text)!important}
[data-theme="light"] .summary-wrap .char-chip .cr{color:var(--mtw-text-dark)!important}
[data-theme="light"] .summary-wrap .myth-item,[data-theme="light"] .summary-wrap .concept-item,
[data-theme="light"] .summary-wrap .art-item,[data-theme="light"] .summary-wrap .place-item,
[data-theme="light"] .aw{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .summary-wrap .myth-item .ms,[data-theme="light"] .summary-wrap .art-item,
[data-theme="light"] .aw .ad{color:var(--mtw-text-dim)!important}
[data-theme="light"] .summary-wrap .concept-item .cd{color:var(--mtw-text-muted)!important}
[data-theme="light"] .summary-wrap .place-item{color:var(--mtw-text-muted)!important}
[data-theme="light"] .cd:hover{border-color:var(--mtw-accent)!important}
[data-theme="light"] .cd .rm{color:var(--mtw-text-dark)!important}
[data-theme="light"] .cd .ds{color:var(--mtw-text-faint)!important}
[data-theme="light"] .cd .tg{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-border-alt)!important;color:var(--mtw-text-dim)!important}
[data-theme="light"] .mv{background:rgba(0,0,0,0.5)!important}
[data-theme="light"] .mo{background:var(--mtw-bg-alt)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .mh{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border-alt)!important}
[data-theme="light"] .mh h2,[data-theme="light"] .ftl{color:var(--mtw-accent)!important}
[data-theme="light"] .mh .s1,[data-theme="light"] .mh .s2{color:var(--mtw-text-dim)!important}
[data-theme="light"] .ms .ts span,[data-theme="light"] .fm .fi span{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-border-alt)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .fm b{color:var(--mtw-text-dark)!important}
[data-theme="light"] .ms h3,[data-theme="light"] .summary-wrap .sec h3{border-color:var(--mtw-border-alt)!important}
[data-theme="light"] .rf,[data-theme="light"] .q-explanation{color:var(--mtw-text-darker)!important}
[data-theme="light"] .nf,[data-theme="light"] .empty-set,[data-theme="light"] #plh{color:var(--mtw-text-darkest)!important}
[data-theme="light"] .fb button{border-color:var(--mtw-border)!important;color:var(--mtw-text-dim)!important}
[data-theme="light"] .fb button:hover{border-color:var(--mtw-accent)!important}
[data-theme="light"] .fb button.on{background:var(--mtw-accent)!important;color:var(--mtw-bg-surface)!important}
[data-theme="light"] .fb button span{color:var(--mtw-text-dark)!important}
[data-theme="light"] .fb button.on span{color:var(--mtw-bg-surface)!important}
[data-theme="light"] .help-body,[data-theme="light"] .explanation{background:var(--mtw-bg-alt)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .help-body{color:var(--mtw-text-muted)!important}
[data-theme="light"] .help-body kbd{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-border-input)!important;color:var(--mtw-text)!important}
[data-theme="light"] .help-body .col h4{color:var(--mtw-accent)!important}
[data-theme="light"] td.cell,[data-theme="light"] .mi,[data-theme="light"] .fm .fi span,
[data-theme="light"] .opts label,[data-theme="light"] .explanation{border-color:var(--mtw-border)!important}
[data-theme="light"] td.cell{background:var(--mtw-bg-surface)!important}
[data-theme="light"] td.cell.focused{background:var(--mtw-bg-highlight)!important;border-color:var(--mtw-accent)!important}
[data-theme="light"] td.cell.filled{background:var(--mtw-bg-elevated)!important}
[data-theme="light"] td.cell.correct{background:rgba(39,174,96,0.15)!important;border-color:var(--mtw-correct)!important}
[data-theme="light"] td.cell.wrong{background:rgba(192,57,43,0.15)!important;border-color:var(--mtw-wrong)!important}
[data-theme="light"] td.b{background:var(--mtw-bg-body)!important}
[data-theme="light"] .l,[data-theme="light"] .current-clue .clue-text{color:var(--mtw-text)!important}
[data-theme="light"] td.correct .l{color:var(--mtw-correct)!important}
[data-theme="light"] td.wrong .l{color:var(--mtw-wrong)!important}
[data-theme="light"] .current-clue,[data-theme="light"] .mode-bar select,
[data-theme="light"] .mode-bar .mode-btn{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .mode-bar .mode-btn:hover{border-color:var(--mtw-accent)!important;color:var(--mtw-accent)!important}
[data-theme="light"] .current-clue .clue-ref{color:var(--mtw-text-dark)!important}
[data-theme="light"] .puzzle-counter,[data-theme="light"] .status,[data-theme="light"] .mode-bar select{color:var(--mtw-text-dim)!important}
[data-theme="light"] .q-desc,[data-theme="light"] .q-visual-desc,[data-theme="light"] .q-story{color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .q-desc{background:var(--mtw-bg-alt)!important;border-color:var(--mtw-accent)!important}
[data-theme="light"] .q-img-wrap{background:var(--mtw-bg-alt)!important}
[data-theme="light"] .q-feedback.correct{background:rgba(39,174,96,0.1)!important;color:var(--mtw-correct)!important}
[data-theme="light"] .q-feedback.wrong{background:rgba(192,57,43,0.1)!important;color:var(--mtw-wrong)!important}
[data-theme="light"] .filter-bar button{border-color:var(--mtw-border)!important;color:var(--mtw-text-dark)!important}
[data-theme="light"] .filter-bar button:hover,[data-theme="light"] .filter-bar button.act{color:var(--mtw-accent)!important;border-color:var(--mtw-accent)!important}
[data-theme="light"] .score-bar{background:var(--mtw-bg-body)!important;border-color:var(--mtw-border)!important;color:var(--mtw-text-dim)!important}
[data-theme="light"] .q-card{background:var(--mtw-bg-surface)!important;border-color:var(--mtw-border)!important}
[data-theme="light"] .q-label{color:var(--mtw-text-dark)!important}
[data-theme="light"] .vis-tooltip{background:var(--mtw-bg-elevated)!important;border-color:var(--mtw-accent)!important;color:var(--mtw-text)!important}
[data-theme="light"] .q-reveal .q-visual-desc{background:var(--mtw-accent-dim)!important;border-color:rgba(184,134,11,0.2)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .q-story{background:rgba(39,174,96,0.05)!important;border-color:rgba(39,174,96,0.15)!important;color:var(--mtw-text-tertiary)!important}
[data-theme="light"] .top-bar,[data-theme="light"] .reader-sidebar,
[data-theme="light"] .reader-toolbar,[data-theme="light"] .reader-main .pdf-info{background:var(--mtw-bg-surface)!important}
[data-theme="light"] .top-bar .sub{color:var(--mtw-text-dark)!important}
[data-theme="light"] .reader-sidebar .rch{color:var(--mtw-text-muted)!important}
[data-theme="light"] .reader-sidebar .rch:hover{color:var(--mtw-text)!important}
[data-theme="light"] .reader-sidebar .rch.active{color:var(--mtw-accent)!important;border-color:var(--mtw-accent)!important}
[data-theme="light"] .reader-sidebar .rch .rpg{color:var(--mtw-text-dark)!important}
[data-theme="light"] .reader-main .pdf-wrap,[data-theme="light"] .pdf-placeholder{background:var(--mtw-bg-body)!important}
[data-theme="light"] .pdf-placeholder .hint,[data-theme="light"] .pdf-placeholder{color:var(--mtw-text-darkest)!important}

/* AI Tutor widget theme vars */
#mtw-btn{position:fixed;bottom:24px;right:24px;padding:10px 18px;border-radius:26px;background:#F5D742;border:none;cursor:pointer;z-index:99999;box-shadow:0 4px 16px rgba(245,215,66,0.3);display:flex;align-items:center;gap:8px;font-size:13px;font-weight:bold;transition:transform 0.2s,box-shadow 0.2s;color:#111;font-family:'Segoe UI',sans-serif;letter-spacing:0.5px}
#mtw-btn:hover{transform:scale(1.05);box-shadow:0 6px 24px rgba(245,215,66,0.45)}
#mtw-btn .mtw-btn-icon{font-size:20px}
[data-theme="light"] #mtw-btn{background:#b8860b;color:#fff;box-shadow:0 4px 16px rgba(184,134,11,0.3)}
[data-theme="light"] #mtw-btn:hover{box-shadow:0 6px 24px rgba(184,134,11,0.45)}
#mtw-panel{position:fixed;bottom:90px;right:24px;width:400px;max-height:640px;height:calc(100vh - 160px);background:var(--mtw-bg-alt);border:1px solid var(--mtw-border);border-radius:16px;z-index:99998;display:none;flex-direction:column;box-shadow:0 16px 48px rgba(0,0,0,0.6);overflow:hidden;font-family:'Segoe UI',sans-serif;color:var(--mtw-text);font-size:14px}
#mtw-panel.open{display:flex}
#mtw-panel .mtw-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;background:var(--mtw-bg-surface);border-bottom:1px solid var(--mtw-border);flex-shrink:0}
#mtw-panel .mtw-hdr .mtw-title{font-weight:bold;color:var(--mtw-accent);font-size:15px;letter-spacing:0.5px}
#mtw-panel .mtw-hdr .mtw-title small{color:var(--mtw-text-dark);font-weight:normal;font-size:10px;margin-left:6px}
#mtw-panel .mtw-hdr .mtw-btn-hdr{background:none;border:none;color:var(--mtw-text-darker);font-size:18px;cursor:pointer;padding:2px 6px;border-radius:4px;line-height:1;transition:color 0.15s,background 0.15s}
#mtw-panel .mtw-hdr .mtw-btn-hdr:hover{color:var(--mtw-accent);background:var(--mtw-accent-dim)}
#mtw-panel .mtw-hdr .mtw-spacer{flex:1}
#mtw-panel .mtw-body{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}
#mtw-panel .mtw-body::-webkit-scrollbar{width:4px}
#mtw-panel .mtw-body::-webkit-scrollbar-track{background:transparent}
#mtw-panel .mtw-body::-webkit-scrollbar-thumb{background:var(--mtw-scrollbar-thumb);border-radius:2px}
#mtw-panel .mtw-msg{max-width:88%;padding:10px 14px;border-radius:12px;line-height:1.6;font-size:13px;animation:mtwFadeIn 0.2s}
#mtw-panel .mtw-msg.mtw-user{background:var(--mtw-bg-elevated);color:var(--mtw-text);align-self:flex-end;border-bottom-right-radius:4px}
#mtw-panel .mtw-msg.mtw-bot{background:var(--mtw-bg-surface);color:var(--mtw-text-secondary);align-self:flex-start;border-bottom-left-radius:4px;border:1px solid var(--mtw-border)}
#mtw-panel .mtw-msg.mtw-bot .mtw-ref{display:block;margin-top:8px;padding-top:6px;border-top:1px solid var(--mtw-border);font-size:11px;color:var(--mtw-text-dark)}
#mtw-panel .mtw-msg.mtw-bot .mtw-ref strong{color:var(--mtw-accent);font-weight:normal}
#mtw-panel .mtw-msg.mtw-bot .mtw-label{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10px;margin-right:6px;background:var(--mtw-accent-dim);color:var(--mtw-accent)}
#mtw-panel .mtw-msg.mtw-bot .mtw-label.ml-c{background:rgba(100,180,255,0.12);color:#64b4ff}
#mtw-panel .mtw-msg.mtw-bot .mtw-label.ml-m{background:var(--mtw-accent-dim);color:var(--mtw-accent)}
#mtw-panel .mtw-msg.mtw-bot .mtw-label.ml-p{background:rgba(80,220,140,0.12);color:#50dc8c}
#mtw-panel .mtw-msg.mtw-bot .mtw-label.ml-a{background:rgba(255,150,100,0.12);color:#ff9664}
#mtw-panel .mtw-msg.mtw-bot .mtw-label.ml-x{background:rgba(200,130,255,0.12);color:#c882ff}
#mtw-panel .mtw-foot{display:flex;align-items:center;gap:8px;padding:10px 14px;background:var(--mtw-bg-surface);border-top:1px solid var(--mtw-border);flex-shrink:0}
#mtw-panel .mtw-foot input{flex:1;padding:9px 14px;border:1px solid var(--mtw-border);border-radius:8px;background:var(--mtw-bg-body);color:var(--mtw-text);font-size:13px;outline:none}
#mtw-panel .mtw-foot input:focus{border-color:var(--mtw-accent)}
#mtw-panel .mtw-foot input::placeholder{color:var(--mtw-text-darker)}
#mtw-panel .mtw-foot .mtw-send{padding:8px 16px;border:1px solid var(--mtw-accent);border-radius:8px;background:transparent;color:var(--mtw-accent);cursor:pointer;font-size:13px;white-space:nowrap;transition:all 0.15s}
#mtw-panel .mtw-foot .mtw-send:hover{background:var(--mtw-accent);color:var(--mtw-bg-surface)}
#mtw-panel .mtw-foot .mtw-send:disabled{opacity:0.4;cursor:not-allowed}
#mtw-panel .mtw-loading{text-align:center;color:var(--mtw-text-darker);padding:16px;font-size:12px;align-self:center}
#mtw-panel .mtw-loading::after{content:'';display:inline-block;width:12px;height:12px;border:2px solid var(--mtw-border-input);border-top-color:var(--mtw-accent);border-radius:50%;animation:mtwSpin 0.6s linear infinite;margin-left:6px;vertical-align:middle}
#mtw-panel .mtw-welcome{text-align:center;padding:20px 10px;color:var(--mtw-text-darker)}
#mtw-panel .mtw-welcome .mtw-icon{font-size:36px;margin-bottom:8px}
#mtw-panel .mtw-welcome p{font-size:13px;line-height:1.6;margin-top:6px}
#mtw-panel .mtw-welcome .mtw-hint{font-size:11px;color:var(--mtw-text-darkest);margin-top:10px}
#mtw-panel .mtw-typing{display:flex;gap:4px;padding:10px 14px;align-self:flex-start;align-items:center}
#mtw-panel .mtw-typing span{width:6px;height:6px;border-radius:50%;background:var(--mtw-text-darker);animation:mtwBounce 1.2s infinite}
#mtw-panel .mtw-typing span:nth-child(2){animation-delay:0.2s}
#mtw-panel .mtw-typing span:nth-child(3){animation-delay:0.4s}
@keyframes mtwFadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes mtwSpin{to{transform:rotate(360deg)}}
@keyframes mtwBounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
`;

  function injectStyles() {
    if (document.getElementById(STYLES_ID)) return;
    var style = document.createElement('style');
    style.id = STYLES_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function initTheme() {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }
  initTheme();

  function loadIndex() {
    if (tutorIndex) return Promise.resolve(tutorIndex);
    return fetch(INDEX_URL).then(function (r) {
      if (!r.ok) throw new Error('Failed to load index');
      return r.json();
    }).then(function (data) {
      tutorIndex = data;
      return data;
    });
  }

  function loadMessages() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) messages = JSON.parse(saved);
    } catch (e) { messages = []; }
    if (!messages.length) {
      messages.push({
        role: 'bot',
        text: '你好！我是 Mythos AI 助教，基于《Classical Mythology》教材知识库。\\n\\n你可以问我任何关于希腊罗马神话的问题，我会根据教材内容回答，并注明出处。\\n\\n例如：\\n• 谁是宙斯？\\n• 特洛伊战争的起因是什么？\\n• 珀耳塞福涅神话有哪些关键人物？'
      });
    }
  }

  function saveMessages() {
    try {
      var toSave = messages.slice(-MAX_HISTORY);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) { /* ignore */ }
  }

  function clearMessages() {
    messages = [];
    saveMessages();
    renderMessages();
  }

  function cleanTerm(w) {
    return w.replace(/[^\w\s]/g, '');
  }

  function getRelevance(text, query, terms, synonymMap) {
    var q = query.toLowerCase();
    var t = (text || '').toLowerCase();
    if (!t) return 0;
    var allTerms = terms;
    if (!allTerms) {
      allTerms = q.split(/\s+/).map(cleanTerm).filter(function (w) { return w.length >= 2 && !STOP_WORDS[w]; });
    } else {
      allTerms = terms.map(cleanTerm).filter(function (w) { return w && !STOP_WORDS[w]; });
    }
    if (!allTerms.length) return 0;
    var matches = 0;
    for (var i = 0; i < allTerms.length; i++) {
      var term = allTerms[i];
      if (t.indexOf(term) !== -1) {
        matches++;
      } else if (synonymMap && synonymMap[term]) {
        var syns = synonymMap[term];
        for (var si = 0; si < syns.length; si++) {
          if (t.indexOf(syns[si]) !== -1) { matches++; break; }
        }
      }
    }
    return matches / allTerms.length;
  }

  function scoreWithBoost(name, extras, terms) {
    var base = getRelevance(name, '', terms, SYNONYM_MAP);
    var nameLower = name.toLowerCase();
    for (var ti = 0; ti < terms.length; ti++) {
      if (terms[ti] === nameLower) { base = 1.0; break; }
      if (nameLower.indexOf(terms[ti]) !== -1) {
        base = Math.max(base, terms[ti].length / nameLower.length);
      }
    }
    for (var ei = 0; ei < extras.length; ei++) {
      base = Math.max(base, getRelevance(extras[ei], '', terms, SYNONYM_MAP));
    }
    return base;
  }

  function search(query) {
    if (!tutorIndex) return { chars: [], myths: [], concepts: [], places: [], artworks: [] };

    var expanded = expandChineseQuery(query);
    var q = expanded.trim().toLowerCase();
    var allTerms = q.split(/\s+/).map(cleanTerm).filter(function (w) { return w.length >= 2; });
    var sigTerms = allTerms.filter(function (w) { return !STOP_WORDS[w]; });
    var effectiveTerms = sigTerms.length ? sigTerms : allTerms;

    var result = { chars: [], myths: [], concepts: [], places: [], artworks: [] };

    var i, item;

    for (i = 0; i < tutorIndex.characters.length; i++) {
      item = tutorIndex.characters[i];
      var extras = [].concat(item.e || [], item.d || [], item.sy || [],
                              item.myths || [], item.desc ? [item.desc] : [],
                              item.r ? [item.r] : []);
      var s = scoreWithBoost(item.n, extras, effectiveTerms);
      if (s >= 0.3) result.chars.push({ item: item, score: s });
    }

    for (i = 0; i < tutorIndex.myths.length; i++) {
      item = tutorIndex.myths[i];
      var extras = [item.s || ''].concat(item.kc || []);
      var s = scoreWithBoost(item.n, extras, effectiveTerms);
      if (s >= 0.3) result.myths.push({ item: item, score: s });
    }

    for (i = 0; i < tutorIndex.concepts.length; i++) {
      item = tutorIndex.concepts[i];
      var extras = [item.def || ''];
      var s = scoreWithBoost(item.n, extras, effectiveTerms);
      if (s >= 0.3) result.concepts.push({ item: item, score: s });
    }

    for (i = 0; i < tutorIndex.places.length; i++) {
      item = tutorIndex.places[i];
      var extras = [item.desc || ''];
      var s = scoreWithBoost(item.n, extras, effectiveTerms);
      if (s >= 0.3) result.places.push({ item: item, score: s });
    }

    for (i = 0; i < tutorIndex.artworks.length; i++) {
      item = tutorIndex.artworks[i];
      var extras = [item.desc || ''];
      var s = scoreWithBoost(item.n, extras, effectiveTerms);
      if (s >= 0.3) result.artworks.push({ item: item, score: s });
    }

    function sortByScore(arr) { arr.sort(function (a, b) { return b.score - a.score; }); }

    sortByScore(result.chars);
    sortByScore(result.myths);
    sortByScore(result.concepts);
    sortByScore(result.places);
    sortByScore(result.artworks);

    result.chars = result.chars.slice(0, 5);
    result.myths = result.myths.slice(0, 5);
    result.concepts = result.concepts.slice(0, 3);
    result.places = result.places.slice(0, 3);
    result.artworks = result.artworks.slice(0, 3);

    return result;
  }

  function compressPages(pages) {
    if (!pages || !pages.length) return '';
    var sorted = pages.slice().sort(function (a, b) { return a - b; });
    var ranges = [];
    var start = sorted[0], end = sorted[0];
    for (var i = 1; i < sorted.length; i++) {
      if (sorted[i] === end + 1) {
        end = sorted[i];
      } else {
        ranges.push(start === end ? String(start) : start + '-' + end);
        start = sorted[i];
        end = sorted[i];
      }
    }
    ranges.push(start === end ? String(start) : start + '-' + end);
    return ranges.join(', ');
  }

  function formatEvidence(ev) {
    if (!ev || !ev.length) return '';
    var parts = [];
    for (var i = 0; i < ev.length; i++) {
      var e = ev[i];
      var pages = compressPages(e.pp);
      parts.push('Ch.' + e.ch + (pages ? ' (pp. ' + pages + ')' : ''));
    }
    return parts.join('; ');
  }

  function buildAnswer(query, results) {
    var lines = [];
    var hasContent = false;

    var total = (results.chars.length + results.myths.length + results.concepts.length +
                 results.places.length + results.artworks.length);

    if (total === 0) {
      return '抱歉，我没有在教材中找到与 "' + query + '" 直接相关的信息。\n\n你可以尝试：\n• 使用不同的关键词\n• 输入英文名称（如 Zeus, Athena）\n• 或者参考教材目录找到相关章节。';
    }

    if (results.chars.length) {
      hasContent = true;
      lines.push('**人物**');
      for (var i = 0; i < results.chars.length; i++) {
        var c = results.chars[i].item;
        var line = '• **' + c.n + '**';
        if (c.r && c.r !== c.n) line += ' (罗马名: ' + c.r + ')';
        if (c.t) line += ' — ' + c.t;
        if (c.desc) line += '\n  ' + c.desc;
        if (c.myths && c.myths.length) line += '\n  相关神话: ' + c.myths.slice(0, 3).join('、');
        if (c.ev && c.ev.length) line += '\n  📖 ' + formatEvidence(c.ev.slice(0, 2));
        lines.push(line);
      }
      lines.push('');
    }

    if (results.myths.length) {
      hasContent = true;
      lines.push('**神话**');
      for (var i = 0; i < results.myths.length; i++) {
        var m = results.myths[i].item;
        var line = '• **' + m.n + '**';
        if (m.s) line += '\n  ' + (m.s.length > 200 ? m.s.slice(0, 200) + '…' : m.s);
        if (m.kc && m.kc.length) line += '\n  关键人物: ' + m.kc.join('、');
        if (m.ev && m.ev.length) line += '\n  📖 ' + formatEvidence(m.ev.slice(0, 2));
        lines.push(line);
      }
      lines.push('');
    }

    if (results.concepts.length) {
      hasContent = true;
      lines.push('**概念**');
      for (var i = 0; i < results.concepts.length; i++) {
        var x = results.concepts[i].item;
        var line = '• **' + x.n + '**';
        if (x.def) line += ': ' + x.def;
        lines.push(line);
      }
      lines.push('');
    }

    if (results.places.length) {
      hasContent = true;
      lines.push('**地点**');
      for (var i = 0; i < results.places.length; i++) {
        var p = results.places[i].item;
        var line = '• **' + p.n + '**';
        if (p.desc) line += ': ' + p.desc;
        lines.push(line);
      }
      lines.push('');
    }

    if (results.artworks.length) {
      hasContent = true;
      lines.push('**艺术品**');
      for (var i = 0; i < results.artworks.length; i++) {
        var a = results.artworks[i].item;
        var line = '• **' + a.n + '**';
        if (a.desc) line += ': ' + (a.desc.length > 150 ? a.desc.slice(0, 150) + '…' : a.desc);
        lines.push(line);
      }
      lines.push('');
    }

    if (hasContent) {
      lines.push('---');
      lines.push('💡 以上信息来源于 Morford, Lenardon, Sham *Classical Mythology* (Oxford University Press)。建议翻阅教材对应章节获取更详细的内容。');
    }

    return lines.join('\n');
  }

  function renderMessages() {
    var body = document.getElementById('mtw-body');
    if (!body) return;

    var welcome = document.getElementById('mtw-welcome');
    if (welcome) welcome.style.display = 'none';

    body.innerHTML = '';

    for (var i = 0; i < messages.length; i++) {
      var msg = messages[i];
      var div = document.createElement('div');
      div.className = 'mtw-msg ' + (msg.role === 'user' ? 'mtw-user' : 'mtw-bot');
      div.textContent = msg.text;
      body.appendChild(div);
    }

    body.scrollTop = body.scrollHeight;
  }

  function renderAnswer(raw) {
    var body = document.getElementById('mtw-body');
    if (!body) return;

    var div = document.createElement('div');
    div.className = 'mtw-msg mtw-bot';

    var paragraphs = raw.split('\n');
    var html = '';

    for (var i = 0; i < paragraphs.length; i++) {
      var p = paragraphs[i];

      if (p.indexOf('---') === 0) {
        html += '<hr style="border:none;border-top:1px solid var(--mtw-border);margin:6px 0">';
        continue;
      }

      if (p.indexOf('**人物**') === 0 || p.indexOf('**神话**') === 0 || p.indexOf('**概念**') === 0 ||
          p.indexOf('**地点**') === 0 || p.indexOf('**艺术品**') === 0) {
        html += '<div style="margin-top:8px;font-weight:bold;color:var(--mtw-accent);font-size:12px;letter-spacing:1px;text-transform:uppercase">' + p.replace(/\*\*/g, '') + '</div>';
        continue;
      }

      if (p.indexOf('💡') === 0) {
        html += '<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--mtw-border);font-size:11px;color:var(--mtw-text-dim)">' + p + '</div>';
        continue;
      }

      if (p.indexOf('📖') === 0) {
        var refText = p.replace('📖 ', '');
        html += '<span class="mtw-ref"><strong>📖 教材引用:</strong> ' + refText + '</span>';
        continue;
      }

      if (p.indexOf('• ') === 0) {
        html += '<div style="margin:3px 0;padding-left:4px;border-left:2px solid var(--mtw-border);font-size:13px">' + p.replace('• ', '').replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--mtw-accent)">$1</strong>') + '</div>';
        continue;
      }

      if (p.trim() === '') {
        html += '<div style="height:4px"></div>';
        continue;
      }

      html += '<div style="margin:2px 0;font-size:13px">' + p.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--mtw-accent)">$1</strong>') + '</div>';
    }

    div.innerHTML = html;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function addUserMessage(text) {
    messages.push({ role: 'user', text: text });
    saveMessages();
    var body = document.getElementById('mtw-body');
    if (body) {
      var div = document.createElement('div');
      div.className = 'mtw-msg mtw-user';
      div.textContent = text;
      body.appendChild(div);
      body.scrollTop = body.scrollHeight;
    }
  }

  function showTyping() {
    var body = document.getElementById('mtw-body');
    if (!body) return;
    var div = document.createElement('div');
    div.className = 'mtw-typing';
    div.id = 'mtw-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function hideTyping() {
    var el = document.getElementById('mtw-typing');
    if (el) el.remove();
  }

  function getOpenId() {
    var oid = localStorage.getItem('mtw_openid');
    if (!oid) {
      oid = 'user_' + Math.random().toString(36).slice(2, 10);
      localStorage.setItem('mtw_openid', oid);
    }
    return oid;
  }

  function handleQuery(query) {
    if (!query.trim()) return;
    if (isLoading) return;

    addUserMessage(query);
    isLoading = true;
    setInputState(true);

    showTyping();

    // Try backend API first, fallback to local search
    var apiUrl = API_BASE + '/api/ask';

    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: query,
        openId: getOpenId()
      })
    }).then(function (resp) {
      return resp.json();
    }).then(function (data) {
      hideTyping();
      if (data.status === 0 && data.data && data.data.answer) {
        var answer = data.data.answer;
        messages.push({ role: 'bot', text: answer });
        saveMessages();
        renderAnswer(answer);
      } else {
        fallbackSearch(query);
      }
      isLoading = false;
      setInputState(false);
    }).catch(function () {
      hideTyping();
      fallbackSearch(query);
      isLoading = false;
      setInputState(false);
    });
  }

  function fallbackSearch(query) {
    var results = search(query);
    var answer = buildAnswer(query, results);
    messages.push({ role: 'bot', text: answer });
    saveMessages();
    renderAnswer(answer);
  }

  function setInputState(disabled) {
    var input = document.getElementById('mtw-input');
    var send = document.getElementById('mtw-send');
    if (input) input.disabled = disabled;
    if (send) send.disabled = disabled;
  }

  function createWidget() {
    injectStyles();

    // Button
    var btn = document.createElement('button');
    btn.id = 'mtw-btn';
    btn.innerHTML = '<span class="mtw-btn-icon">💬</span> AI ASSISTANT';
    btn.setAttribute('aria-label', '打开 AI Tutor');
    document.body.appendChild(btn);

    // Panel
    var panel = document.createElement('div');
    panel.id = 'mtw-panel';
    panel.innerHTML =
      '<div class="mtw-hdr">' +
        '<div class="mtw-title">🎓 Mythos AI Tutor<small>α</small></div>' +
        '<span class="mtw-spacer"></span>' +
        '<button class="mtw-btn-hdr" id="mtw-theme" title="切换白天/夜间模式">🌙</button>' +
        '<button class="mtw-btn-hdr" id="mtw-clear" title="清空对话">🗑️</button>' +
        '<button class="mtw-btn-hdr" id="mtw-close" title="关闭">✕</button>' +
      '</div>' +
      '<div class="mtw-body" id="mtw-body"></div>' +
      '<div class="mtw-foot">' +
        '<input id="mtw-input" type="text" placeholder="输入你的问题…" autocomplete="off">' +
        '<button class="mtw-send" id="mtw-send">发送</button>' +
      '</div>';
    document.body.appendChild(panel);

    // Welcome overlay
    var body = document.getElementById('mtw-body');
    var welcome = document.createElement('div');
    welcome.id = 'mtw-welcome';
    welcome.className = 'mtw-welcome';
    welcome.innerHTML =
      '<div class="mtw-icon">📚</div>' +
      '<div style="font-weight:bold;color:var(--mtw-accent);font-size:14px">Mythos AI Tutor</div>' +
      '<p>基于 <em>Classical Mythology</em> 教材的知识检索助手</p>' +
      '<div class="mtw-hint">Morford · Lenardon · Sham · Oxford University Press</div>';
    body.appendChild(welcome);

    // Events
    btn.addEventListener('click', function () {
      isOpen = !isOpen;
      panel.classList.toggle('open', isOpen);
      if (isOpen) {
        loadIndex().catch(function () { /* ignore */ });
        body.scrollTop = body.scrollHeight;
        document.getElementById('mtw-input').focus();
      }
    });

    document.getElementById('mtw-close').addEventListener('click', function () {
      isOpen = false;
      panel.classList.remove('open');
    });

    document.getElementById('mtw-theme').addEventListener('click', function () {
      var html = document.documentElement;
      var isLight = html.getAttribute('data-theme') === 'light';
      if (isLight) {
        html.removeAttribute('data-theme');
        localStorage.setItem(THEME_KEY, 'dark');
        document.getElementById('mtw-theme').textContent = '🌙';
      } else {
        html.setAttribute('data-theme', 'light');
        localStorage.setItem(THEME_KEY, 'light');
        document.getElementById('mtw-theme').textContent = '☀️';
      }
    });

    // Sync button icon on panel open
    var themeBtn = document.getElementById('mtw-theme');
    if (document.documentElement.getAttribute('data-theme') === 'light') {
      themeBtn.textContent = '☀️';
    }

    document.getElementById('mtw-clear').addEventListener('click', function () {
      if (confirm('确定清空对话历史？')) {
        clearMessages();
        loadMessages();
        var w = document.getElementById('mtw-welcome');
        if (w) w.style.display = 'block';
        renderMessages();
      }
    });

    var input = document.getElementById('mtw-input');
    var sendBtn = document.getElementById('mtw-send');

    function doSend() {
      var q = input.value.trim();
      if (q) {
        input.value = '';
        handleQuery(q);
      }
    }

    sendBtn.addEventListener('click', doSend);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSend();
    });

    // Load messages
    loadMessages();

    // Preload index and name_map in background
    setTimeout(function () {
      loadIndex().catch(function () { /* ignore */ });
      loadNameMap().catch(function () { /* ignore */ });
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();
