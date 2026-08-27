import sys
content = sys.stdin.read()
with open("src/services/api.js", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
