from __future__ import annotations

from threading import RLock

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.ai_factory import AIAgentSpec, AIFactory
from aethon.auth import current_owner, security
from aethon.model_router import ModelRouter

router = APIRouter(prefix="/v1/ai-factory", tags=["ai-factory"])
_lock = RLock()
_factories: dict[str, AIFactory] = {}


class CreateAgentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=4000)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    tools: list[str] = Field(default_factory=list, max_length=32)
    model: str = Field(default="provider-default", max_length=120)
    constraints: list[str] = Field(default_factory=list, max_length=32)
    evaluation_cases: list[str] = Field(default_factory=list, max_length=128)


class RepairRequest(BaseModel):
    model_config = {"extra": "forbid"}
    artifacts: dict[str, str]


def _owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _factory(owner_id: str) -> AIFactory:
    with _lock:
        if owner_id not in _factories:
            router_model = ModelRouter()

            def generator(spec: AIAgentSpec) -> dict[str, str]:
                prompt = (
                    "Design a bounded AI agent. Return a concise implementation artifact, "
                    "not executable deployment commands. Include purpose, inputs, outputs, "
                    "tools, safety constraints, evaluation strategy, and pseudocode.\n"
                    f"Name: {spec.name}\nGoal: {spec.goal}\n"
                    f"Capabilities: {', '.join(spec.capabilities)}\n"
                    f"Tools: {', '.join(spec.tools)}\n"
                    f"Constraints: {', '.join(spec.constraints)}"
                )
                return {"agent_spec.md": router_model.generate(prompt, user_text=spec.goal)}

            def evaluator(agent) -> dict:
                artifact = agent.artifacts.get("agent_spec.md", "")
                passed = bool(artifact.strip()) and len(artifact) <= AIFactory.MAX_ARTIFACT_CHARS
                return {"passed": passed, "checks": ["artifact_present", "artifact_bounded"], "version": agent.version}

            _factories[owner_id] = AIFactory(generator=generator, evaluator=evaluator)
        return _factories[owner_id]


def _serialize(agent) -> dict:
    return {
        "agent_id": agent.agent_id,
        "spec": {
            "name": agent.spec.name, "goal": agent.spec.goal,
            "capabilities": list(agent.spec.capabilities), "tools": list(agent.spec.tools),
            "model": agent.spec.model, "constraints": list(agent.spec.constraints),
            "evaluation_cases": list(agent.spec.evaluation_cases),
        },
        "stage": agent.stage,
        "version": agent.version,
        "artifacts": agent.artifacts,
        "evaluation": agent.evaluation,
        "repair_count": agent.repair_count,
    }


@router.get("")
def list_agents(owner_id: str = Depends(_owner)):
    factory = _factory(owner_id)
    return {"ok": True, "agents": [_serialize(x) for x in factory.agents.values()]}


@router.post("")
def create_agent(request: CreateAgentRequest, owner_id: str = Depends(_owner)):
    try:
        agent = _factory(owner_id).specify(AIAgentSpec(
            name=request.name.strip(), goal=request.goal.strip(),
            capabilities=tuple(x.strip() for x in request.capabilities if x.strip()),
            tools=tuple(x.strip() for x in request.tools if x.strip()),
            model=request.model.strip() or "provider-default",
            constraints=tuple(x.strip() for x in request.constraints if x.strip()),
            evaluation_cases=tuple(x.strip() for x in request.evaluation_cases if x.strip()),
        ))
        return {"ok": True, "agent": _serialize(agent)}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/generate")
def generate(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).generate(agent_id))}
    except (KeyError, ValueError, RuntimeError) as exc: raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/sandbox")
def sandbox(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).sandbox(agent_id))}
    except (KeyError, ValueError) as exc: raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/evaluate")
def evaluate(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).evaluate(agent_id))}
    except (KeyError, ValueError, RuntimeError) as exc: raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/approve")
def approve(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).approve(agent_id))}
    except (KeyError, ValueError) as exc: raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/deploy")
def deploy(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).deploy(agent_id))}
    except (KeyError, ValueError) as exc: raise HTTPException(400, str(exc)) from exc


@router.post("/{agent_id}/pause")
def pause(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id).pause(agent_id))}
    except (KeyError, ValueError) as exc: raise HTTPException(400, str(exc)) from exc


@router.get("/{agent_id}")
def get_agent(agent_id: str, owner_id: str = Depends(_owner)):
    try: return {"ok": True, "agent": _serialize(_factory(owner_id)._get(agent_id))}
    except KeyError as exc: raise HTTPException(404, str(exc)) from exc
