with open('C:/Programs/codex/SheGuard/SheGuard_Backend/app/routes/incidents.py', 'r') as f:
    content = f.read()

old_func = '''async def _incident_payload_from_request(request: Request, incident_dir: str | Path | None = None) -> tuple[IncidentCreate, StoredIncidentMedia | None]:
    content_type = request.headers.get(\
content-type\, \\).lower()
    if content_type.startswith(\multipart/form-data\):
        form = await request.form()
        # Handle different field names: \file\, \image\, \video\
        upload_file = form.get(\file\) or form.get(\image\)
        image_file = form.get(\image\)
        video_file = form.get(\video\) or form.get(\video\)  # Handle both cases

        incident_dir_path = Path(incident_dir) if incident_dir else None
        if upload_file:
            # Also check for video file in the same request
            video_file = form.get(\video\)
            uploaded_media = await store_uploaded_incident_media(
                image_file=upload_file,
                video_file=video_file,
                incident_time=datetime.utcnow(),
                incident_dir=incident_dir_path,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
            )
            payload = IncidentCreate(
                incident_type=form.get(\incident_type\, \unknown\),
                confidence=float(form.get(\confidence\, 0.9)),
                ai_summary=form.get(\ai_summary\),
                latitude=float(form.get(\latitude\)) if form.get(\latitude\) else None,
                longitude=float(form.get(\longitude\)) if form.get(\longitude\) else None,
                camera_id=form.get(\camera_id\),
                user_id=int(form.get(\user_id\)) if form.get(\user_id\) else None,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
                metadata_path=str(incident_dir_path / \metadata.json\) if incident_dir_path else None,
            )
            return payload, uploaded_media
        elif image_file or video_file:
            from app.services.media_storage import create_incident_folder
            incident_time = datetime.utcnow()
            save_dir = create_incident_folder(incident_time, incident_folder_id=incident_dir)
            image_path = None
            video_path = None
            if image_file:
                image_path = str(save_dir / \frame_1.jpg\)
                image_path_bytes = await image_file.read()
                Path(image_path).write_bytes(image_path_bytes)
            if video_file:
                video_path = str(save_dir / \incident_video.mp4\)
                video_path_bytes = await video_file.read()
                Path(video_path).write_bytes(video_path_bytes)
            
            uploaded_media = StoredIncidentMedia(
                image_path=image_path,
                video_path=video_path,
                incident_dir=str(save_dir),
            )
            payload = IncidentCreate(
                incident_type=form.get(\incident_type\, \unknown\),
                confidence=float(form.get(\confidence\, 0.9)),
                ai_summary=form.get(\ai_summary\),
                latitude=float(form.get(\latitude\)) if form.get(\latitude\) else None,
                longitude=float(form.get(\longitude\)) if form.get(\longitude\) else None,
                camera_id=form.get(\camera_id\),
                user_id=int(form.get(\user_id\)) if form.get(\user_id\) else None,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
                metadata_path=str(save_dir / \metadata.json\),
            )
            return payload, uploaded_media
            body = await request.json()
    payload = IncidentCreate(**body)
    return payload, None'''

new_func = '''async def _incident_payload_from_request(request: Request, incident_dir: str | Path | None = None) -> tuple[IncidentCreate, StoredIncidentMedia | None]:
    content_type = request.headers.get(\content-type\, \\).lower()
    if content_type.startswith(\multipart/form-data\):
        form = await request.form()
        # Handle different field names: \file\, \image\, \video\
        upload_file = form.get(\file\) or form.get(\image\)
        image_file = form.get(\image\)
        video_file = form.get(\video\)

        incident_dir_path = Path(incident_dir) if incident_dir else None
        if upload_file:
            # Also check for video file in the same request
            video_file = form.get(\video\)
            uploaded_media = await store_uploaded_incident_media(
                image_file=upload_file,
                video_file=video_file,
                incident_time=datetime.utcnow(),
                incident_dir=incident_dir_path,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
            )
            payload = IncidentCreate(
                incident_type=form.get(\incident_type\, \unknown\),
                confidence=float(form.get(\confidence\, 0.9)),
                ai_summary=form.get(\ai_summary\),
                latitude=float(form.get(\latitude\)) if form.get(\latitude\) else None,
                longitude=float(form.get(\longitude\)) if form.get(\longitude\) else None,
                camera_id=form.get(\camera_id\),
                user_id=int(form.get(\user_id\)) if form.get(\user_id\) else None,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
                metadata_path=str(incident_dir_path / \metadata.json\) if incident_dir_path else None,
            )
            return payload, uploaded_media
        elif image_file or video_file:
            from app.services.media_storage import create_incident_folder
            incident_time = datetime.utcnow()
            save_dir = create_incident_folder(incident_time, incident_folder_id=incident_dir)
            image_path = None
            video_path = None
            if image_file:
                image_path = str(save_dir / \frame_1.jpg\)
                image_path_bytes = await image_file.read()
                Path(image_path).write_bytes(image_path_bytes)
            if video_file:
                video_path = str(save_dir / \incident_video.mp4\)
                video_path_bytes = await video_file.read()
                Path(video_path).write_bytes(video_path_bytes)
            
            uploaded_media = StoredIncidentMedia(
                image_path=image_path,
                video_path=video_path,
                incident_dir=str(save_dir),
            )
            payload = IncidentCreate(
                incident_type=form.get(\incident_type\, \unknown\),
                confidence=float(form.get(\confidence\, 0.9)),
                ai_summary=form.get(\ai_summary\),
                latitude=float(form.get(\latitude\)) if form.get(\latitude\) else None,
                longitude=float(form.get(\longitude\)) if form.get(\longitude\) else None,
                camera_id=form.get(\camera_id\),
                user_id=int(form.get(\user_id\)) if form.get(\user_id\) else None,
                frame_count=int(form.get(\frame_count\)) if form.get(\frame_count\) else None,
                metadata_path=str(save_dir / \metadata.json\),
            )
            return payload, uploaded_media

    # JSON request
    body = await request.json()
    payload = IncidentCreate(**body)
    return payload, None'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('C:/Programs/codex/SheGuard/SheGuard_Backend/app/routes/incidents.py', 'w') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Pattern not found')
