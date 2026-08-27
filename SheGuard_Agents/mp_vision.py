import mediapipe.tasks.vision as vision
print('Vision dir:', [x for x in dir(vision) if not x.startswith('_')])
