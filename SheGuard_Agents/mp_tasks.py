import mediapipe.tasks as tasks
print('Tasks dir:', [x for x in dir(tasks) if not x.startswith('_')])
