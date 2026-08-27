with open('app/routes/incidents.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'content_type = request.headers.get' in line:
        lines[i] = '    content_type = request.headers.get(\
content-type\, \\).lower()\n'
        print('Fixed line', i+1)
with open('app/routes/incidents.py', 'w') as f:
    f.writelines(lines)
print('Done')
