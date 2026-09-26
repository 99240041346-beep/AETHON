from aethon.action_policy import ActionPolicy


def test_read_actions_do_not_require_confirmation():
    assert ActionPolicy.classify("web_search", {"query": "test"}).requires_confirmation is False
    assert ActionPolicy.classify("SCREEN_READ").requires_confirmation is False


def test_external_actions_require_confirmation():
    assert ActionPolicy.classify("SCREEN_CLICK", {"text": "Send"}).requires_confirmation is True
    assert ActionPolicy.classify("OPEN_APP", {"package_name": "com.android.settings"}).requires_confirmation is True


def test_urls_and_unknown_actions_fail_closed():
    assert ActionPolicy.validate_url("https://example.com/path")
    for value in ("example.com", "ftp://example.com", ""):
        try:
            ActionPolicy.validate_url(value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid URL accepted")
    try:
        ActionPolicy.classify("delete_everything")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown action accepted")
