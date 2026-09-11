"""POST /speech/synthesize — mocked, never a live call to edge-tts's
service: tests must be hermetic (see conftest.py's own note on this),
and a real network TTS call would make this test slow and flaky."""
import edge_tts
import pytest


class _FakeCommunicate:
    def __init__(self, text, voice, rate=None):
        self.text = text
        self.voice = voice

    async def stream(self):
        if not self.text:
            return
        yield {"type": "audio", "data": b"\x00\x01fake-mp3-bytes"}


def test_empty_text_returns_null(client):
    res = client.post("/speech/synthesize", json={"text": "", "language": "en"})
    assert res.status_code == 200
    assert res.json()["audio_url"] is None


def test_synthesizes_to_a_data_url(client, monkeypatch):
    monkeypatch.setattr(edge_tts, "Communicate", _FakeCommunicate)
    res = client.post("/speech/synthesize", json={"text": "Please take a seat.", "language": "hi"})
    assert res.status_code == 200
    audio_url = res.json()["audio_url"]
    assert audio_url.startswith("data:audio/mpeg;base64,")


def test_unknown_language_falls_back_to_english_voice(client, monkeypatch):
    seen_voice = {}

    class _Capturing(_FakeCommunicate):
        def __init__(self, text, voice, rate=None):
            seen_voice["voice"] = voice
            super().__init__(text, voice, rate)

    monkeypatch.setattr(edge_tts, "Communicate", _Capturing)
    client.post("/speech/synthesize", json={"text": "Hello", "language": "xx"})
    assert seen_voice["voice"] == "en-IN-NeerjaNeural"


def test_provider_failure_falls_back_to_null(client, monkeypatch):
    class _Broken:
        def __init__(self, *a, **k):
            raise RuntimeError("service unavailable")

    monkeypatch.setattr(edge_tts, "Communicate", _Broken)
    res = client.post("/speech/synthesize", json={"text": "Hello", "language": "en"})
    assert res.status_code == 200
    assert res.json()["audio_url"] is None
