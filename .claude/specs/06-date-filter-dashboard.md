# Spec: Date Filter Dashboard

## Overview

Adds a date-range filter to the signed-in dashboard (`/<user_id>`) built in
Step 5. Users can narrow the transaction history, summary stats, and
category breakdown to a specific date range via a small GET-based filter
form at the top of the dashboard. This is the first step that lets a user
interact with their own expense data rather than just viewing everything
at once — a prerequisite for the dashboard staying usable once a user has
accumulated many months of expenses.

## Depends on

- Step 1 — Database setup (`database/db.py`: `get_db()`, `expenses` table
  with its `date` column, seeded demo data).
- Step 5 — Expense Listing Dashboard (`dashboard.html`, and the
  `get_transactions`, `get_summary_stats`, `get_category_breakdown` helper
  functions in `app.py` that this step extends).

## Routes

- `GET /<user_id>` — signed-in visitors viewing their own id: now also
  accepts optional `start_date` and `end_date` query params
  (`YYYY-MM-DD`) and, when present, filters transaction history, summary
  stats, and category breakdown to that date range (inclusive) —
  logged-in (behavior change to the existing `landing` view function, not
  a new route). No filter params behaves exactly as it does today.

No new URL paths are introduced.

## Database changes

No database changes. The existing `expenses.date` column is stored as
`YYYY-MM-DD` text, which sorts and compares correctly with SQL `BETWEEN`
without any schema change. Verified against `database/db.py`.

## Templates

- **Create:** none.
- **Modify:** `templates/dashboard.html`
  - Add a filter form above the transaction history block: two
    `type="date"` inputs (`name="start_date"`, `name="end_date"`), an
    "Apply" submit button, and a "Clear filter" link
    (`{{ url_for('landing', user_id=session['user_id']) }}`) shown only
    when a filter is active. Form uses `method="get"` so the filtered view
    stays a plain, bookmarkable/shareable URL — no new form-handling route.
  - Inputs are pre-filled with `value="{{ start_date or '' }}"` /
    `value="{{ end_date or '' }}"` so the chosen range persists after
    filtering.
  - Show `filter_error` (if passed) above the form, reusing the existing
    error-message styling pattern already used on other pages
    (e.g. `info_error` on `profile.html`).
  - Stats, category breakdown, and transaction list markup are otherwise
    unchanged — they already handle the empty-state case, which also
    covers "no expenses in this range."

## Files to change

- `app.py`:
  - `get_transactions(conn, user_id, start_date=None, end_date=None)` —
    extend the existing query with an optional `AND date >= ?` /
    `AND date <= ?` clause, added only for the params that are present.
  - `get_summary_stats(conn, user_id, start_date=None, end_date=None)` —
    same optional date-range extension.
  - `get_category_breakdown(conn, user_id, start_date=None, end_date=None)`
    — same optional date-range extension.
  - `landing()` view function: read `start_date`/`end_date` from
    `request.args`, validate each is either absent or a well-formed
    `YYYY-MM-DD` date (reuse a `datetime.strptime` check, matching the
    style already used in `format_member_since`), and that
    `start_date <= end_date` when both are present. On validation failure,
    render `dashboard.html` with a `filter_error` message and the
    **unfiltered** data (do not apply a partial/invalid filter). On
    success, pass `start_date`/`end_date` through to all three helper
    calls and to the template.
- `static/css/style.css` — add dashboard-filter form styles (inputs,
  labels, apply button, clear link, error message) near the existing
  dashboard rules from Step 5, using existing CSS variables only.

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Mirror existing `app.py` conventions: inline SQL via
  `get_db()`/`conn.execute(...)` inside `try/finally` (no new shared
  DB-helper functions — extend the three existing Step 5 helpers instead
  of adding more)
- Keep the date-range clauses optional/composable in each helper (a call
  with no dates must produce the exact same query Step 5 already runs)
- Do not touch `/expenses/add`, `/expenses/<id>/edit`, or
  `/expenses/<id>/delete` — they stay exactly as their current placeholder
  responses
- Do not change the "mismatched id redirects to `/login`" behavior from
  Step 3

## Definition of done

- [ ] Visiting `/<user_id>` with no query params renders exactly as it did
      before this step (all transactions, unfiltered stats and breakdown).
- [ ] Visiting `/<user_id>?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
      shows only transactions within that inclusive range, with stats and
      category breakdown recomputed for that same range.
- [ ] Supplying only `start_date` filters from that date onward; supplying
      only `end_date` filters up to that date.
- [ ] The filter form's inputs are pre-filled with the submitted
      start/end dates after filtering.
- [ ] A "Clear filter" link is shown when a filter is active and returns
      to the unfiltered `/<user_id>` view.
- [ ] Submitting `start_date` after `end_date` (invalid range) shows a
      validation error and falls back to the unfiltered view instead of
      erroring or silently misfiltering.
- [ ] Submitting a malformed date value shows a validation error and
      falls back to the unfiltered view.
- [ ] Filtering to a range with zero matching expenses shows the existing
      empty-state messages, with stats correctly at `₹0.00` / `0`.
- [ ] Visiting `/<user_id>` for an id that doesn't match the signed-in
      user's session still redirects to `/login` (unchanged from Step 3).
- [ ] No unhandled exceptions/500s for any of the above.
- [ ] App still starts cleanly via `python app.py`.
