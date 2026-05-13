"""Unit tests for the policy engine. Run with `cd api && pytest ../tests`."""

import sys
from pathlib import Path


# Allow import of the api package when running from the project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from policy import PolicyEngine, User


def _engine():
    return PolicyEngine.from_file(ROOT / "api" / "policy" / "rules.yaml")


def _user(role: str) -> User:
    return User(sub="test", username="test", role=role, claims={})


def test_admin_can_do_anything():
    d = _engine().can_execute_command(
        _user("admin"), "anything-goes", "http://whatever/foo", "http://schemas/x.json"
    )
    assert d.allowed, d.reason


def test_user_denied_internal_path():
    d = _engine().can_execute_command(
        _user("user"), "converttojson", "file:///data/products.csv", None
    )
    assert not d.allowed


def test_user_allowed_public_path():
    d = _engine().can_execute_command(
        _user("user"), "converttojson", "file:///data/public/posts.json", None
    )
    assert d.allowed, d.reason


def test_unknown_role_denied():
    d = _engine().can_execute_command(_user("stranger"), "fetch", "http://data/x", None)
    assert not d.allowed


def test_analyst_can_run_pipeline():
    d = _engine().can_execute_command(
        _user("analyst"), "pipeline", "http://data/x", None
    )
    assert d.allowed


def test_query_access_respects_uris():
    eng = _engine()
    ok = eng.can_execute_query(_user("user"), "from-url", ["http://cqrs-data/x"])
    assert ok.allowed
    bad = eng.can_execute_query(_user("user"), "from-url", ["http://secret/x"])
    assert not bad.allowed
