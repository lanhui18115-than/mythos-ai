content = open('output/character_index.html', 'r', encoding='utf-8').read()

# Find the JS after all JSON data declarations
marker = 'var TYPE_COLORS = '
js_data_start = content.find(marker)
# Find the closing script tag
script_end = content.find('</script>', js_data_start)
js_code = content[js_data_start:script_end]
print(js_code[:4000])
print("...")
print(js_code[-1000:])
