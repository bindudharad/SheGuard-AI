with open('app/routes/incidents.py') as f: c=f.read(); c=c.replace('        content_type = request.headers.get(\
content-type\, \\).lower()', '    content_type = request.headers.get(\content-type\, \\).lower()'); open('app/routes/incidents.py','w').write(c); print('Fixed')
