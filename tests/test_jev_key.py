"""The Jev key check (offline: the network call is faked)."""
import urllib.error

from triage import jev_client
from ui.jev_key import APP_PASSWORD, jev_error


def fake_urlopen(code):
    def opener(request, timeout=10):
        assert request.get_header("Authorization") == "Bearer sk-test"  # sent exactly like the SDK sends it
        if code != 200:
            raise urllib.error.HTTPError(request.full_url, code, "error", {}, None)
    return opener


def test_check_key_reports_accepted_rejected_and_unreachable(monkeypatch):
    for code, expected in ((200, "ok"), (401, "rejected"), (500, "unreachable")):
        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen(code))
        assert jev_client.check_key("sk-test") == expected


def test_spots_a_gmail_app_password_in_the_jev_box():
    assert APP_PASSWORD.fullmatch("abcd efgh ijkl mnop") and APP_PASSWORD.fullmatch("abcdefghijklmnop")
    assert not APP_PASSWORD.fullmatch("sk-live-1234567890abcdef")


def test_401_gets_a_plain_language_message():
    assert "rejected the Jev key" in jev_error(Exception("POST /v1/systemone: 401 Cannot authenticate"))
    assert jev_error(Exception("timeout")).startswith("Jev couldn't sort")
