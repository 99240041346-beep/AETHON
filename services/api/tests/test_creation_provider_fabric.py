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
