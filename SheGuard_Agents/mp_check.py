import mediapipe as mp
print('Version:', mp.__version__)
print('Has solutions:', hasattr(mp, 'solutions'))
if hasattr(mp, 'solutions'):
    print('solutions type:', type(mp.solutions))
    print('solutions:', [x for x in dir(mp.solutions) if not x.startswith('_')])
