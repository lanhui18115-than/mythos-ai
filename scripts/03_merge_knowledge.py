"""
程序 3/3：合并所有章节的知识图谱

功能：
  1. 读取每章提取的 JSON 文件
  2. 合并同名实体（人物、神话、地点、概念、艺术品）
  3. 合并证据（收录所有出现的章节和页码）
  4. 去重关系
  5. 输出完整的知识图谱 JSON

输出位置：data/knowledge_graph.json
"""

import json
from pathlib import Path
from collections import defaultdict

# ── 配置 ──────────────────────────────────────────────
KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "knowledge_graph.json"

# ── 实体合并 ─────────────────────────────────────────

def normalize_name(name: str) -> str:
    """标准化名称用于去重匹配"""
    if not name:
        return ""
    return name.strip().lower().replace("(", "").replace(")", "")


def merge_entities(entities_list: list[list[dict]]) -> list[dict]:
    """
    合并多个章节中的同类型实体。
    entities_list: 每个元素是某一章提取出的实体列表。
    """
    merged = {}  # key: normalized_name, value: merged entity

    for chapter_entities in entities_list:
        for entity in chapter_entities:
            name = entity.get("name", "")
            key = normalize_name(name)
            if not key:
                continue

            if key in merged:
                existing = merged[key]
                # 合并页码
                existing_pages = set(existing.get("mentioned_pages", []))
                new_pages = set(entity.get("mentioned_pages", []))
                existing["mentioned_pages"] = sorted(existing_pages | new_pages)

                # 合并罗马名
                if not existing.get("roman_name") and entity.get("roman_name"):
                    existing["roman_name"] = entity["roman_name"]

                # 补充描述（优先用已有的）
                if not existing.get("description") and entity.get("description"):
                    existing["description"] = entity["description"]

                # 合并 epithets
                if "epithets" in existing and "epithets" in entity:
                    existing_ep = set(existing["epithets"])
                    existing_ep.update(entity["epithets"])
                    existing["epithets"] = sorted(existing_ep)

                # 合并 domains
                if "domains" in existing and "domains" in entity:
                    existing_dom = set(existing["domains"])
                    existing_dom.update(entity["domains"])
                    existing["domains"] = sorted(existing_dom)

                # 合并 symbols
                if "symbols" in existing and "symbols" in entity:
                    existing_sym = set(existing["symbols"])
                    existing_sym.update(entity["symbols"])
                    existing["symbols"] = sorted(existing_sym)

                # 合并 key_characters（对 myth 类型）
                if "key_characters" in existing and "key_characters" in entity:
                    existing_kc = set(existing["key_characters"])
                    existing_kc.update(entity["key_characters"])
                    existing["key_characters"] = sorted(existing_kc)

                # 合并 major_myths（对 character 类型）
                if "major_myths" in existing and "major_myths" in entity:
                    existing_mm = set(existing["major_myths"])
                    existing_mm.update(entity["major_myths"])
                    existing["major_myths"] = sorted(existing_mm)

            else:
                merged[key] = dict(entity)

    return list(merged.values())


def merge_relationships(all_relationships: list[list[dict]]) -> list[dict]:
    """
    合并多个章节的关系，去重。
    同一个 (source, target, type) 只保留一条，合并页码。
    """
    merged = {}  # key: (source, target, type)

    for chapter_rels in all_relationships:
        for rel in chapter_rels:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            rtype = rel.get("type", "").strip()
            if not source or not target or not rtype:
                continue

            key = (source.lower(), target.lower(), rtype)
            if key in merged:
                existing = merged[key]
                # 合并页码
                existing_page = existing.get("page")
                new_page = rel.get("page")
                if existing_page != new_page:
                    # 如果页码不同，存为列表
                    existing.setdefault("pages", [])
                    if existing_page and existing_page not in existing["pages"]:
                        existing["pages"].append(existing_page)
                    if new_page and new_page not in existing["pages"]:
                        existing["pages"].append(new_page)
                    existing.pop("page", None)
                # 补充描述
                if not existing.get("description") and rel.get("description"):
                    existing["description"] = rel["description"]
                # 保留 chapter（若新值非空）
                if rel.get("chapter") and not existing.get("chapter"):
                    existing["chapter"] = rel["chapter"]
                # 保留 evidence_level（若新值非空）
                if rel.get("evidence_level") and not existing.get("evidence_level"):
                    existing["evidence_level"] = rel["evidence_level"]
            else:
                merged[key] = dict(rel)

    return list(merged.values())


