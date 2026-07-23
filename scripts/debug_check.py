html = open('output/character_index.html','r',encoding='utf-8').read()
start = html.find('id="fb"')
end = html.find('id="cg"')
print(html[start:end][:1000])
