import mediapipe.tasks as tasks
print('tasks:', [x for x in dir(tasks) if not x.startswith('_')])
