from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol
from urllib.parse import urlparse

class BrowserActionType(str, Enum):
    OPEN='open'; CLICK='click'; TYPE='type'; SELECT='select'; SCROLL='scroll'; BACK='back'; WAIT='wait'

class BrowserSecurityError(ValueError): pass

@dataclass(frozen=True)
class BrowserPage:
    url: str
    title: str = ''
    text: str = ''
    links: tuple[str, ...] = ()

@dataclass(frozen=True)
class BrowserAction:
    action: BrowserActionType
    target: str = ''
    value: str = ''
    requires_approval: bool = False

@dataclass(frozen=True)
class BrowserResult:
    action: BrowserAction
    success: bool
    message: str = ''

class BrowserAdapter(Protocol):
    def execute(self, action: BrowserAction) -> BrowserResult: ...

class BoundedBrowserAgent:
    """Provider-neutral browser policy boundary with bounded navigation and execution."""
    _SCHEMES = {'http','https'}
    def __init__(self, *, max_actions: int = 32, max_page_text: int = 12000, allowed_domains: Iterable[str] = ()) -> None:
        if not 1 <= max_actions <= 64 or not 1 <= max_page_text <= 20000: raise ValueError('invalid browser bounds')
        self.max_actions, self.max_page_text = max_actions, max_page_text
        self.allowed_domains = frozenset(d.strip().lower().lstrip('.') for d in allowed_domains if d.strip())

    def validate_url(self, url: str) -> str:
        value=url.strip(); p=urlparse(value); host=(p.hostname or '').lower()
        if p.scheme.lower() not in self._SCHEMES or not host: raise BrowserSecurityError('only http and https URLs with hosts are allowed')
        if self.allowed_domains and not any(host == d or host.endswith('.'+d) for d in self.allowed_domains): raise BrowserSecurityError('URL host is outside allowed domain policy')
        return value

    def normalize_page(self, page: BrowserPage) -> BrowserPage:
        return BrowserPage(self.validate_url(page.url), page.title.strip()[:500], page.text.strip()[:self.max_page_text], tuple(self.validate_url(x) for x in page.links[:128]))

    def validate_actions(self, actions: Iterable[BrowserAction]) -> tuple[BrowserAction, ...]:
        values=tuple(actions)
        if len(values)>self.max_actions: raise BrowserSecurityError('browser action budget exceeded')
        for a in values:
            if not isinstance(a.action, BrowserActionType): raise BrowserSecurityError('unsupported browser action')
            if len(a.target)>1000 or len(a.value)>4000: raise BrowserSecurityError('browser action payload exceeds bounds')
        return values

    def plan(self, page: BrowserPage, goal: str) -> tuple[BrowserAction, ...]:
        self.normalize_page(page)
        if not goal.strip(): raise BrowserSecurityError('browser goal is required')
        return (BrowserAction(BrowserActionType.OPEN, page.url),)

    def execute(self, actions: Iterable[BrowserAction], adapter: BrowserAdapter, *, approve: bool = False) -> tuple[BrowserResult, ...]:
        results=[]
        for action in self.validate_actions(actions):
            if action.requires_approval and not approve:
                results.append(BrowserResult(action, False, 'approval required')); continue
            result=adapter.execute(action); results.append(result)
            if not result.success: break
        return tuple(results)

__all__=['BrowserAction','BrowserActionType','BrowserAdapter','BrowserPage','BrowserResult','BrowserSecurityError','BoundedBrowserAgent']
