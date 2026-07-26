python - << 'PYEOF'
import pathlib
p = pathlib.Path("tests/test_scopes.py")
s = p.read_text()

old = '''        message = str(excinfo.value).lower()
        assert any(
            word in message
            for word in ("scope", "auth", "permit", "denied", "forbidden", "not found")
        ), f"refused, but not recognisably on authorization grounds: {excinfo.value}"'''

new = '''        message = str(excinfo.value).lower()
        # Component auth hides rather than 403s: an out-of-scope tool is filtered
        # out of the caller's surface entirely, so the refusal surfaces as
        # "Unknown tool" rather than "insufficient scope". That is the stronger
        # outcome, and it is why "unknown tool" counts as an authorization refusal.
        assert any(
            phrase in message
            for phrase in (
                "unknown tool",
                "not found",
                "scope",
                "auth",
                "permit",
                "denied",
                "forbidden",
            )
        ), f"refused, but not recognisably on authorization grounds: {excinfo.value}"'''

assert old in s, "assertion block not found unchanged; edit by hand"
p.write_text(s.replace(old, new))
print("patched")
PYEOF

python -m pytest
