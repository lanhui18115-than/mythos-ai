import json, os

kg = json.loads(open('data/knowledge_graph.json', 'r', encoding='utf-8').read())

# Search for problematic characters in all string values
import re

problematic = []

def search_obj(obj, path=''):
    if isinstance(obj, str):
        for ch in ['\u2028', '\u2029', '\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005', '\u0006', '\u0007', '\u0008', '\u000e', '\u000f', '\u0010', '\u0011', '\u0012', '\u0013', '\u0014', '\u0015', '\u0016', '\u0017', '\u0018', '\u0019', '\u001a', '\u001b', '\u001c', '\u001d', '\u001e', '\u001f']:
            if ch in obj:
                problematic.append((path, repr(ch), obj[:100]))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            search_obj(v, path + '.' + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            search_obj(v, path + f'[{i}]')

search_obj(kg)

# Also check enhanced_myth_summaries
if os.path.exists('data/enhanced_myth_summaries.json'):
    em = json.loads(open('data/enhanced_myth_summaries.json', 'r', encoding='utf-8').read())
    for k, v in em.items():
        for ch in ['\u2028', '\u2029']:
            if ch in v:
                problematic.append(('enhanced_myths.' + k, repr(ch), v[:100]))

print(f"Found {len(problematic)} problematic characters")
for p in problematic[:20]:
    print(f"  {p[0]}: {p[1]} -> {p[2]}")
