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
