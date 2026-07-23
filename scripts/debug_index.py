content = open('output/character_index.html', 'r', encoding='utf-8').read()

# Find body HTML after the script tag
script_start = content.find('<script>')
head_end = content[:script_start].rfind('</head>')
body_html = content[head_end:script_start]
print(body_html[:3000])
