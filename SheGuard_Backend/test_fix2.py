with open("tests/test_backend.py", "r") as f:
    content = f.read()

# Fix the test to use the correct parameter name
old = """    manager = EvidenceManager(
        incident_root=str(tmp_path / "incidents"),
        fps=20.0,
        pre_event_seconds=10.0,
    )"""

new = """    manager = EvidenceManager(
        evidence_dir=str(tmp_path / "incidents"),
        fps=20.0,
        pre_event_seconds=10.0,
    )"""

if old in content:
    content = content.replace(old, new)
    with open("tests/test_backend.py", "w") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found")