def build_evidence(merged_entity: dict, chapter_num: int) -> dict:
    """
    为实体构建证据条目。
    返回 { chapter, printed_pages } 格式
    """
    pages = merged_entity.get("mentioned_pages", [])
    return {
        "chapter": chapter_num,
        "printed_pages": pages if isinstance(pages, list) else [pages],
    }


# ── 悬空引用修复配置 ──────────────────────────
# 你可以编辑下方字典来控制哪些悬空引用被创建为正式实体
# 格式: "实体名": {"type": "类型", "description": "描述"}

FIXUP_ENTITIES = {
    # ── 群体 / 族群 ──
    "Greeks": {"type": "group", "description": "The Greek people, also called Achaeans or Danaans in Homer."},
    "Trojans": {"type": "group", "description": "The people of Troy, led by King Priam."},
    "Humans": {"type": "race", "description": "The human race in Greek mythology, created from the ashes of the Titans."},
    "Centaurs": {"type": "race", "description": "Half-human, half-horse creatures; offspring of Centaurus and mares."},
    "Cretan Sailors": {"type": "group", "description": "Sailors from Crete who became attendants of Apollo."},
    "Pirates": {"type": "group", "description": "Pirates who attempted to capture Dionysus and were transformed into dolphins."},
    "Ciconian Women": {"type": "group", "description": "Women of Ciconia, followers of Dionysus, who tore Orpheus apart."},
    "Nymphs of Nysa": {"type": "nymph", "description": "Nymphs who nurtured the infant Dionysus on Mount Nysa."},
    "Proetus's Daughters": {"type": "mortal", "description": "Daughters of Proetus driven mad by Dionysus and cured by Melampus."},
    "Minyas's Daughters": {"type": "mortal", "description": "Daughters of Minyas driven mad by Dionysus."},
    "Armed Men (Spartoi)": {"type": "warrior", "description": "Armed men who sprang from the dragon's teeth sown by Cadmus and Jason."},

    # ── 有名字的个人 ──
    "Sychaeus": {"type": "mortal", "description": "Former husband of Dido, killed by her brother Pygmalion."},
    "Armenius": {"type": "mortal", "description": "Father of Er, the Pamphylian who returned from the dead in Plato's myth."},
    "Seth": {"type": "god", "description": "Egyptian god of chaos, who killed and dismembered Osiris."},

    # ── 动物 / 怪物 ──
    "Colchian Dragon": {"type": "monster", "description": "The serpent / dragon that guarded the Golden Fleece in Colchis."},
    "Serpent": {"type": "creature", "description": "A serpent in Greek mythology, often associated with transformation or guardianship."},
    "Dolphin": {"type": "creature", "description": "A dolphin, often associated with Apollo and known for rescuing humans."},
    "Raven": {"type": "creature", "description": "A bird sacred to Apollo; originally white, turned black as punishment."},
    "Swan": {"type": "creature", "description": "A bird associated with transformation in Greek mythology."},
    "Bull": {"type": "creature", "description": "A bull, often associated with Poseidon and appearing in myths of Crete."},
    "Fire-Breathing Bulls": {"type": "monster", "description": "Bronze-hooved bulls that breathed fire, yoked by Jason in Colchis."},
    "Spider": {"type": "creature", "description": "The form into which Arachne was transformed by Athena."},
    "Lion": {"type": "creature", "description": "A lion; in Plato's myth, the soul of Ajax chose the life of a lion."},
    "Eagle": {"type": "creature", "description": "An eagle; in Plato's myth, the soul of Agamemnon became an eagle."},
    "Boar": {"type": "creature", "description": "A wild boar; killed Idmon the seer among the Mariandyni."},
    "Stag": {"type": "creature", "description": "A stag loved by Cyparissus, who accidentally killed it."},
    "Ape": {"type": "creature", "description": "An ape; in Plato's myth, the soul of Thersites became an ape."},

    # ── 物品 / 象征物 ──
    "Flute": {"type": "object", "description": "A double flute (aulos) invented by Athena and later picked up by Marsyas."},
    "Lyre": {"type": "object", "description": "A stringed instrument invented by Hermes from a tortoise shell."},
    "Fire Sticks": {"type": "object", "description": "Fire sticks invented by Hermes for creating fire."},
    "Pomegranate": {"type": "object", "description": "The fruit whose seeds bound Persephone to the Underworld."},
    "Olive Tree": {"type": "plant", "description": "The olive tree created by Athena in her contest with Poseidon."},
    "Laurel": {"type": "plant", "description": "The laurel tree into which Daphne was transformed; sacred to Apollo."},
    "Flower": {"type": "plant", "description": "The flower into which Hyacinthus was transformed from his blood."},
    "Cypress Tree": {"type": "plant", "description": "The tree into which Cyparissus was transformed after grieving his stag."},
    "Salt Spring": {"type": "place", "description": "The salt spring (or horse) created by Poseidon in his contest with Athena."},
    "Apollo's Cattle": {"type": "animal", "description": "The herd of cattle belonging to Apollo, stolen by the infant Hermes."},
    "Dragon's Teeth": {"type": "object", "description": "Teeth of the dragon slain by Cadmus; sown to produce armed men."},

    # ── 神话元素 / 剧本 ──
    "Iphigenia in Tauris": {"type": "myth", "description": "Euripides' play about Iphigenia serving as a priestess in Tauris."},
    "Republic": {"type": "concept", "description": "Plato's philosophical work, which includes the Myth of Er."},
    "Bernini Sculpture": {"type": "artwork", "description": "Bernini's sculpture depicting Apollo and Daphne."},

    # ── 核心缺失实体 ──
    "Medea's Children": {"type": "mortal", "description": "The two sons of Medea and Jason, killed by Medea as revenge against Jason."},

    # ── 描述性悬空（灵魂转世选择）→ 归入概念 ──
    "Male Athlete": {"type": "concept", "description": "The life form chosen by the soul of Atalanta in Plato's Myth of Er."},
    "Craftswoman": {"type": "concept", "description": "The life form chosen by the soul of Epeus in Plato's Myth of Er."},
    "Quiet Life of an Ordinary Man": {"type": "concept", "description": "The life form chosen by the soul of Odysseus in Plato's Myth of Er."},
}

