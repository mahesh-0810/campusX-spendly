# Spec: Login and Logout

## Overview

Implements authenticated sessions for Spendly. The `GET /login` route and its
template already exist and render a form, but submitting it does nothing —
there is no handler that verifies credentials against the `users` table and
establishes a session. `/logout` is currently a placeholder that returns the
string `"Logout — coming in Step 3"`. This step wires up real sign-in
(verify email/password, start a session) and sign-out (clear the session),
building directly on the data layer from
[01-database-setup.md](01-database-setup.md) and the account creation flow
from [02-registration.md](02-registration.md). It also makes the navbar and
the existing placeholder routes (`/profile`, `/expenses/*`) aware of whether
a visitor is signed in, since that's the whole point of having a session.
Building out what those placeholder routes actually *do* remains later steps.

## Depends on

- Step 1 — Database setup (`database/db.py`: `get_db()`, `users` table).
- Step 2 — Registration (`POST /register` creates the hashed-password rows
  that login authenticates against).

## Routes

- `GET /login` — renders the sign-in form — public (already exists, unchanged
  for anonymous visitors; now redirects to `/<user_id>` if already signed in)
- `POST /login` — validates credentials, starts a session on success,
  redirects to `/<user_id>`, re-renders the form with an error on failure —
  public (new handler on the existing route)
- `GET /register` — renders the registration form — public for anonymous
  visitors; now redirects to `/<user_id>` if already signed in (unchanged
  otherwise from Step 2)
- `GET /<int:user_id>` — renders the landing page for a signed-in user;
  redirects to `/login` if the id doesn't match the current session — logged-in
  (new variant of the existing `GET /` route, same view function)
- `GET /logout` — clears the session, redirects to `/login` — logged-in
  (replaces the placeholder string response)
- `GET /profile`, `GET /expenses/add`, `GET /expenses/<id>/edit`,
  `GET /expenses/<id>/delete` — unchanged placeholder responses, but now
  redirect anonymous visitors to `/login` instead of rendering — logged-in
  (access-control only; their placeholder text is untouched)

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`,
`password_hash`, `created_at`) already has everything login needs. Verified
against `database/db.py`.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — no structural changes needed; it already posts
    to `/login` and renders `{{ error }}` when present.
  - `templates/base.html` — the navbar currently always shows "Sign in" /
    "Get started". Make it conditional on `session`: signed-out visitors see
    the existing links; signed-in visitors see a "Logout" link (Flask's
    `session` object is available in Jinja by default, no context processor
    needed).

## Files to change

- `app.py`:
  - Set `app.secret_key` (required for Flask's signed session cookie) —
    read from `os.environ.get("SECRET_KEY")` with a clearly-marked
    dev-only fallback, since there's no secrets setup elsewhere in this
    teaching project.
  - Change `@app.route("/login")` to accept `GET` and `POST`; add credential
    validation (`check_password_hash`), a generic invalid-credentials error,
    and `session["user_id"]` / `session["user_name"]` on success.
  - Replace the `/logout` placeholder with a real handler: clear the
    session (`session.clear()`) and redirect to `/login`.
  - Add a small `login_required` decorator (`functools.wraps`) that redirects
    to `/login` when `session.get("user_id")` is missing, and apply it to
    `/profile`, `/expenses/add`, `/expenses/<id>/edit`,
    `/expenses/<id>/delete`. Their existing placeholder return values are
    otherwise untouched.
  - Add a guard at the top of `login()` and `register()` that redirects an
    already-authenticated visitor (`session.get("user_id")` set) straight to
    `/<user_id>`, so a signed-in user can't navigate back to either form —
    only `/logout` clears the session and makes them reachable again.
  - Add an `after_request` hook that sets `Cache-Control: no-store` (and
    `Pragma: no-cache`) on every non-static response, so the browser's
    back/forward button can't show a stale cached page (e.g. a page from
    before logout, or a 404 for a nonexistent URL) without re-hitting the
    server — that would bypass every session check above.
- `templates/base.html` — conditional navbar block described above.

## Files to create

None.

## New dependencies

No new dependencies. Flask's session support (`itsdangerous`) ships with
Flask already.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (verify with `check_password_hash`, never
  compare plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server even though the form has `required`/`type=email`
  HTML attributes
- Use one generic error message ("Invalid email or password") for both
  "no such user" and "wrong password" so the form doesn't leak which
  emails are registered
- Look up the user by email (case-insensitive, matching the registration
  lookup) before checking the password
- On success, store the minimum needed in `session` (`user_id`, `user_name`)
  — never store the password or password hash in the session
- On failed login, re-render `login.html` with `error` (not a redirect) so
  the message is visible, matching the registration error pattern
- `/logout` must work for a GET request (it's a plain navbar link) and must
  redirect (302) to `/login` after clearing the session
- `login_required` must redirect (302) to `/login`, not return a 403/401
  page, since there's no error page built yet

## Definition of done

- [ ] Visiting `/login` still renders the form (GET unchanged)
- [ ] Submitting valid credentials for a real user (e.g. the seeded
      `demo@spendly.com` / `demo123`) logs in and redirects to `/<user_id>`
      (e.g. `/1`), which renders the landing page with the navbar showing
      "Logout" — chosen over `/profile` since that route is still a bare
      placeholder string with no navbar until Step 4 builds it out
- [ ] Visiting `/<user_id>` for an id that doesn't match the signed-in
      user's session redirects to `/login` instead of rendering
- [ ] Submitting an unknown email re-renders `login.html` with a generic
      "Invalid email or password" error
- [ ] Submitting a known email with the wrong password re-renders
      `login.html` with the same generic error
- [ ] After logging in, the navbar shows a "Logout" link instead of
      "Sign in" / "Get started"
- [ ] Visiting `/logout` while logged in clears the session and redirects
      to `/login`; the navbar reverts to "Sign in" / "Get started"
- [ ] Visiting `/profile` (or any `/expenses/*` placeholder route) while
      logged out redirects to `/login` instead of showing the placeholder text
- [ ] Visiting `/profile` (or any `/expenses/*` placeholder route) while
      logged in still shows its existing placeholder text
- [ ] While logged in, visiting `/login` or `/register` redirects to
      `/<user_id>` instead of rendering either form
- [ ] After `/logout`, `/login` and `/register` render their forms again
- [ ] Any dynamic page response (including a 404 for an unknown URL) carries
      `Cache-Control: no-store`; `/static/*` responses are unaffected
- [ ] No unhandled exceptions/500s for any of the above cases
- [ ] App still starts cleanly via `python app.py`
