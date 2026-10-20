import json

from PIL import Image

from factory import orchestrator, package, prompts, schedule, state


def test_cover_typesetting(cfg, tmp_path):
    art = tmp_path / "art.png"
    Image.new("RGB", (1024, 1536), (40, 60, 90)).save(art)
    out = package.typeset_cover(cfg, art, tmp_path / "cover.jpg", "The Ink Oath", "Test Pen")
    img = Image.open(out)
    assert img.size == (1600, 2560)


def test_epub_contains_front_and_back_matter(cfg, approved_series):
    orchestrator.run(cfg, book_id=f"{approved_series}-b01", echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    md = (cfg.paths.book_dir(approved_series, b["book_id"]) / "package" / "book.md").read_text()
    assert "Copyright ©" in md and "Test Pen" in md
    assert "Also by Test Pen" in md and "Coming next" in md
    assert b["package"]["docx_headings"] in (True, None)
    assert b["package"]["epubcheck"] in (True, None), b["package"]  # None only where epubcheck isn't installed
    assert "scene-break" in md


def test_upload_checklist_lists_fields(cfg, approved_series):
    orchestrator.run(cfg, book_id=f"{approved_series}-b01", echo=lambda *_: None)
    b = state.load_book(cfg, f"{approved_series}-b01")
    text = (cfg.paths.book_dir(approved_series, b["book_id"]) / "package" / "upload-checklist.md").read_text()
    assert "Keyword 7" in text and "Stop before Publish" in text and "factory published" in text


def test_every_agent_loads_content_rules_and_style_guide(cfg):
    for path in cfg.paths.agents.glob("*.md"):
        if path.name.startswith("_"):
            continue
        sp = prompts.system_prompt(cfg, path.stem)
        assert 'canon/content-rules.md' in sp and 'canon/style-guide.md' in sp, path.name


def test_canon_files_under_3000_words(cfg):
    for path in cfg.paths.canon.glob("*.md"):
        assert len(path.read_text().split()) < 3000, path.name


def test_launchd_plist(cfg):
    text = schedule.plist(cfg)
    assert "<integer>45</integer>" in text and "--scheduled" in text
    assert "MTWRFSU 00:40:00" in schedule.wake_command(cfg)


def test_cover_command_fills_disclosure(cfg, approved_series, tmp_path):
    from typer.testing import CliRunner

    from factory.cli import app

    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    art = tmp_path / "art.png"
    Image.new("RGB", (1024, 1536), (40, 60, 90)).save(art)
    res = CliRunner().invoke(app, ["cover", bid, "--art", str(art), "--tool", "ElevenLabs (GPT Image 2.5)"])
    assert res.exit_code == 0, res.output
    pkg = cfg.paths.book_dir(approved_series, bid) / "package"
    text = (pkg / "ai-disclosure.md").read_text()
    assert "ElevenLabs (GPT Image 2.5)" in text and "fill in before upload" not in text
    assert Image.open(pkg / "cover.jpg").size == (1600, 2560)


def test_repackage_keeps_cover_tool(cfg, approved_series, tmp_path):
    from typer.testing import CliRunner

    from factory.cli import app

    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    art = tmp_path / "art.png"
    Image.new("RGB", (1024, 1536), (40, 60, 90)).save(art)
    runner = CliRunner()
    res = runner.invoke(app, ["cover", bid, "--art", str(art), "--tool", "ElevenLabs (FLUX 3 Image)"])
    assert res.exit_code == 0, res.output
    assert state.load_book(cfg, bid)["cover_tool"] == "ElevenLabs (FLUX 3 Image)"
    res = runner.invoke(app, ["repackage", bid])
    assert res.exit_code == 0, res.output
    text = (cfg.paths.book_dir(approved_series, bid) / "package" / "ai-disclosure.md").read_text()
    assert "Tool: ElevenLabs (FLUX 3 Image) |" in text and "fill in before upload" not in text


def test_repackage_recovers_cover_tool_from_old_disclosure(cfg, approved_series):
    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    b = state.load_book(cfg, bid)
    b.pop("cover_tool", None)
    disclosure = cfg.paths.book_dir(approved_series, bid) / "package" / "ai-disclosure.md"
    disclosure.write_text(disclosure.read_text().replace(package.COVER_TOOL_PLACEHOLDER, "ElevenLabs (FLUX 3 Image)"))
    meta = json.loads((disclosure.parent / "metadata.json").read_text())
    package.write_disclosure(cfg, b, meta)
    assert "Tool: ElevenLabs (FLUX 3 Image) |" in disclosure.read_text()
    assert b["cover_tool"] == "ElevenLabs (FLUX 3 Image)"


def test_paperback_interior_and_wrap(cfg, approved_series, tmp_path):
    from factory import paperback

    bid = f"{approved_series}-b01"
    orchestrator.run(cfg, book_id=bid, echo=lambda *_: None)
    b = state.load_book(cfg, bid)
    assert b["package"]["paperback"]["pages"] >= 4
    art = tmp_path / "art.png"
    Image.new("RGB", (2048, 3072), (70, 40, 90)).save(art)
    info = paperback.build(cfg, b, art)
    out = cfg.paths.book_dir(approved_series, bid) / "package" / "paperback"
    for name in ("interior.pdf", "cover-wrap.pdf", "cover-wrap-preview.jpg", "paperback-checklist.md"):
        assert (out / name).exists(), name
    assert info["spine_in"] == paperback.spine_width(info["pages"], "cream")
    assert info["wrap_in"][1] == 8.75


def test_kdp_formulas():
    from factory import paperback

    assert paperback.gutter_for(120) == 0.375 and paperback.gutter_for(305) == 0.625
    assert paperback.spine_width(305, "cream") == 0.7625
    assert paperback.spine_width(300, "white") == 0.6756


def test_author_page(cfg, approved_series):
    from factory import authorpage

    out = authorpage.build(cfg, "Test Pen", "test lane")
    text = (out / "author-central.md").read_text()
    assert "Biography" in text and "Short bio" in text
    assert Image.open(out / "author-image.png").size == (1200, 1200)
