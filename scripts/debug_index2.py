content = open('output/character_index.html', 'r', encoding='utf-8').read()

# Extract JS code after JSON data
js_start = content.find('var CHARACTERS = ')
js_mid = content.find('renderGrid();\n</script>', js_start)
# Find the actual end of the CHARACTERS data
type_groups_start = content.find('var TYPE_GROUPS = ', js_start)
actual_js = content[type_groups_start:js_mid + len('renderGrid();')]
print(actual_js[:5000])
