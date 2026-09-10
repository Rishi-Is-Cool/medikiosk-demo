"""Adaptive kiosk interview: question count, memory, red flags, language."""
from app.ai import adaptive_engine as engine
from app.utils.identity import mask_aadhaar, mask_abha, normalize_aadhaar, normalize_abha


def _run(complaints, framework="general_medicine", answers=None):
    """Answer every question with its default; return the ids asked in order."""
    answers = dict(answers or {})
    asked = []
    for _ in range(80):
        ctx = engine.build_context(complaints, framework, answers)
        question, _steps = engine.next_question(ctx)
        if question is None:
            return asked, ctx
        asked.append(question.id)
        answers.setdefault(question.id, engine.default_answer(question, ctx))
    raise AssertionError("interview did not terminate")


def test_interviews_stay_short():
    assert len(_run(["chest_pain"])[0]) <= 10
    assert len(_run(["fever"])[0]) <= 10
    # Several complaints share the duration/severity/associated questions rather than repeating them.
    asked, _ = _run(["chest_pain", "headache", "fever"])
    assert len(asked) <= 12
    assert asked.count("duration") == 1 and asked.count("severity") == 1


def test_no_question_is_asked_twice():
    for complaints in (["chest_pain"], ["headache", "fever"], ["abdominal_pain", "vomiting_diarrhoea"], ["other"]):
        asked, _ = _run(complaints)
        assert len(asked) == len(set(asked)), complaints


def test_ayush_includes_prakriti_questions():
    asked, _ = _run(["joint_back_pain"], framework="ayush")
    assert "ayush_q2_prakriti" in asked


def test_follow_up_questions_depend_on_answers():
    ctx = engine.build_context(["breathlessness"], "general_medicine", {"sob_when": {"values": ["rest"], "text": None}})
    asked, _ = _run(["breathlessness"], answers={"sob_when": {"values": ["rest"], "text": None}})
    assert "sob_speech" in asked
    asked, _ = _run(["breathlessness"], answers={"sob_when": {"values": ["exertion"], "text": None}})
    assert "sob_speech" not in asked
    assert ctx.findings  # structured findings drive the branching


def test_red_flags_are_cumulative_across_answers():
    answers = {"cp_character": {"values": ["pressing"], "text": None}}
    assert not engine.evaluate_red_flags(engine.build_context(["chest_pain"], "general_medicine", answers).findings)
    answers["cp_radiation"] = {"values": ["left_arm"], "text": None}
    rules = [f["rule"] for f in engine.evaluate_red_flags(engine.build_context(["chest_pain"], "general_medicine", answers).findings)]
    assert rules[0] == "ACS_SUSPECTED"


def test_benign_answers_raise_no_flag():
    _, ctx = _run(["joint_back_pain"])
    assert engine.evaluate_red_flags(ctx.findings) == []


def test_spoken_text_maps_to_findings_with_negation():
    assert "cp_radiates" in engine.text_findings("pain going to my left arm")
    assert not engine.text_findings("no chest pain and no sweating")


def test_spoken_answer_matches_options():
    ctx = engine.build_context(["chest_pain"], "general_medicine", {})
    duration = engine.ALL_QUESTIONS["duration"]
    assert engine.match_options(duration, ctx, "since 3 days") == ["d1_3"]
    assert engine.match_options(duration, ctx, "two weeks") == ["w1_4"]
    assert engine.match_options(duration, ctx, "दो हफ़्ते से") == ["w1_4"]


def test_complaint_matching_finds_several():
    assert engine.match_complaints("chest pain and fever since morning") == ["chest_pain", "fever"]
    assert engine.normalize_complaints(["fever_cough"]) == ["fever", "cough_cold"]


def test_render_is_localised():
    ctx = engine.build_context(["chest_pain"], "general_medicine", {})
    question, steps = engine.next_question(ctx)
    rendered = engine.render(question, ctx, steps, "mr")
    assert rendered["question_id"] == "duration"
    assert rendered["text"] != engine.render(question, ctx, steps, "en")["text"]
    assert rendered["progress"]["current"] == 1


def test_identity_normalisation_and_masking():
    assert normalize_abha("91 7267 4417 6579") == "91-7267-4417-6579"
    assert normalize_abha("123") is None
    assert normalize_aadhaar("2345-6789-0123") == "234567890123"
    assert mask_abha("91-7267-4417-6579") == "XX-XXXX-XXXX-6579"
    assert mask_aadhaar("0123") == "XXXX XXXX 0123"
