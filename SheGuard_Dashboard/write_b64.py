import base64; content = b'placeholder'; b64 = base64.b64encode(content).decode(); open('api_b64.txt', 'w').write(b64)
