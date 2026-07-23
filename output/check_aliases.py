import json

kg = json.load(open('data/knowledge_graph.json','r',encoding='utf-8'))
chars = kg['characters']

# Count roman names
with_roman = [c for c in chars if c.get('roman_name')]
print('Characters with roman_name:', len(with_roman))
print('Sample:')
for c in with_roman[:20]:
    print('  %s -> %s' % (c['name'], c.get('roman_name','')))

# Check for cross-references
names_set = {c['name'] for c in chars}
roman_set = {c.get('roman_name','') for c in chars if c.get('roman_name')}
intersection = names_set & roman_set
print()
print('Names that also appear as roman_name of another:')
for n in sorted(intersection):
    sources = [c['name'] for c in chars if c.get('roman_name')==n]
    print('  %s is roman name of: %s' % (n, sources))

# Check epithets field
has_epithets = [c for c in chars if c.get('epithets')]
print()
print('Characters with epithets:', len(has_epithets))
if has_epithets:
    print('Sample:', has_epithets[0]['name'], '->', has_epithets[0]['epithets'][:3])
