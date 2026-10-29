from kt_movemacc.terminal_convergence import TerminalConvergenceVerifier

def test_terminal_convergence_scopes():
    verifier = TerminalConvergenceVerifier()
    
    # TASK scope success
    ev = verifier.evaluate_scope("TASK", "KTMA_NTV_005", {
        "tests_passed": True,
        "outputs_verified": True,
        "dependencies_reconciled": True,
        "no_unauthorized_mutations": True
    })
    assert ev.converged is True

    # GOAL scope blocked by human approval
    ev_goal = verifier.evaluate_scope("GOAL", "SAFE_CORE_QA", {
        "tests_passed": True,
        "outputs_verified": True,
        "dependencies_reconciled": True,
        "no_unauthorized_mutations": True,
        "human_approved": False
    })
    assert ev_goal.converged is False
    assert "human approval gate is open" in ev_goal.reasons[0]
