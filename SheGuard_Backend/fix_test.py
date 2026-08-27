with open("tests/test_backend.py", "r") as f:
    content = f.read()

old = """        location = client.post(
            "/location/update",
            json={"user_id": user_id, "latitude": 12.9716, "longitude": 77.5946, "speed": 1.0},
        )"""

new = """        token = login.json()["access_token"]
        location = client.post(
            "/location/update",
            json={"user_id": user_id, "latitude": 12.9716, "longitude": 77.5946, "speed": 1.0},
            headers={"Authorization": f"Bearer {token}"},
        )"""

content = content.replace(old, new)

with open("tests/test_backend.py", "w") as f:
    f.write(content)

print("Fixed test_backend_core_flow")
