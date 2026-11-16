from app.engines import priority, similarity, recommender, escalation


def test_worked_example_from_report():
    score, level, _ = priority.priority_from_factors(S=0.8, U=0.9, N=1.0, D=1.0, R=0.75)
    assert score == 88.0 and level == "Critical"


def test_safety_rule_raises_to_critical():
    score, level, _ = priority.priority_from_factors(0.1, 0.25, 0.04, 0, 0, safety_flag=True)
    assert level == "Critical" and score >= 80


def test_bands():
    assert priority.level_for(79.9) == "High" and priority.level_for(59.9) == "Medium" and priority.level_for(39) == "Low"


def test_related_detection_links_reworded_reports_but_not_unrelated():
    cands = [(1, "Wi-Fi is not working in Block B library, no internet for students"),
             (2, "Tuition payment not reflected on the student portal")]
    hits = similarity.find_related("Internet down in Block B, wifi not working for everyone", cands)
    assert hits and hits[0][0] == 1 and all(h[0] != 2 for h in hits)
    assert similarity.find_related("The canteen food prices are too high", cands) == []


def test_delegate_example_and_exclusions():
    s, _, _ = recommender.score_delegate(categories_handled="ICT / Internet", category_name="ICT / Internet",
                                         open_load=1, max_open_load=5, resolved_similar=6)
    assert s == 86.0
    base = dict(portfolio="", category_name="ICT / Internet", resolved_similar=0)
    ranked = recommender.rank_delegates([
        dict(id=1, name="Full", categories_handled="ICT / Internet", open_load=5, max_open_load=5, is_available=True, **base),
        dict(id=2, name="Away", categories_handled="ICT / Internet", open_load=0, max_open_load=5, is_available=False, **base),
        dict(id=3, name="Free", categories_handled="ICT / Internet", open_load=1, max_open_load=5, is_available=True, **base),
        dict(id=4, name="Other", categories_handled="Security", open_load=0, max_open_load=5, is_available=True, **base)])
    assert [r["delegate_id"] for r in ranked] == [3, 4]


def test_escalation_rules():
    assert escalation.evaluate("High", 5, False, False) is None
    assert escalation.evaluate("High", 13, False, False) == "reminder"
    assert escalation.evaluate("High", 13, True, False) is None
    assert escalation.evaluate("High", 25, True, False) == "escalation"
    assert escalation.evaluate("High", 30, True, True) is None
