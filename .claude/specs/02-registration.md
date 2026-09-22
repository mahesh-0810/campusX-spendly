# Spec: Registration

## Overview

Implements user registration for Spendly. The `GET /register` route and its
template already exist and render a form, but submitting it does nothing —
there is no handler that validates the input, hashes the password, and
inserts a new row into `users`. This step wires that up so a visitor can
create an account, building directly on the data layer from
[01-database-setup.md](01-database-setup.md). It does not implement login
sessions — after a successful registration the user is redirected to the
existing `/login` page, whose own session/auth logic is a later step.

## Depends on

- Step 1 — Database setup (`database/db.py`: `get_db()`, `users` table). Must
  already be implemented and working.

## Routes

- `GET /register` — renders the registration form — public (already exists, unchanged)
- `POST /register` — validates input, creates the user, redirects to `/login` on success, re-renders the form with an error on failure — public (new handler on the existing route)

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`,
`password_hash`, `created_at`) already has everything registration needs.
Verified against `database/db.py`.

## Templates

- **Create:** none
- **Modify:** `templates/register.html` — no structural changes needed; it
  already posts to `/register` and renders `{{ error }}` when present. The
  handler just needs to supply `error` (and ideally re-populate `name`/`email`
  on validation failure so the user doesn't retype everything).

## Files to change

- `app.py` — change `@app.route("/register")` to accept `GET` and `POST`;
  add form validation, duplicate-email check, password hashing, insert, and
  redirect-on-success logic.

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server even though the form has `required`/`type=email`
  HTML attributes (don't trust client-side validation alone)
- Check for an existing email (case-insensitive) before inserting, and show
  a clear `error` message if it's taken, re-rendering `register.html` with a
  422/200 response (not a redirect) so the message is visible
- Enforce a minimum password length (8 characters, matching the placeholder
  text already in the template) server-side
- On success, redirect (302) to `/login` — do not log the user in automatically,
  since session handling isn't built yet

## Definition of done

- [ ] Visiting `/register` still renders the form (GET unchanged)
- [ ] Submitting the form with valid name/email/password creates a row in
      `users` with a hashed (not plaintext) password
- [ ] Submitting with an email that already exists re-renders `register.html`
      with an error message and does not create a duplicate row
- [ ] Submitting with a password under 8 characters re-renders the form with
      an error and does not create a row
- [ ] Submitting with a missing name, email, or password re-renders the form
      with an error and does not create a row
- [ ] A successful registration redirects to `/login`
- [ ] No unhandled exceptions/500s for any of the above cases
- [ ] App still starts cleanly via `python app.py`
