import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Create 4 users and test multi-user isolation
users = []
for i in range(4):
    phone = '9' + str(100000000 + i * 11111111)
    reg = client.post('/register', json={'full_name': 'User'+str(i+1), 'phone_number': phone, 'password': 'secret123'})
    if reg.status_code == 200:
        login = client.post('/login', json={'phone_number': phone, 'password': 'secret123'})
        token = login.json()['access_token']
        user_id = login.json()['user_id']
        users.append({'phone': phone, 'token': token, 'user_id': user_id})
        print(f"User{i+1}: user_id={user_id}")
    else:
        print(f"User{i+1} register failed: {reg.status_code}")

# User A - SOS
if len(users) >= 1:
    sos_a = client.post('/emergency/start', json={
        'user_id': users[0]['user_id'],
        'trigger_source': 'manual_sos',
        'latitude': 12.9716,
        'longitude': 77.5946
    }, headers={'Authorization': 'Bearer ' + users[0]['token']})
    print(f"User A SOS: {sos_a.status_code}")
    if sos_a.status_code == 200:
        print(f"  Session: {sos_a.json()}")

# User B - HELP
if len(users) >= 2:
    help_b = client.post('/emergency/start', json={
        'user_id': users[1]['user_id'],
        'trigger_source': 'help_voice',
        'latitude': 12.9717,
        'longitude': 77.5947
    }, headers={'Authorization': 'Bearer ' + users[1]['token']})
    print(f"User B HELP: {help_b.status_code}")

# User C - Tracking
if len(users) >= 3:
    track_c = client.post('/locations/start', json={
        'user_id': users[2]['user_id'],
        'latitude': 12.9718,
        'longitude': 77.5948
    }, headers={'Authorization': 'Bearer ' + users[2]['token']})
    print(f"User C Tracking: {track_c.status_code}")
    if track_c.status_code == 200:
        loc_c = client.post('/locations/update', json={
            'user_id': users[2]['user_id'],
            'latitude': 12.9720,
            'longitude': 77.5950,
            'speed': 2.0,
            'battery': 80,
            'accuracy': 10.0
        }, headers={'Authorization': 'Bearer ' + users[2]['token']})
        print(f"User C Location Update: {loc_c.status_code}")

# User D - SOS
if len(users) >= 4:
    sos_d = client.post('/emergency/start', json={
        'user_id': users[3]['user_id'],
        'trigger_source': 'manual_sos',
        'latitude': 12.9719,
        'longitude': 77.5949
    }, headers={'Authorization': 'Bearer ' + users[3]['token']})
    print(f"User D SOS: {sos_d.status_code}")

# Get all emergencies (police dashboard view)
print("\n--- All Emergency Sessions (Police View) ---")
for u in users:
    sessions = client.get('/emergency/session?user_id=' + str(u['user_id']), headers={'Authorization': 'Bearer ' + u['token']})
    print(f"User {u['user_id']} sessions: {sessions.status_code} - {sessions.json()}")

# Test cross-user isolation
print("\n--- Cross-user isolation test ---")
if len(users) >= 2:
    cross = client.get('/emergency/session/sos-123', headers={'Authorization': 'Bearer ' + users[0]['token']})
    print(f"User A accessing B session: {cross.status_code}")
