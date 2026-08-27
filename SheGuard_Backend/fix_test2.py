with open("tests/test_backend.py", "r") as f:
    content = f.read()

old = """            incident = client.post(
                "/incident/create",
                json={
                    "user_id": user_id,
                    "incident_type": "fall",
                    "confidence": 0.9,
                    "ai_summary": "Test incident",
                    "send_alert": False,
                },
            )"""

new = """            incident = client.post(
                "/incident/create",
                json={
                    "user_id": user_id,
                    "incident_type": "fall",
                    "confidence": 0.9,
                    "ai_summary": "Test incident",
                    "send_alert": False,
                },
                headers={"Authorization": f"Bearer {token}"},
            )"""

content = content.replace(old, new)

with open("tests/test_backend.py", "w") as f:
    f.write(content)

print("Fixed incident creation test")
