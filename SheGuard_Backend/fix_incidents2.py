with open('app/routes/incidents.py', 'r') as f:
    content = f.read()

# Fix the indentation issue on line 260
content = content.replace('        content_type = request.headers.get(\
content-type\, \\).lower()', '    content_type = request.headers.get(\content-type\, \\).lower()')

# Find the duplicate block and remove it
# The duplicate starts after the first 'return payload, uploaded_media' in the elif block
# and ends before 'body = await request.json()'
parts = content.split('return payload, uploaded_media')
# Keep first 3 parts (before first return in elif, the elif return, and before second return)
# The structure is: ... return payload, uploaded_media (from if block)
#                    elif ... return payload, uploaded_media (from elif block) 
#                    return payload, uploaded_media (duplicate from elif block)
#                    body = await request.json()
# So we want parts[0], parts[1], parts[2] + parts[3:] joined
# Actually let's find the second occurrence of the elif block

# Simpler approach: find the second 'from app.services.media_storage import create_incident_folder'
first_idx = content.find('from app.services.media_storage import create_incident_folder')
second_idx = content.find('from app.services.media_storage import create_incident_folder', first_idx + 1)

if second_idx > 0:
    # Find the next 'body = await request.json()' after second_idx
    end_idx = content.find('body = await request.json()', second_idx)
    if end_idx > 0:
        # Remove the duplicate block
        content = content[:second_idx] + content[end_idx:]

with open('app/routes/incidents.py', 'w') as f:
    f.write(content)
print('Fixed!')