# 关系目标重映射（将悬空名称修正为已有的或新创建的实体名）
RELATIONSHIP_TARGET_FIXES = {
    "her children": "Medea's Children",
    "his children": "Medea's Children",
    "serpent (dragon)": "Colchian Dragon",
    "noah": "Noah",
    "earth": "Gaia",
    "ajax the locrian": "Ajax the Locrian (son of Oïleus)",
    "serpent": "Serpent",
    "snake": "Serpent",
}


def _create_fixup_entity(merged: dict, ename: str, eprops: dict, entity_names_lower: set):
    """根据 FIXUP_ENTITIES 配置创建一个实体并加入对应分类"""
    etype = eprops.get("type", "other")
    type_to_category = {
        "group": "characters", "race": "concepts", "warrior": "characters",
        "nymph": "characters", "monster": "characters", "creature": "characters",
        "animal": "characters", "object": "concepts", "plant": "concepts",
        "myth": "myths", "artwork": "artworks", "mortal": "characters",
        "concept": "concepts", "god": "characters", "goddess": "characters",
    }
    category = type_to_category.get(etype, "characters")

    if category == "myths":
        entity = {"name": ename, "summary": eprops.get("description", ""), "key_characters": [], "mentioned_pages": []}
    elif category == "concepts":
        entity = {"name": ename, "definition": eprops.get("description", ""), "mentioned_pages": []}
    elif category == "artworks":
        entity = {"name": ename, "type": eprops.get("artwork_type", "other"), "description": eprops.get("description", ""), "mentioned_pages": []}
    elif category == "places":
        entity = {"name": ename, "type": etype, "description": eprops.get("description", ""), "mentioned_pages": []}
    else:
        entity = {"name": ename, "roman_name": "", "epithets": [], "domains": [], "symbols": [], "type": etype, "description": eprops.get("description", ""), "mentioned_pages": [], "evidence": [], "chapters": []}

    merged.setdefault(category, []).append(entity)
    entity_names_lower.add(ename.lower())


