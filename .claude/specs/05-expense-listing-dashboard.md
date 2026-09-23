# Spec: Expense Listing Dashboard

## Overview

Replaces the marketing `landing.html` page that a signed-in user currently
sees at `/<user_id>` with a real dashboard showing three pieces: **transaction
history** (a list of the user's expenses), **summary stats** (total spent and
transaction count), and a **category breakdown** (per-category totals). This
is the first step that actually reads and displays expense data — until now
the `expenses` table exists and is seeded but nothing renders it. It's a
prerequisite for the still-placeholder `/expenses/add`,
`/expenses/<id>/edit`, and `/expenses/<id>/delete` routes, since a real
dashboard is what those routes need to link to/from and redirect back to
once they're implemented in later steps. The three pieces are implemented as
three independent, parallelizable read-only helper functions in `app.py` so
they can be built concurrently without touching the same lines of the file.

## Depends on

- Step 1 — Database setup (`database/db.py`: `get_db()`, `expenses` table,
  seeded demo data).
- Step 3 — Login/Logout (session `user_id`, the existing `/<user_id>`
  route variant, `login_required`).

## Routes

- `GET /` — anonymous visitors: unchanged, renders the existing marketing
  `landing.html` — public
- `GET /` — signed-in visitors: now redirects to `/<user_id>` (their own
  dashboard) instead of rendering the marketing page — logged-in (behavior
  change to the existing `landing` view function, not a new route)
- `GET /<user_id>` — signed-in visitors viewing their own id: now
  gathers transaction history, summary stats, and category breakdown via
  three separate queries and renders the new `dashboard.html` with that
  data, instead of `landing.html` — logged-in (behavior change to the
  existing `landing` view function; the existing "mismatched id redirects
  to `/login`" behavior from Step 3 is unchanged)

No new URL paths are introduced — this step changes what the existing
`landing` view function renders depending on session state.

## Database changes

No database changes. Uses the existing `expenses` table
(`id, user_id, amount, category, date, description, created_at`) and
`users` table. Verified against `database/db.py`. The category breakdown is
computed with a `GROUP BY category` query over the existing `expenses` table
— no migration needed.

## Templates

- **Create:** `templates/dashboard.html` — extends `base.html`. Shows:
  - **Summary stats**: two stat tiles — total spent and number of
    transactions. Since these come from `COALESCE(SUM(...), 0)` and
    `COUNT(*)`, they never need an empty-state branch — a zero-expense user
    still sees `₹0.00` / `0` correctly.
  - **Category breakdown**: one row per category the user has spent in,
    category name and total, sorted by total descending. Its own
    empty-state message when the user has no expenses.
  - **Transaction history**: an "Add expense" link
    (`{{ url_for('add_expense') }}`), then a list of the user's expenses,
    most recent date first, each row showing date, category, description,
    and amount, with "Edit" (`{{ url_for('edit_expense', id=expense['id']) }}`)
    and "Delete" (`{{ url_for('delete_expense', id=expense['id']) }}`)
    links. These three routes remain placeholder responses until Steps
    7–9 — this step only needs the links to exist and point at the right
    URLs. Its own empty-state message (e.g. "No expenses yet — add your
    first one.") when the user has zero expenses, instead of an empty list.
- **Modify:** none. `landing.html` and `base.html` are unchanged.

## Files to change

- `app.py`:
  - Add three new module-level helper functions, each a small, independent,
    pure read-only query — `get_transactions(conn, user_id)`,
    `get_summary_stats(conn, user_id)`, `get_category_breakdown(conn, user_id)`
    — placed at three separate, non-adjacent points in the file.
    **Deliberate, scoped exception to the "no shared DB-helper functions"
    convention below**: these three exist specifically so three subagents
    could implement the dashboard's three pieces in parallel without
    touching the same lines of `app.py`. This does not license further
    DB-helper extraction elsewhere — new routes should still keep inline
    SQL per the existing convention.
  - Modify the `landing()` view function:
    - If `user_id is None` and the visitor is signed in
      (`session.get('user_id')`), redirect to
      `url_for('landing', user_id=session['user_id'])`.
    - If `user_id is not None` and it matches the signed-in session, call
      all three helper functions and render `dashboard.html` with their
      results.
    - Anonymous visitors to `/` keep rendering `landing.html`, unchanged.
- `static/css/style.css` — add dashboard-related rules (header, stat tiles,
  category breakdown list, transaction list/row, shared empty-state class)
  near the existing page-specific blocks, using existing CSS variables only.

## Files to create

- `templates/dashboard.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Mirror existing `app.py` conventions: inline SQL via
  `get_db()`/`conn.execute(...)` inside `try/finally` (no shared
  DB-helper functions beyond what's already in `database/db.py`)
- Format `amount` for display as currency (e.g. `₹{{ '%.2f' % amount }}`),
  matching the ₹ symbol already used elsewhere in the templates
- Do not touch `/expenses/add`, `/expenses/<id>/edit`, or
  `/expenses/<id>/delete` — they stay exactly as their current placeholder
  responses; this step only links to them

## Definition of done

- [ ] Visiting `/` while logged out still renders the existing marketing
      landing page, unchanged.
- [ ] Visiting `/` while logged in redirects to `/<user_id>`.
- [ ] Visiting `/<user_id>` while logged in as that user renders
      `dashboard.html` listing all of that user's expenses (the seeded demo
      user has 8), sorted by date descending.
- [ ] The dashboard shows the correct total spent and transaction count
      (both matching the seeded data).
- [ ] The dashboard shows a per-category breakdown with correct per-category
      totals, sorted highest-first.
- [ ] The dashboard shows an "Add expense" link pointing at
      `/expenses/add`.
- [ ] Each expense row shows working "Edit" and "Delete" links pointing at
      `/expenses/<id>/edit` and `/expenses/<id>/delete` for that expense's
      id.
- [ ] Visiting `/<user_id>` for an id that doesn't match the signed-in
      user's session still redirects to `/login` (unchanged from Step 3).
- [ ] A signed-in user with zero expenses sees empty-state messages in both
      the category breakdown and the transaction list, while the stats
      still show `₹0.00` / `0` transactions without erroring.
- [ ] No unhandled exceptions/500s for any of the above.
- [ ] App still starts cleanly via `python app.py`.
