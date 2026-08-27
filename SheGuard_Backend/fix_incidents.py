with open('app/routes/incidents.py', 'r') as f:
    content = f.read()

# Fix the indentation issue on line 260
content = content.replace('        content_type = request.headers.get(\
content-type\, \\).lower()', '    content_type = request.headers.get(\content-type\, \\).lower()')

# Remove the duplicate code block
import re
pattern = r'(            return payload, uploaded_media\n            from app\.services\.media_storage import create_incident_folder\n            incident_time = datetime\.utcnow\(\)\n            save_dir = create_incident_folder\(incident_time, incident_folder_id=incident_dir\)\n            image_path = None\n            video_path = None\n            if image_file:\n                image_path = str\(save_dir / \frame_1\.jpg\\)\n                image_path_bytes = await image_file\.read\(\)\n                Path\(image_path\)\.write_bytes\(image_path_bytes\)\n            if video_file:\n                video_path = str\(save_dir / \incident_video\.mp4\\)\n                video_path_bytes = await video_file\.read\(\)\n                Path\(video_path\)\.write_bytes\(video_path_bytes\)\n            \n            uploaded_media = StoredIncidentMedia\(\n                image_path=image_path,\n                video_path=video_path,\n                incident_dir=str\(save_dir\),\n            \)\n            payload = IncidentCreate\(\n                incident_type=form\.get\(\incident_type\, \unknown\\)\n                confidence=float\(form\.get\(\confidence\, 0\.9\)\)\n                ai_summary=form\.get\(\ai_summary\\)\n                latitude=float\(form\.get\(\latitude\\)\) if form\.get\(\latitude\\) else None,\n                longitude=float\(form\.get\(\longitude\\)\) if form\.get\(\longitude\\) else None,\n                camera_id=form\.get\(\camera_id\\)\n                user_id=int\(form\.get\(\user_id\\)\) if form\.get\(\user_id\\) else None,\n                frame_count=int\(form\.get\(\frame_count\\)\) if form\.get\(\frame_count\\) else None,\n                metadata_path=str\(save_dir / \metadata\.json\\)\n            \)\n            return payload, uploaded_media\n)'

# Replace the second occurrence with empty string (keep only first)
content = re.sub(pattern, '', content, count=1)

with open('app/routes/incidents.py', 'w') as f:
    f.write(content)
print('Fixed!')