def cleanup_dangling_references(merged: dict):
    """
    清洗知识图谱中的悬空引用：

    1. 自动为缺少独立实体的罗马名创建实体
    2. 按 RELATIONSHIP_TARGET_FIXES 重映射关系目标
    3. 为仍有悬空引用的目标按 FIXUP_ENTITIES 创建实体
    4. 移除残留的、无法处理的悬空关系
    """
    # 构建现有实体名称索引
    entity_names_lower = set()
    for cat in ["characters", "myths", "places", "concepts", "artworks"]:
        for e in merged.get(cat, []):
            name = (e.get("name") or "").strip().lower()
            if name:
                entity_names_lower.add(name)

    created_count = 0
    remapped_count = 0

    # ── 步骤1：自动创建缺失的罗马名实体 ──
    new_characters = []
    for c in merged.get("characters", []):
        roman = (c.get("roman_name") or "").strip()
        greek = c.get("name") or ""
        if roman and roman.lower() not in entity_names_lower:
            roman_entity = {
                "name": roman,
                "roman_name": "",
                "epithets": [],
                "domains": [],
                "symbols": [],
                "type": c.get("type", "other"),
                "description": f"Roman equivalent of {greek}.",
                "mentioned_pages": [],
                "evidence": [],
                "chapters": [],
            }
            new_characters.append(roman_entity)
            entity_names_lower.add(roman.lower())
            # 添加反向关系：罗马名 ──[greek_equivalent]──> 希腊名
            merged["relationships"].append({
                "source": roman,
                "target": greek,
                "type": "greek_equivalent",
                "description": f"{roman} is the Roman equivalent of {greek}.",
                "page": 0,
            })
            created_count += 1
    if new_characters:
        merged["characters"].extend(new_characters)
        print(f"  创建了 {len(new_characters)} 个罗马名实体")

    # ── 步骤2：重映射关系目标 ──
    for r in merged.get("relationships", []):
        old_target = r.get("target", "").strip()
        old_source = r.get("source", "").strip()
        fixed = False
        if old_target.lower() in RELATIONSHIP_TARGET_FIXES:
            r["target"] = RELATIONSHIP_TARGET_FIXES[old_target.lower()]
            fixed = True
        if old_source.lower() in RELATIONSHIP_TARGET_FIXES:
            r["source"] = RELATIONSHIP_TARGET_FIXES[old_source.lower()]
            fixed = True
        if fixed:
            r["_cleaned"] = True
            remapped_count += 1
    if remapped_count > 0:
        print(f"  重映射了 {remapped_count} 条关系目标")

    # ── 步骤2b：为步骤2重映射到的目标创建实体 ──
    # 例如 "serpent" → "Serpent" 需要确保 "Serpent" 实体存在
    remap_targets = set(RELATIONSHIP_TARGET_FIXES.values())
    fixup_keys_lower = {k.lower(): k for k in FIXUP_ENTITIES}
    for target in remap_targets:
        if target.lower() in fixup_keys_lower and target.lower() not in entity_names_lower:
            proper_name = fixup_keys_lower[target.lower()]
            eprops = FIXUP_ENTITIES[proper_name]
            _create_fixup_entity(merged, proper_name, eprops, entity_names_lower)
            created_count += 1

    # ── 步骤3：为仍有悬空引用的目标创建实体 ──
    # 重新索引（包含新创建的罗马实体）
    entity_names_lower = set()
    for cat in ["characters", "myths", "places", "concepts", "artworks"]:
        for e in merged.get(cat, []):
            name = (e.get("name") or "").strip().lower()
            if name:
                entity_names_lower.add(name)

    # 收集所有悬空引用
    dangling_targets = set()
    for r in merged.get("relationships", []):
        tgt = r.get("target", "").strip().lower()
        src = r.get("source", "").strip().lower()
        if tgt and tgt not in entity_names_lower:
            dangling_targets.add(r["target"].strip())
        if src and src not in entity_names_lower:
            dangling_targets.add(r["source"].strip())

    if dangling_targets:
        # 确定应该创建哪些实体（使用 FIXUP_ENTITIES 中的规范名）
        dangling_normalize = {}
        for fx_key in FIXUP_ENTITIES:
            dangling_normalize[fx_key.lower()] = fx_key

        to_create = {}
        old_to_new = {}
        for name in sorted(dangling_targets):
            key = name.lower()
            if key in RELATIONSHIP_TARGET_FIXES:
                continue  # 已在步骤2处理
            if key in dangling_normalize:
                proper_name = dangling_normalize[key]
                to_create[proper_name] = FIXUP_ENTITIES[proper_name]
                old_to_new[name] = proper_name

        # 将关系中的旧名称替换为规范名
        for name, proper in old_to_new.items():
            for r in merged.get("relationships", []):
                if r.get("target", "").strip() == name:
                    r["target"] = proper
                    r["_cleaned"] = True
                if r.get("source", "").strip() == name:
                    r["source"] = proper
                    r["_cleaned"] = True

        # 创建实体并添加到对应分类
        for ename, eprops in to_create.items():
            _create_fixup_entity(merged, ename, eprops, entity_names_lower)
            created_count += 1

        if to_create:
            print(f"  创建了 {len(to_create)} 个缺失实体")

    # ── 步骤4：为仍悬空的引用自动创建桩实体 ──
    auto_created = 0
    while True:
        # 重新索引实体名
        entity_names_lower = set()
        for cat in ["characters", "myths", "places", "concepts", "artworks"]:
            for e in merged.get(cat, []):
                name = (e.get("name") or "").strip().lower()
                if name:
                    entity_names_lower.add(name)

        # 找出当前仍悬空的名字
        dangling_now = set()
        for r in merged.get("relationships", []):
            tgt = r.get("target", "").strip()
            src = r.get("source", "").strip()
            if tgt and tgt.lower() not in entity_names_lower:
                dangling_now.add(tgt)
            if src and src.lower() not in entity_names_lower:
                dangling_now.add(src)

        if not dangling_now:
            break

        # 为每个悬空名创建桩实体
        new_count = 0
        for name in sorted(dangling_now):
            if name.lower() in entity_names_lower:
                continue
            # 简单启发推断类型
            lower_name = name.lower()
            if any(kw in lower_name for kw in ["myth", "tale", "story", "birth of", "death of", "judgment", "sacrifice", "quest", "journey"]):
                cat = "myths"
                entity = {"name": name, "summary": "", "key_characters": [], "mentioned_pages": []}
            elif any(kw in lower_name for kw in ["vase", "painting", "sculpture", "krater", "amphora", "cup", "hydria"]):
                cat = "artworks"
                entity = {"name": name, "type": "other", "description": "", "mentioned_pages": []}
            elif any(kw in lower_name for kw in ["mountain", "river", "island", "city", "temple", "cave", "forest", "plain", "sea", "lake"]):
                cat = "places"
                entity = {"name": name, "type": "mythological", "description": "", "mentioned_pages": []}
            else:
                # 默认为概念类
                cat = "concepts"
                entity = {"name": name, "definition": "", "mentioned_pages": []}
            merged.setdefault(cat, []).append(entity)
            entity_names_lower.add(name.lower())
            new_count += 1

        if new_count > 0:
            auto_created += new_count
        else:
            break  # 安全阀

    if auto_created > 0:
        print(f"  自动创建了 {auto_created} 个桩实体以修复剩余悬空引用")




