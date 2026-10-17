"""macOS launchd job for the nightly run, with a cron fallback (PRD section 9, M7)."""

import shutil
import sys
from pathlib import Path

from .config import Config

LABEL = "com.romantasy.factory"


def plist(cfg: Config) -> str:
    h, m = (int(x) for x in cfg.get("schedule.start", "01:00").split(":"))
    factory_bin = shutil.which("factory") or f"{sys.executable} -m factory.cli"
    program = factory_bin.split() + ["run", "--scheduled"]
    args = "\n".join(f"      <string>{a}</string>" for a in program)
    root = cfg.paths.root
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>WorkingDirectory</key>
    <string>{root}</string>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>{h}</integer>
      <key>Minute</key>
      <integer>{m}</integer>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{Path.home()}/.local/bin</string>
    </dict>
    <key>StandardOutPath</key>
    <string>{root}/reports/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>{root}/reports/launchd.err.log</string>
  </dict>
</plist>
"""


def wake_command(cfg: Config) -> str:
    wake = cfg.get("schedule.wake", "00:55")
    return f"sudo pmset repeat wakeorpoweron MTWRFSU {wake}:00"


def cron_line(cfg: Config) -> str:
    h, m = (int(x) for x in cfg.get("schedule.start", "01:00").split(":"))
    return f"{m} {h} * * * cd {cfg.paths.root} && factory run --scheduled >> reports/cron.log 2>&1"


def install(cfg: Config, dry_run: bool = False) -> tuple[Path, str]:
    target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    text = plist(cfg)
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return target, text
