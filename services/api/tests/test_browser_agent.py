import pytest
from app.browser_agent import BrowserAction, BrowserActionType, BrowserPage, BrowserResult, BrowserSecurityError, BoundedBrowserAgent

class Adapter:
    def execute(self, action): return BrowserResult(action, True, 'ok')

def test_url_domain_and_page_bounds():
    a=BoundedBrowserAgent(max_page_text=5, allowed_domains=['example.com'])
    p=a.normalize_page(BrowserPage('https://example.com/x', ' title ', '123456', ('https://example.com/a',)))
    assert p.text=='12345' and p.title=='title'
    with pytest.raises(BrowserSecurityError): a.validate_url('https://evil.example.net')

def test_action_budget_and_approval():
    a=BoundedBrowserAgent(max_actions=1)
    action=BrowserAction(BrowserActionType.CLICK,'#buy',requires_approval=True)
    result=a.execute([action], Adapter())
    assert result[0].success is False and result[0].message=='approval required'
    with pytest.raises(BrowserSecurityError): a.validate_actions([BrowserAction(BrowserActionType.WAIT), BrowserAction(BrowserActionType.BACK)])

def test_failure_stops_execution():
    class F:
        def execute(self, action): return BrowserResult(action, False, 'failed')
    a=BoundedBrowserAgent()
    result=a.execute([BrowserAction(BrowserActionType.OPEN,'https://example.com'), BrowserAction(BrowserActionType.CLICK,'#x')], F())
    assert len(result)==1 and not result[0].success

def test_empty_goal_rejected():
    with pytest.raises(BrowserSecurityError): BoundedBrowserAgent().plan(BrowserPage('https://example.com'), ' ')
