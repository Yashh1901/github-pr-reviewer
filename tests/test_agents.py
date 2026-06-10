from agents.supervisor import PRReviewState, build_supervisor_graph


def test_supervisor_graph_builds():
    graph = build_supervisor_graph()
    assert graph is not None

def test_supervisor_graph_runs():
    graph = build_supervisor_graph()
    state = PRReviewState(
        repo="user/repo",
        pr_number=1,
        diff="",
        code_review="",
        security_review="",
        test_review="",
        final_report="",
        human_approved=False,
    )
    result = graph.invoke(state)
    assert result["repo"] == "user/repo"
