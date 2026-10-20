#!/usr/bin/env python3
"""Stand-in for `claude -p` so tests use no plan usage.

Identifies the agent from the system prompt heading and prints a JSON result like
`claude -p --output-format json`. Behaviour switches (env):
  FAKE_CLAUDE_MODE   comma list: limit, error, critique_fail, continuity_error, bad_outline
  FAKE_CLAUDE_STATE  folder for counters and the call log
"""

import json
import os
import random
import re
import sys
from pathlib import Path

WORDS = (
    "lantern iron river oath salt crown ember hollow vow ash glass thorn tide raven silver wolf "
    "ledger bell harbour mist cinder vault blade shrine tower frost garden archive debt warden "
    "scribe envoy hostage map compass needle ink seal ring glove scar candle storm bridge gate "
    "she he they walked waited watched answered lied promised counted measured carried burned "
    "kept broke opened closed turned reached refused offered asked told drew held lifted "
    "slowly quietly sharply carefully again almost only still never always nearly softly "
    "under across beside beyond through against toward before after between within "
    "cold bright narrow heavy bitter quiet small old new red black pale gold green "
    "morning evening winter harvest midnight north south market chapel stable kitchen courtyard"
).split()


def state_dir() -> Path:
    p = Path(os.environ.get("FAKE_CLAUDE_STATE", "/tmp/fake-claude"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def bump(name: str) -> int:
    path = state_dir() / f"{name}.count"
    n = int(path.read_text()) + 1 if path.exists() else 1
    path.write_text(str(n))
    return n


def modes() -> set[str]:
    return set(filter(None, os.environ.get("FAKE_CLAUDE_MODE", "").split(",")))


def prose(words: int, seed: int) -> str:
    rng = random.Random(seed)
    paras, count = [], 0
    while count < words:
        n = min(rng.randint(45, 70), words - count)
        sentence_words = [rng.choice(WORDS) for _ in range(n)]
        text = " ".join(sentence_words)
        paras.append(text[0].upper() + text[1:] + ".")
        count += n
    return "\n\n".join(paras)


def block(name: str, body) -> str:
    if not isinstance(body, str):
        body = json.dumps(body, indent=2)
    return f"=== FILE: {name} ===\n{body}\n=== END FILE ===\n"


def input_block(user: str, label: str) -> str:
    m = re.search(rf"=== INPUT: {re.escape(label)} ===\n(.*?)\n=== END INPUT ===", user, re.DOTALL)
    return m.group(1) if m else ""


def chapter(n: int, target: int, seed: int) -> str:
    body = prose(target - 9, seed).split("\n\n")
    mid = len(body) // 2
    return (f"# Chapter {n}: The {WORDS[n % len(WORDS)].title()} Hour\n\n" + "\n\n".join(body[:mid])
            + "\n\n* * *\n\n" + "\n\n".join(body[mid:]))


def respond(system: str, user: str) -> str:
    m = modes()
    if "# S1 " in system:
        count = int(re.search(r"Propose exactly (\d+)", user).group(1))
        concepts = [{
            "slug": f"concept-{i}", "title": f"The Witness Clause {i}", "premise": "A truth-scribe and a border-lord.",
            "engine": "court", "world_rule": "Oath-Law", "tropes": ["enemies to lovers"], "structure": "one couple per book",
            "books": 3, "heat": "moderate", "darkness": "dark edges",
            "originality": [{"test": t, "pass": True, "note": "ok"} for t in range(1, 9)],
        } for i in range(1, count + 1)]
        out = block("proposals.json", {"concepts": concepts})
        for i in range(1, count + 1):
            out += block(f"concept-{i}.md", f"# The Witness Clause {i}\n\n## Hook\nA scribe, 29, and a lord, 34.")
        return out
    if "# S2 " in system:
        bible = "\n\n".join([
            "# Bible", "## Series overview\nCourt engine.", "## World rules\nOath-Law. Cost: the speaker forgets.",
            "## Places\nThe Archive.", "## Cast\nIssa (29), Corvin (34).", "## Relationship worksheet\n1. ...",
            "## Book arcs\nBook 1...", "## Secret map\nThe seal.", "## Theme\nTruth or mercy?",
            "## Cover style\nInk blue and gold.", "## Glossary\nOath-ink.",
        ])
        series = {"title": "The Witness Clause", "slug": "witness-clause", "engine": "court", "heat": "moderate",
                  "subgenre": "romantasy", "structure": "one couple per book",
                  "books": [{"number": n, "working_title": f"Book {n}", "couple": "Issa and Corvin",
                             "central_question": f"Question {n}?", "hinge": "the seal wakes"} for n in (1, 2, 3)]}
        return block("bible.md", bible) + block("continuity.json", {"facts": [{"id": "F001", "category": "name",
                                                                          "fact": "Issa is 29", "since": "bible"}]}) \
            + block("series.json", series)
    if "# S3 " in system:
        lo = int(re.search(r"in (\d+) to (\d+) chapters", user).group(1))
        if "bad_outline" in m:
            return block("outline.md", "# Outline") + block("outline.json", {"chapters": []})
        chapters = [{"n": i, "title": f"Ch {i}", "pov": "Issa", "goal": "learn", "value_shift": "safe -> exposed",
                     "beats": ["a", "b"], "reader_question_out": "Who sealed it?",
                     "techniques": [1, 26] if i == lo else [1, 9], "target_words": 320} for i in range(1, lo + 1)]
        data = {"title": "The Ink Oath", "logline": "x", "central_question": "Will she testify?",
                "midpoint_chapter": max(1, lo // 2), "chapters": chapters,
                "clues": [{"id": "C01", "clue": "ring", "planted": 1, "payoff": "series"}]}
        return block("outline.md", "# The Ink Oath\n\n## Chapter 1: Ch 1") + block("outline.json", data)
    if "# S4 " in system or "# S6 " in system:
        n = int(re.search(r"(?:Write|Revise) chapter (\d+)", user).group(1))
        target = int(re.search(r"Target length: (\d+) words", user).group(1))
        seed = bump(f"chapter-{n}")
        return block("chapter.md", chapter(n, target, seed * 100 + n)) + block(
            "new-facts.json", {"facts": [{"category": "place", "fact": f"ch{n} detail", "why": "scene"}]})
    if "# S5 " in system:
        n = int(re.search(r"Critique chapter (\d+)", user).group(1))
        k = bump(f"critique-{n}")
        fail = "critique_fail" in m and k == 1 or "critique_always_fail" in m
        score = 2 if fail else 4
        scores = {c: score for c in ("reader_question", "change", "romance_movement", "shown_chemistry",
                                     "character_logic", "stakes_and_cost", "prose")}
        scores["continuity"] = 5
        return block("critique.json", {"scores": scores, "reasons": {}, "reader_question": "Who?",
                                       "techniques_landed": [1], "failure_modes": [], "new_facts_assessment": "ok",
                                       "content_rule_violation": False, "fixes": ["Fix A", "Fix B"]})
    if "# S7 " in system:
        k = bump("continuity")
        errors = []
        if ("continuity_error" in m and k == 1) or "continuity_always" in m:
            errors = [{"id": "E01", "chapter": 2, "severity": "major", "category": "injury", "issue": "hand",
                       "fix": "switch hand"}]
        if "continuity_patch" in m and k == 1:
            heading = re.search(r"^# Chapter 1: .*$", input_block(user, "book.md"), re.MULTILINE).group(0)
            errors = [{"id": "E02", "chapter": 1, "severity": "major", "category": "name", "issue": "title",
                       "fix": "rename", "patches": [{"chapter": 1, "find": heading, "replace": "# Chapter 1: The Patched Hour"}]}]
        if "continuity_minor_always" in m:
            errors = [{"id": "E03", "chapter": 3, "severity": "minor", "category": "timeline", "issue": "which night",
                       "fix": "say Tuesday"}]
        return block("errors.json", {"open_errors": errors}) + block("continuity-report.md", "Checked. None.") \
            + block("new-facts.json", {"facts": [{"category": "place", "fact": "The fort has one gate"}]})
    if "# Book-level checks" in system:
        return block("book-check.json", {"checks": [{"name": "central_question_resolved", "pass": True, "evidence": "ch 3"},
                                                    {"name": "real_loss", "pass": False, "evidence": "none found"}],
                                         "series_threads": [], "summary": "ok"})
    if "# S8 " in system:
        return block("chapter.md", input_block(user, "chapter.md"))
    if "# S9 " in system:
        return block("summary.md", "# The Ink Oath — summary\n\n## Plot\nShe testifies.\n\n## Open threads\n- the ring")
    if "# S10 " in system:
        meta = {"title": "The Ink Oath", "subtitle": "A Romantasy", "series_name": "The Witness Clause",
                "series_number": 1, "pen_name": "Test Pen", "description": "A scribe. A lord. An oath.",
                "keywords": [f"keyword {i}" for i in range(7)],
                "categories": ["Kindle Store > Romance > Fantasy", "Kindle Store > Fantasy > Romantic",
                               "Kindle Store > Romance > Paranormal"],
                "age_notes": "Adult (18+). All characters are adults.", "heat_notes": "moderate",
                "content_notes": "violence", "price_usd": 4.99, "language": "English", "kdp_select": True}
        return block("metadata.json", meta) + block("blurb.md", "<p><b>One oath.</b> Two liars.</p>") \
            + block("cover-prompt.md", "## Art prompt\nInk and gold.") + block("teaser.md", "# Next\nThe seal wakes.") \
            + block("launch-email.md", "Subject: The Ink Oath is out\n\nHi! Read it: {{AMAZON_LINK}}")
    if "# Author bio writer" in system:
        return block("author-bio.json", {"bio_long": "Long bio. " * 40, "bio_short": "Short bio about the books.",
                                         "tagline": "Dangerous love, old magic"})
    if "# Market check" in system:
        concepts = json.loads(input_block(user, "concepts.json") or "[]")
        return block("market-check.json", {"pen_name": {"name": "Test Pen", "verdict": "clear", "evidence": []},
                                           "concepts": [{"n": c["n"], "title": c["title"], "title_collision": "none",
                                                         "premise_collision": "none", "evidence": [], "verdict": "clear",
                                                         "clear_titles": []} for c in concepts],
                                           "limits": "fake"})
    if "# Concept selector" in system:
        return block("selection.json", {"pick": 2, "scores": [], "why": "Strongest hook.", "owner_watch": "x"})
    if "# Beta reader" in system:
        k = bump("beta")
        verdict = "revise" if ("beta_revise" in m or "beta_always_revise" in m) and (k == 1 or "beta_always_revise" in m) else "approve"
        return block("verdict.json", {"verdict": verdict, "predicted_rating": 4.2, "summary": "Good."}) \
            + block("beta-notes.md", "## Keep\n- banter\n## Fix\n1. Chapter 1: fewer smirks.\n## Blurb\nok")
    if "# Reader magnet writer" in system:
        return block("bonus.md", "# The Night He Chose\n\n*A Witness Clause bonus story*\n\n" + prose(200, 7)) \
            + block("bonus-meta.json", {"title": "The Night He Chose", "pitch": "Corvin's side of the trial.", "words": 200})
    if "# Owner notes planner" in system:
        return block("plan.json", {"chapters": [{"n": 1, "instructions": ["Cut the smirks"]}], "notes_not_actioned": []})
    return "unrecognised agent"


def main() -> int:
    args = sys.argv[1:]
    tools_flag = args[args.index("--tools") + 1] if "--tools" in args else None
    flag = "--system-prompt" if "--system-prompt" in args else "--append-system-prompt"
    system = args[args.index(flag) + 1] if flag in args else ""
    model = args[args.index("--model") + 1] if "--model" in args else ""
    user = sys.stdin.read()
    with (state_dir() / "calls.log").open("a") as fh:
        fh.write(json.dumps({"model": model, "system_head": system.splitlines()[0] if system else "",
                             "api_key_seen": bool(os.environ.get("ANTHROPIC_API_KEY")), "tools": tools_flag,
                             "allowed": args[args.index("--allowedTools") + 1] if "--allowedTools" in args else None}) + "\n")
    m = modes()
    if "limit" in m:
        print(json.dumps({"type": "result", "is_error": True, "result": "Claude usage limit reached. Your limit will reset at 5am."}))
        return 1
    if "error" in m:
        print("boom", file=sys.stderr)
        return 1
    text = respond(system, user)
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text,
                      "duration_ms": 10, "num_turns": 1, "total_cost_usd": 0.01,
                      "usage": {"input_tokens": len(user) // 4, "output_tokens": len(text) // 4,
                                "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
