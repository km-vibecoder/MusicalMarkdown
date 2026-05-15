# Contributing to Musical Markdown

Thanks for your interest in contributing. This document covers how to get set up, what kinds of contributions are welcome, and the workflow for getting changes merged.

---

## Table of Contents

- [What to Work On](#what-to-work-on)
- [Getting Set Up](#getting-set-up)
- [The Spec is the Source of Truth](#the-spec-is-the-source-of-truth)
- [Contribution Workflow](#contribution-workflow)
- [Code Style](#code-style)
- [Running Tests](#running-tests)

---

## What to Work On

Check the [open issues](../../issues) for bugs and planned features. The project roadmap is outlined in `README.md`. If you have an idea not already tracked, open an issue first to discuss it before writing code — this avoids wasted effort on work that won't be merged.

Good first contributions:
- Adding `.mmd` example scores to `examples/`
- Expanding the test suite in `tests/test_mmd_validator.py`
- Reporting and fixing validator edge cases
- Improving error messages

---

## Getting Set Up

```bash
git clone https://github.com/km-vibecoder/MusicalMarkdown.git
cd MusicalMarkdown

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python tests/test_mmd_validator.py   # should pass all 71 tests
```

No other setup is required for the core tools. `mmd_to_midi.py` requires `midiutil`; `mmd_to_lilypond.py` requires a local LilyPond installation for PDF rendering (`.ly` export works without it).

---

## The Spec is the Source of Truth

`spec/musical-markdown-spec.md` defines correct `.mmd` behavior. If the validator and the spec disagree, the spec wins. Any change to parsing or validation behavior **must** be preceded by a spec update. Do not patch the validator to match edge-case behavior you observed — first determine whether the spec should allow it.

---

## Contribution Workflow

1. **Open or claim an issue** — comment on the issue you're working on so others know it's in progress.
2. **Fork and branch** — branch names like `fix/validator-tie-edge-case` or `feat/prompt-library` are preferred.
3. **Follow the change checklist** for the area you're touching:

   | Area | Checklist |
   |------|-----------|
   | New syntax feature | Update spec → add tests → implement → confirm tests pass → update MANIFEST.md |
   | Validator bug fix | Add a failing test that reproduces it → fix → confirm it passes |
   | New tool | Add tests → document in README and MANIFEST.md |
   | New example score | Validate with `python tools/mmd_validator.py examples/your-score.mmd` before committing |

4. **Open a pull request** — fill out the PR template. Link the issue it closes.
5. **Review** — the maintainer will review and may request changes. Keep the PR focused; one concern per PR.

---

## Code Style

- Python: follow PEP 8. No external formatters are enforced, but keep lines under 100 characters.
- No comments that restate what the code does. Comments should explain *why* something is done a non-obvious way.
- New `.mmd` example files must pass the validator with exit code `0`.

---

## Running Tests

```bash
# Full suite
python tests/test_mmd_validator.py

# Verbose
python tests/test_mmd_validator.py -v

# Validate an example score
python tools/mmd_validator.py examples/your-score.mmd
```

All tests must pass before a PR can be merged.
