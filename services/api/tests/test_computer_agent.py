import pytest
from app.computer_agent import *
class A:
 def execute(self,a): return ComputerResult(a,True,'ok')
def test_screen_bounds_and_text():
 a=BoundedComputerAgent(max_text=5); s=a.normalize_screen(Screen(100,100,' T ','123456')); assert s.text=='12345' and s.title=='T'
 with pytest.raises(ComputerSecurityError): a.normalize_screen(Screen(0,100))
def test_coordinates_and_budget():
 a=BoundedComputerAgent(max_actions=1); s=Screen(100,100)
 with pytest.raises(ComputerSecurityError): a.validate_actions([ComputerAction(ComputerActionType.CLICK,100,1)],s)
 with pytest.raises(ComputerSecurityError): a.validate_actions([ComputerAction(ComputerActionType.WAIT),ComputerAction(ComputerActionType.WAIT)],s)
def test_approval_and_failure_stop():
 a=BoundedComputerAgent(); s=Screen(100,100); x=ComputerAction(ComputerActionType.CLICK,1,1,requires_approval=True); assert not a.execute([x],s,A())[0].success
 class F:
  def execute(self,a): return ComputerResult(a,False,'failed')
 assert len(a.execute([ComputerAction(ComputerActionType.WAIT),ComputerAction(ComputerActionType.WAIT)],s,F()))==1
def test_empty_goal():
 with pytest.raises(ComputerSecurityError): BoundedComputerAgent().plan(Screen(100,100),'')
