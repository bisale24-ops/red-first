

def test_the_whole_suite_notice_leads_and_states_what_changes():
    """Without coverage contexts, UNREACHED cannot be told from UNGUARDED - so say so first."""
    from redfirst import report
    text = report.render([], whole_suite=True)
    first = text.splitlines()[0]
    assert "coverage contexts were unavailable" in first
    assert "UNREACHED" in text and "cannot be" in text
    assert "same verdicts" not in text
