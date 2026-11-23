"""Regression checks for scoring errors that can silently approve a bad release."""

import copy
from suite import retrieval_scores, answer_scores
from gate import gate


def test_duplicate_chunks_cannot_inflate_ndcg():
    r = {"source": "a", "section": "s", "page": 1}
    m = retrieval_scores([r], [r, r, r])
    assert m["ndcg_at_5"] == 1 and m["recall_at_3"] == 1 and m["mrr"] == 1


def test_right_retrieval_wrong_final_citation():
    target = {"source": "lab", "section": "s", "page": 1}
    other = {"source": "handbook", "section": "s", "page": 1}
    q = {"relevant": [target], "expect": "LAB-5"}
    response = {
        "answered_from_context": True,
        "answer": "Use LAB-5",
        "citations": [other],
        "retrieved": [dict(target, chunk_id="correct"), dict(other, chunk_id="wrong")],
    }
    assert retrieval_scores(q["relevant"], response["retrieved"])["recall_at_5"] == 1
    m = answer_scores(
        q, response, {"correct": "Use LAB-5", "wrong": "Use the handbook"}
    )
    assert m["citation_validity"] == 1
    assert m["citation_ground_truth"] == 0 and m["faithfulness"] == 0


def test_gate_missing_nan_and_regression_fail_closed():
    baseline = {"golden_sha256": "a", "component": {"recall_at_5": 0.8}}
    thresholds = {"component.recall_at_5": {"max_drop": 0.02}}
    for value in (None, float("nan"), 0.77):
        c = copy.deepcopy(baseline)
        c["component"]["recall_at_5"] = value
        assert gate(baseline, c, thresholds)
    assert not gate(baseline, baseline, thresholds)


def test_calculated_total_requires_correct_answer_and_cited_operands():
    from fact_rubrics import fact_checks

    evidence = "Tuition per credit hour 12,000. Activities fund 2,500 per semester."
    good = fact_checks("H8", "180,000 tuition plus 2,500 totals Rs 182,500.", evidence)
    assert all(good["answer_facts"] + good["evidence_facts"])
    wrong = fact_checks("H8", "180,000 tuition plus 2,500 totals Rs 185,000.", evidence)
    assert not all(wrong["answer_facts"])
    missing = fact_checks(
        "H8", "180,000 tuition plus 2,500 totals Rs 182,500.", "12,000 per credit hour"
    )
    assert not all(missing["evidence_facts"])


def test_refund_rubric_requires_conditions_not_just_amount():
    from fact_rubrics import fact_checks

    result = fact_checks(
        "q22",
        "Rs 20,000.",
        "20,000 refundable on degree completion or closing admission",
    )
    assert not all(result["answer_facts"])
    result = fact_checks(
        "q22",
        "Rs 20,000 on degree completion or admission closure.",
        "20,000 refundable on degree completion or closing admission",
    )
    assert all(result["answer_facts"] + result["evidence_facts"])