def main():
    """主函数：合并所有章节的知识图谱"""
    print("=" * 60)
    print("Mythos AI — 知识图谱合并工具")
    print("=" * 60)

    # 检查章节知识文件
    json_files = sorted(KNOWLEDGE_DIR.glob("chapter_*.json"))
    if not json_files:
        print(f"\n[错误] 未找到章节知识文件！")
        print(f"  请先运行 02_extract_knowledge.py")
        print(f"  文件应位于: {KNOWLEDGE_DIR}")
        return

    print(f"\n找到 {len(json_files)} 个章节知识文件")

    # 读取所有章节数据
    all_chapters = []
    for fpath in json_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        all_chapters.append(data)
        ch = data.get("chapter", "?")
        char_count = len(data.get("characters", []))
        myth_count = len(data.get("myths", []))
        rel_count = len(data.get("relationships", []))
        print(f"  第 {ch:2d} 章: {char_count:3d} 个人物, {myth_count:3d} 个神话, {rel_count:3d} 条关系")

    # ── 分类收集所有实体和关系 ──
    categories = ["characters", "myths", "places", "concepts", "artworks"]

    all_by_category = {cat: [] for cat in categories}
    all_relationships = []

    for chapter_data in all_chapters:
        for cat in categories:
            all_by_category[cat].append(chapter_data.get(cat, []))
        all_relationships.append(chapter_data.get("relationships", []))

    # ── 合并实体 ──
    print("\n正在合并实体...")
    merged = {}
    for cat in categories:
        merged[cat] = merge_entities(all_by_category[cat])
        print(f"  {cat}: {sum(len(e) for e in all_by_category[cat])} 条 → 合并为 {len(merged[cat])} 条")

    # ── 合并关系 ──
    print("\n正在合并关系...")
    total_rels_before = sum(len(r) for r in all_relationships)
    merged["relationships"] = merge_relationships(all_relationships)
    print(f"  relationships: {total_rels_before} 条 → 合并为 {len(merged['relationships'])} 条")

    # ── 构建证据索引 ──
    print("\n正在构建证据索引...")
    evidence_index = defaultdict(list)
    for chapter_data in all_chapters:
        ch = chapter_data.get("chapter", 0)
        for cat in categories:
            for entity in chapter_data.get(cat, []):
                name = entity.get("name", "")
                if name:
                    # 使用 normalize_name 确保与查询键一致
                    evidence_index[normalize_name(name)].append(build_evidence(entity, ch))

    # ── 添加证据到合并实体 ──
    for cat in categories:
        for entity in merged[cat]:
            key = normalize_name(entity.get("name", ""))
            if key in evidence_index:
                entity["evidence"] = evidence_index[key]
                # 不再保留单独的证据列表，用 chapters 字段替代
                chapters = sorted(set(ev["chapter"] for ev in evidence_index[key]))
                entity["chapters"] = chapters

    # ── 清洗悬空引用 ──
    print("\n正在清洗悬空引用...")
    cleanup_dangling_references(merged)
    total_cleaned = sum(
        1 for r in merged["relationships"]
        if r.get("_cleaned", False)
    )
    # 移除内部标记
    for r in merged["relationships"]:
        r.pop("_cleaned", None)
    print(f"  已修复 {total_cleaned} 条悬空关系")

    # ── 分配唯一ID ──
    print("\n正在分配实体ID...")
    id_prefixes = {
        "characters": "CHAR", "myths": "MYTH", "places": "PLACE",
        "concepts": "CON", "artworks": "ART",
    }
    name_to_id = {}  # lowercase name → ID
    id_counters = {}
    for cat in categories:
        id_counters[cat] = 1
        for entity in merged.get(cat, []):
            name = entity.get("name", "")
            if name:
                prefix = id_prefixes[cat]
                eid = f"{prefix}_{id_counters[cat]:04d}"
                entity["id"] = eid
                id_counters[cat] += 1
                name_to_id[normalize_name(name)] = eid

    # ── 添加 primary_chapter ──
    print("正在计算主章节...")
    for cat in categories:
        for entity in merged.get(cat, []):
            evidence = entity.get("evidence", [])
            if len(evidence) > 1:
                # 主章节 = 页码最多的章节
                best_ch = max(evidence, key=lambda e: len(e.get("printed_pages", [])))
                entity["primary_chapter"] = best_ch["chapter"]
            elif len(evidence) == 1:
                entity["primary_chapter"] = evidence[0]["chapter"]

    # ── 关系引用改为ID ──
    print("正在转换关系引用为ID...")
    for r in merged.get("relationships", []):
        src_name = r.get("source", "").strip()
        tgt_name = r.get("target", "").strip()
        src_id = name_to_id.get(normalize_name(src_name))
        tgt_id = name_to_id.get(normalize_name(tgt_name))
        if src_id:
            r["source_id"] = src_id
        if tgt_id:
            r["target_id"] = tgt_id

    # ── 构建最终知识图谱 ──
    knowledge_graph = {
        "metadata": {
            "source": "Classical Mythology (11th Edition), Morford, Lenardon, Sham",
            "source_file": "classical_myth.pdf",
            "chapters_processed": len(all_chapters),
            "total_characters": len(merged["characters"]),
            "total_myths": len(merged["myths"]),
            "total_places": len(merged["places"]),
            "total_concepts": len(merged["concepts"]),
            "total_artworks": len(merged["artworks"]),
            "total_relationships": len(merged["relationships"]),
        },
        "characters": merged["characters"],
        "myths": merged["myths"],
        "places": merged["places"],
        "concepts": merged["concepts"],
        "artworks": merged["artworks"],
        "relationships": merged["relationships"],
    }

    # 保存
    OUTPUT_FILE.write_text(
        json.dumps(knowledge_graph, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── 统计报告 ──
    print(f"\n{'=' * 60}")
    print(f"知识图谱已生成！")
    print(f"{'=' * 60}")
    print(f"  人物 (Characters):   {len(merged['characters'])}")
    print(f"  神话 (Myths):        {len(merged['myths'])}")
    print(f"  地点 (Places):       {len(merged['places'])}")
    print(f"  概念 (Concepts):     {len(merged['concepts'])}")
    print(f"  艺术品 (Artworks):   {len(merged['artworks'])}")
    print(f"  关系 (Relationships):{len(merged['relationships'])}")
    print(f"{'=' * 60}")
    print(f"输出文件: {OUTPUT_FILE}")

    # 统计出现次数最多的章节
    char_chapters = defaultdict(int)
    for char in merged["characters"]:
        for ch in char.get("chapters", []):
            char_chapters[ch] += 1
    if char_chapters:
        top_chs = sorted(char_chapters.items(), key=lambda x: -x[1])[:5]
        print(f"\n人物最多的章节: {', '.join(f'第{c}章({n}人)' for c, n in top_chs)}")


if __name__ == "__main__":
    main()
