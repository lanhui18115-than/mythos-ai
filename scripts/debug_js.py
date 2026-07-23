html = open('output/character_index.html', 'r', encoding='utf-8').read()
start = html.find('<script src=')  # first script tag (data include)
# Find the second script tag
s2 = html.find('<script>', start)
s2_end = html.find('</script>', s2)
js = html[s2 + len('<script>'):s2_end].strip()
print("JS code:")
print(js)
print("\n--- Checking JS syntax ---")
# Check for common issues
lines = js.split('\n')
for i, line in enumerate(lines):
    if 'function' in line and '{' not in line and i < len(lines)-1:
        print(f"  Line {i+1}: function without brace")
    if '=>' in line and '{' not in line:
        pass  # arrow functions without braces are OK
    # Check for obvious issues
