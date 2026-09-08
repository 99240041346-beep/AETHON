import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_candidate_count_limit_is_hard():
    candidates = [ModelCandidate(f"m{i}") for i in range(4)]
    with pytest.raises(ModelRoutingError):
        ModelRouter(candidates, max_candidates=3)
