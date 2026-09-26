from aethon.creation_provider_fabric import CreationProviderFabric


def test_provider_capability_listing():
    fabric = CreationProviderFabric({
        "higgsfield": {"base_url": "https://example.test", "api_key": "x"},
        "vercel": {"base_url": "https://example.test", "api_key": "x"},
    })
    rows = {item.id: item.capabilities for item in fabric.list()}
    assert "video" in rows["higgsfield"]
    assert "website" in rows["vercel"]


def test_code_has_no_external_creation_fallback():
    fabric = CreationProviderFabric({})
    try:
        fabric.dispatch("code", {"prompt": "hello"})
    except RuntimeError as exc:
        assert "AI provider fabric" in str(exc)
    else:
        raise AssertionError("expected explicit code-provider error")


def test_native_higgsfield_video_uses_key_credentials(monkeypatch):
    from aethon.creation_provider_fabric import CreationProviderFabric
    class Response:
        status_code = 200
        content = b'{"request_id":"req-123","status":"queued"}'
        def json(self): return {"request_id":"req-123","status":"queued"}
    captured = {}
    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return Response()
    monkeypatch.setattr("aethon.creation_provider_fabric.httpx.post", fake_post)
    fabric = CreationProviderFabric({"higgsfield": {"base_url": "https://api.higgsfield.ai", "api_key_id": "id", "api_key_secret": "secret", "model": "bytedance/seedance-2.0/text-to-video", "native": True}})
    result = fabric.dispatch("video", {"prompt": "a cinematic project trailer"})
    assert result.status == "queued"
    assert result.output["request_id"] == "req-123"
    assert captured["headers"]["Authorization"] == "Key id:secret"
    assert captured["json"]["duration"] == 5
