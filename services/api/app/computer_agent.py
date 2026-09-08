from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

class ComputerActionType(str, Enum):
    MOVE='move'; CLICK='click'; DOUBLE_CLICK='double_click'; TYPE='type'; KEY='key'; SCROLL='scroll'; WAIT='wait'; SCREENSHOT='screenshot'
class ComputerSecurityError(ValueError): pass
@dataclass(frozen=True)
class Screen:
    width:int; height:int; title:str=''; text:str=''
@dataclass(frozen=True)
class ComputerAction:
    action:ComputerActionType; x:int=0; y:int=0; value:str=''; requires_approval:bool=False
@dataclass(frozen=True)
class ComputerResult:
    action:ComputerAction; success:bool; message:str=''
class ComputerAdapter(Protocol):
    def execute(self, action:ComputerAction)->ComputerResult: ...
class BoundedComputerAgent:
    """Provider-neutral local-computer policy boundary with bounded coordinates and actions."""
    def __init__(self, *, max_actions:int=32, max_text:int=12000, max_width:int=10000, max_height:int=10000)->None:
        if not 1<=max_actions<=64 or not 1<=max_text<=20000 or not 1<=max_width<=10000 or not 1<=max_height<=10000: raise ValueError('invalid computer bounds')
        self.max_actions,self.max_text,self.max_width,self.max_height=max_actions,max_text,max_width,max_height
    def normalize_screen(self, screen:Screen)->Screen:
        if not 1<=screen.width<=self.max_width or not 1<=screen.height<=self.max_height: raise ComputerSecurityError('screen dimensions exceed bounds')
        return Screen(screen.width,screen.height,screen.title.strip()[:500],screen.text.strip()[:self.max_text])
    def validate_actions(self, actions:Iterable[ComputerAction], screen:Screen)->tuple[ComputerAction,...]:
        screen=self.normalize_screen(screen); values=tuple(actions)
        if len(values)>self.max_actions: raise ComputerSecurityError('computer action budget exceeded')
        for a in values:
            if not isinstance(a.action,ComputerActionType): raise ComputerSecurityError('unsupported computer action')
            if not 0<=a.x<screen.width or not 0<=a.y<screen.height: raise ComputerSecurityError('screen coordinate outside bounds')
            if len(a.value)>4000: raise ComputerSecurityError('computer action payload exceeds bounds')
        return values
    def plan(self, screen:Screen, goal:str)->tuple[ComputerAction,...]:
        self.normalize_screen(screen)
        if not goal.strip(): raise ComputerSecurityError('computer goal is required')
        return (ComputerAction(ComputerActionType.SCREENSHOT),)
    def execute(self, actions:Iterable[ComputerAction], screen:Screen, adapter:ComputerAdapter, *, approve:bool=False)->tuple[ComputerResult,...]:
        results=[]
        for action in self.validate_actions(actions,screen):
            if action.requires_approval and not approve: results.append(ComputerResult(action,False,'approval required')); continue
            result=adapter.execute(action); results.append(result)
            if not result.success: break
        return tuple(results)
__all__=['BoundedComputerAgent','ComputerAction','ComputerActionType','ComputerAdapter','ComputerResult','ComputerSecurityError','Screen']
