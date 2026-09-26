from aethon.ai_factory import AIAgentSpec, AIFactory, FactoryStage


def test_ai_factory_lifecycle_and_repair():
    factory = AIFactory(
        generator=lambda spec: {"agent.json": spec.goal},
        evaluator=lambda agent: {"passed": not agent.spec.name.startswith("bad")},
    )
    agent = factory.specify(AIAgentSpec("weather", "Monitor weather", capabilities=("research",)))
    factory.generate(agent.agent_id)
    factory.sandbox(agent.agent_id)
    factory.evaluate(agent.agent_id)
    factory.approve(agent.agent_id)
    factory.deploy(agent.agent_id)
    assert agent.stage is FactoryStage.DEPLOYED


def test_ai_factory_failed_evaluation_can_repair():
    factory = AIFactory(
        generator=lambda spec: {"main.py": "v1"},
        evaluator=lambda agent: {"passed": False},
    )
    agent = factory.specify(AIAgentSpec("bad", "test"))
    factory.generate(agent.agent_id)
    factory.sandbox(agent.agent_id)
    factory.evaluate(agent.agent_id)
    assert agent.stage is FactoryStage.REPAIR_REQUIRED
    factory.repair(agent.agent_id, {"main.py": "v2"})
    assert agent.version == 2
    assert agent.stage is FactoryStage.GENERATED
