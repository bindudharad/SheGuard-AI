with open('app/routes/incidents.py', 'r') as f:
    content = f.read()

# Fix the metadata write in _create_incident to preserve folder name as incident_id
old = '''    if uploaded_media and uploaded_media.metadata_path:
        try:
            metadata = {
                \
incident_id\: incident.incident_id,
                \incident_type\: payload.incident_type,
                \confidence\: payload.confidence,
                \threat_score\: threat_score,
                \threat_level\: threat_lvl,
                \camera_id\: payload.camera_id,
                \latitude\: payload.latitude,
                \longitude\: payload.longitude,
                \timestamp\: datetime.utcnow().isoformat(),
                \image_path\: uploaded_media.image_path,
                \video_path\: uploaded_media.video_path,
            }
            Path(uploaded_media.metadata_path).write_text(json.dumps(metadata, indent=2))
        except Exception:
            pass'''

new = '''    if uploaded_media and uploaded_media.metadata_path:
        try:
            # Read existing metadata to preserve folder name as incident_id
            import json as _json
            try:
                existing_metadata = _json.loads(Path(uploaded_media.metadata_path).read_text())
                folder_incident_id = existing_metadata.get(\incident_id\, incident.incident_id)
            except Exception:
                folder_incident_id = incident.incident_id
            
            metadata = {
                \incident_id\: folder_incident_id,
                \database_incident_id\: incident.incident_id,
                \incident_type\: payload.incident_type,
                \confidence\: payload.confidence,
                \threat_score\: threat_score,
                \threat_level\: threat_lvl,
                \camera_id\: payload.camera_id,
                \latitude\: payload.latitude,
                \longitude\: payload.longitude,
                \timestamp\: datetime.utcnow().isoformat(),
                \image_path\: uploaded_media.image_path,
                \video_path\: uploaded_media.video_path,
            }
            Path(uploaded_media.metadata_path).write_text(json.dumps(metadata, indent=2))
        except Exception:
            pass'''

if old in content:
    content = content.replace(old, new)
    with open('app/routes/incidents.py', 'w') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Pattern not found')
