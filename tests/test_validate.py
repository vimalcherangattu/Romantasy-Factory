import pytest

from factory import parse, validate


def test_file_blocks_parse():
    text = "intro\n=== FILE: a.md ===\nhello\n=== END FILE ===\n=== FILE: b.json ===\n{\"x\": 1}\n=== END FILE ===\n"
    files = parse.require_files(text, ["a.md", "b.json"])
    assert files["a.md"].strip() == "hello"
    assert parse.json_text(files["b.json"]) == {"x": 1}


def test_missing_block_is_output_error():
    with pytest.raises(parse.OutputError):
        parse.require_files("nothing", ["a.md"])


def test_json_in_fence():
    assert parse.json_text("```json\n{\"a\": 2}\n```") == {"a": 2}


def test_style_lists_load_from_canon(cfg):
    banned, tells = validate.style_lists(cfg)
    assert "a testament to" in banned
    assert "couldn't help but" in tells


def test_style_report_counts(cfg):
    text = "# Chapter 1: X\n\nIt was a testament to her nerve. She couldn't help but smile. " * 2
    rep = validate.style_report(cfg, text)
    assert rep["banned_hits"]["a testament to"] == 2
    assert validate.style_problems(cfg, rep)


def _scores(v, cont=5):
    s = {c: v for c in ("reader_question", "change", "romance_movement", "shown_chemistry",
                        "character_logic", "stakes_and_cost", "prose")}
    s["continuity"] = cont
    return s


def test_critique_pass_rules(cfg):
    assert validate.critique(cfg, {"scores": _scores(4)})["passed"]
    # average >= 3.5 but one criterion below 3 fails
    s = _scores(4)
    s["prose"] = 2
    assert not validate.critique(cfg, {"scores": s})["passed"]
    # continuity 0 fails
    assert not validate.critique(cfg, {"scores": _scores(5, cont=0)})["passed"]
    # content rule violation fails regardless
    assert not validate.critique(cfg, {"scores": _scores(5), "content_rule_violation": True})["passed"]


def test_critique_rejects_bad_continuity_score(cfg):
    with pytest.raises(parse.OutputError):
        validate.critique(cfg, {"scores": _scores(4, cont=3)})


def test_chapter_length_window(cfg):
    good = "# Chapter 2: T\n\n" + "word " * 300
    assert validate.chapter_draft(cfg, good, 2, 300) == []
    short = "# Chapter 2: T\n\n" + "word " * 100
    assert any("words" in e for e in validate.chapter_draft(cfg, short, 2, 300))
    assert validate.chapter_draft(cfg, "no heading " * 300, 2, 300)


def test_outline_requires_fields(cfg):
    chapters = [{"n": i, "pov": "a", "goal": "b", "value_shift": "c", "reader_question_out": "d",
                 "techniques": [1, 26] if i == 3 else [1]} for i in (1, 2, 3)]
    ok = {"title": "T", "central_question": "Q", "midpoint_chapter": 2, "chapters": chapters}
    assert validate.outline(cfg, ok) == []
    chapters[1].pop("pov")
    assert any("pov" in e for e in validate.outline(cfg, ok))


def test_proposals_need_all_tests_passing():
    concept = {"slug": "s", "title": "t", "premise": "p", "books": 3,
               "originality": [{"test": i, "pass": i != 4} for i in range(1, 9)]}
    errors = validate.proposals({"concepts": [concept]}, 1)
    assert any("fails originality tests [4]" in e for e in errors)
