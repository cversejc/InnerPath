from app.domains.workflow.authorization import has_collaboration_contract


def test_collaborative_assignment_mode_requires_a_saved_contract():
    assert has_collaboration_contract({"collaboration_contract": {"version": 1}})
    assert not has_collaboration_contract(None)
    assert not has_collaboration_contract({})
    assert not has_collaboration_contract({"collaboration_contract": None})
