import mediapipe as mp
print('Version:', mp.__version__)
print('Dir:', [x for x in dir(mp) if not x.startswith('_')])
