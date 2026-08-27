with open('app/routes/incidents.py', 'r') as f:
    content = f.read()
content = content.replace('content_type = request.headers.get(content-type\\, \\).lower()', 'content_type = request.headers.get(\
content-type\, \\).lower()')
with open('app/routes/incidents.py', 'w') as f:
    f.write(content)
print('Fixed')
