with open("tests/test_backend.py", "r") as f:
    content = f.read()

# Fix the test to correctly extract file handle from tuple
old = """    def fake_post(url, **kwargs):
        calls.append((url.rsplit("/", 1)[-1], kwargs))
        files = kwargs.get("files") or {}
        for handle in files.values():
            assert Path(handle.name).is_absolute()
        return FakeResponse()"""

new = """    def fake_post(url, **kwargs):
        calls.append((url.rsplit("/", 1)[-1], kwargs))
        files = kwargs.get("files") or {}
        for handle in files.values():
            # handle is a tuple (filename, file_object, content_type)
            file_obj = handle[1] if isinstance(handle, tuple) else handle
            assert Path(file_obj.name).is_absolute()
        return FakeResponse()"""

if old in content:
    content = content.replace(old, new)
    with open("tests/test_backend.py", "w") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found")
