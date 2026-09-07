from aethon.task_graph import TaskGraphPlanner


def test_graph_respects_dependencies_and_ready_nodes():
    graph = TaskGraphPlanner().build(
        ["research", "draft", "review"],
        {"draft": ["research"], "review": ["draft"]},
    )
    assert [node.id for node in graph.ready(set())] == ["task-1"]
    assert [node.id for node in graph.ready({"task-1"})] == ["task-2"]


def test_graph_is_bounded_and_deduplicated():
    graph = TaskGraphPlanner(max_nodes=2).build(["A", "a", "B", "C"])
    assert len(graph.nodes) == 2
    assert [node.goal for node in graph.nodes] == ["A", "B"]


def test_invalid_bound_rejected():
    try:
        TaskGraphPlanner(max_nodes=0)
        assert False
    except ValueError:
        pass
