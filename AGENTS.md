# Mythos AI — Build Summary

## Current State
- `data/knowledge_graph.json` (4.9 MB) — 1010 chars, 402 myths, 390 places, 433 concepts, 206 artworks, 3340 relationships
- `data/ai_tutor_index.json` (617 KB) — lightweight search index for AI Tutor widget
- `data/name_map.json` (1855 entries) — Chinese→English name mapping with variant support
- `data/enhanced_myth_summaries.json` — Chinese myth summaries with all-character annotation
- `output/ai_tutor_widget.js` (19 KB) — floating chat widget (Layer 4), injected on all 7 pages
- `scripts/14_build_tutor_index.py` — builds `ai_tutor_index.json` from knowledge graph

### Output Pages (all include AI Tutor widget)
- `output/index.html` — Landing page
- `output/learning_center.html` — Textbook reader + chapter summaries + quizzes
- `output/quiz.html` — Quiz system
- `output/crossword.html` — Crossword puzzles
- `output/family_tree.html` — Family tree visualization
- `output/artwork_quiz.html` — Artwork identification
- `output/character_index.html` — Character index

## Key Design Decisions
- AI Tutor is a standalone JS file (no framework dependency), injects its own CSS
- Floating button (bottom-right) → expands to 400px chat panel
- RAG-style: keyword search against pre-built index, results show textbook references
- Index loaded asynchronously on first open (617 KB JSON fetch)
- Chat history persisted in localStorage
- Zero intrusion into existing page HTML/CSS

## Run Commands
- Character index: `py -3 scripts/12_character_index.py`
- AI Tutor index: `py -3 scripts/14_build_tutor_index.py`
- Learning center: `py -3 scripts/13_learning_center.py`

## File Sizes
- `output/character_index.html`: 11 KB
- `data/char_index_data.js`: 4944 KB
- `data/name_map.json`: 78 KB
- `data/ai_tutor_index.json`: 617 KB
- `output/ai_tutor_widget.js`: 19 KB
