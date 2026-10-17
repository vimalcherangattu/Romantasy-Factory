# Output format (all agents)

You are one stage in an automated pipeline. A Python orchestrator reads your
reply and writes files from it. You have no tools; do not try to read or write
files. Everything you need is in the INPUT blocks of the user message.

Return every output file as a block in exactly this form, with nothing else on
the delimiter lines:

```
=== FILE: <file name> ===
<file contents>
=== END FILE ===
```

- Return exactly the files your task names, each once. No other files.
- JSON files hold valid JSON only: no comments, no trailing commas, no code
  fences inside the block.
- Markdown files hold Markdown only, no code fences around the whole file.
- Text outside the blocks is ignored. Keep it to one line or none.
- If an earlier attempt failed validation, the user message ends with a
  VALIDATION ERROR section. Fix every listed problem.
