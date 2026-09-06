from aethon.schemas import ToolRequest
from aethon.tools import ToolRegistry
from aethon.web import WebPolicyError, validate_public_url


class FakeSearch:
    def search(self, query, limit):
        assert query == 'aethon'
        return [type('R', (), {'title': 'AETHON', 'url': 'https://example.com', 'snippet': 'test', 'source': 'fake'})()]


class FakeFetch:
    def fetch(self, url):
        assert url == 'https://example.com'
        return {'url': url, 'status_code': 200, 'content_type': 'text/html', 'text': 'ok'}


def test_registry_exposes_web_tools():
    names = {spec.name for spec in ToolRegistry().list()}
    assert {'calculator', 'web_search', 'web_fetch'} <= names


def test_web_search_execution_is_structured():
    result = ToolRegistry(web_search=FakeSearch()).execute(ToolRequest(tool='web_search', arguments={'query': 'aethon'}))
    assert result.ok is True
    assert result.output[0]['url'] == 'https://example.com'
    assert result.output[0]['source'] == 'fake'


def test_web_fetch_execution_is_structured():
    result = ToolRegistry(web_fetch=FakeFetch()).execute(ToolRequest(tool='web_fetch', arguments={'url': 'https://example.com'}))
    assert result.ok is True
    assert result.output['status_code'] == 200


def test_private_ip_url_is_blocked():
    import aethon.web as web
    original = web.socket.getaddrinfo
    try:
        web.socket.getaddrinfo = lambda *args, **kwargs: [(None, None, None, None, ('127.0.0.1', 0))]
        try:
            validate_public_url('http://localhost')
            assert False, 'expected WebPolicyError'
        except WebPolicyError:
            pass
    finally:
        web.socket.getaddrinfo = original


def test_non_http_scheme_is_blocked():
    try:
        validate_public_url('file:///etc/passwd')
        assert False, 'expected WebPolicyError'
    except WebPolicyError:
        pass
