import mediapipe.tasks as tasks
print('Vision:', [x for x in dir(tasks.vision) if not x.startswith('_')])
