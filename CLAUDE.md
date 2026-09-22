# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask-based personal expense tracker built as a teaching project (course-style, step-numbered). Many routes and the database layer are intentionally left as stubs for students to implement incrementally — do not assume unimplemented functionality is a bug.

## Commands

```bash
# Install dependencies (Python venv already exists at venv/)
pip install -r requirements.txt

# Run the dev server (runs on port 5001, not the Flask default 5000)
python app.py

# Run tests
pytest
```

There is no build step, linter, or frontend bundler — templates and static assets are served directly by Flask.

## Architecture

- **`app.py`** — single Flask app with all routes defined directly on it (no blueprints). Implemented routes render Jinja templates via `render_template()`; several routes under the "Placeholder routes" comment (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) currently just return a plain string like `"Add expense — coming in Step 7"` and are meant to be built out later.
- **`database/db.py`** — currently an empty stub. Intended to hold `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (create tables with `CREATE TABLE IF NOT EXISTS`), and `seed_db()` (sample data). No ORM is used — expect raw SQLite.
- **`templates/`** — Jinja2 templates. `base.html` is the shared layout (navbar, footer, font links, `static/js/main.js` script tag) and defines `{% block title %}`, `{% block head %}`, `{% block content %}`, `{% block scripts %}`. Every page template `{% extends "base.html" %}` and fills `content`/`title`. The footer (with Terms/Privacy links) lives in `base.html`, not in individual page templates — check there first when a footer-related change is requested for "the landing page."
- **`static/css/style.css`** — the only stylesheet in the project (there is no `landing.css` despite that name sometimes being referenced informally). Design tokens (colors, fonts, radii, max-widths) are defined once as CSS custom properties in `:root` at the top of the file; reuse these tokens rather than hardcoding values. Two font families are loaded via Google Fonts in `base.html`: `--font-display` (DM Serif Display) and `--font-body` (DM Sans, weights 300/400/500/600).
- **`static/js/main.js`** — vanilla JS only, no frameworks/libraries. Code is organized as null-guarded IIFEs (e.g. the "See how it works" video modal) since this single file is loaded globally on every page via `base.html`, so feature code must check that its target elements exist before wiring up listeners.

## Conventions

- No JS frameworks or build tooling — plain HTML/CSS/JS with Jinja templating.
- Legal/informational pages (`terms.html`, `privacy.html`) share a common `.legal-*` class set in `style.css` rather than page-specific styles.
- Route functions are named after the page (`landing`, `register`, `login`, `terms`, `privacy`), and templates use `{{ url_for('<route_function>') }}` rather than hardcoded paths.
