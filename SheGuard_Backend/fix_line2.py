with open('app/routes/incidents.py', 'r') as f:
    lines = f.readlines()
lines[259] = '    content_type = request.headers.get(\
content-type\, \\).lower()\n'
with open('app/routes/incidents.py', 'w') as f:
    f.writelines(lines)
print('Fixed')
