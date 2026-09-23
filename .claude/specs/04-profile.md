# Spec: Profile Page

## Overview
Implements the real `/profile` page, replacing the current placeholder (`"Profile page — coming in Step 4"`). This is the first "logged-in app" page beyond authentication: a logged-in user can view their account details (name, email, member-since date) and update them, and separately change their password. It builds directly on the auth/session foundation from Steps 01–03.

## Depends on
- Step 01 (database setup) — `users` table and `get_db()`.
- Step 02 (registration) — validation conventions (`EMAIL_RE`, error wording, duplicate-email check, password hashing) that this spec mirrors.
- Step 03 (login/logout) — session (`user_id`, `user_name`) and `login_required`.

## Routes
- `GET /profile` — render the profile page pre-filled with the current user's name, email, and formatted "member since" date — logged-in only
- `POST /profile` — update name/email — logged-in only
- `POST /profile/password` — change password — logged-in only

(Two separate routes/views rather than one view branching on a hidden field, matching this codebase's existing pattern of distinct routes per distinct action, e.g. `login`/`logout`.)

## Database changes
No database changes. No new tables or columns. Uses the existing `users` table (`id, name, email, password_hash, created_at`).

## Templates
- **Create:** `templates/profile.html` — extends `base.html`. Structure:
  - `.auth-section > .auth-container > .auth-header` (title "Your profile", subtitle) — same pattern as `login.html`/`register.html`.
  - First `.auth-card`: account details. Shows `.profile-meta` line "Member since {{ member_since }}". Independent `.auth-error`/`.auth-success` block. Form (`method="POST" action="/profile"`) with `.form-group` fields `name` (text, pre-filled) and `email` (email, pre-filled), `button.btn-submit` "Save changes".
  - Second `.auth-card`: change password, with an `.auth-card-title` heading "Change password". Independent `.auth-error`/`.auth-success` block. Form (`method="POST" action="/profile/password"`) with `.form-group` fields `current_password`, `new_password`, `confirm_new_password` (all `type="password"`), `button.btn-submit` "Update password".
  - `.auth-switch` link back to the dashboard (`{{ url_for('landing', user_id=session['user_id']) }}`).
  - The two cards' error/success state must stay independent — a result from one form must never overwrite or clear the other's message.
- **Modify:** `templates/base.html` — in the logged-in branch of `.nav-links`, add `<a href="{{ url_for('profile') }}">Profile</a>` immediately before the existing Logout link.

## Files to change
- `app.py` — implement `profile()` GET/POST, add `change_password()` POST view + route, add `format_member_since()` helper, add `from datetime import datetime` import.
- `templates/base.html` — add the Profile navbar link.
- `static/css/style.css` — add `.auth-success`, `.auth-card-title`, `.profile-meta` rules near the existing `.auth-*` block, using existing CSS variables only.

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only.
- Passwords hashed with werkzeug (`generate_password_hash`/`check_password_hash`).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Mirror existing `app.py` conventions exactly: inline SQL via `get_db()`/`conn.execute(...)` inside `try/finally` (no shared DB-helper functions), hardcoded form `action="/path"` strings in templates (not `url_for`, matching `register.html`/`login.html`), reuse the existing `EMAIL_RE` regex, and reuse registration's exact validation order (presence → format → length → match) and error-message wording wherever equivalent.
- Edit-info validation: `name` required ("Name is required."); `email` required ("Email is required."), format-checked with `EMAIL_RE` ("Enter a valid email address."), lowercased before comparison/storage; duplicate check excludes the current user's own id (`WHERE LOWER(email) = ? AND id != ?`, error "An account with that email already exists."); wrap the `UPDATE` in `try/except sqlite3.IntegrityError` as a race-condition backstop with the same error message.
- On successful name change, update `session["user_name"]` to keep it in sync.
- On a failed edit-info submission, re-render the form with the submitted (not stale DB) values so the user doesn't lose their edit.
- Change-password validation, in order: `current_password` required ("Current password is required."); must verify via `check_password_hash` against the stored hash ("Current password is incorrect."); `new_password` required ("New password is required."); `confirm_new_password` required ("Confirm new password is required."); `new_password` must be at least 8 characters ("Password must be at least 8 characters."); `new_password` must equal `confirm_new_password` ("Passwords do not match."). On success, store `generate_password_hash(new_password)`.
- No flash-message system exists yet; both success and error states are passed as template variables into the same `render_template("profile.html", ...)` call (no redirects on either form).

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`.
- [ ] Visiting `/profile` while logged in shows the current name, email, and correctly formatted "Member since" date, with name/email pre-filled in editable fields.
- [ ] Submitting the info form with a valid new name updates the row, updates `session["user_name"]`, and re-renders `/profile` with a success message and the new name showing.
- [ ] Submitting the info form with an empty name shows "Name is required." and does not modify the row.
- [ ] Submitting the info form with an empty email shows "Email is required."
- [ ] Submitting the info form with a malformed email (e.g. `notanemail`) shows "Enter a valid email address."
- [ ] Submitting the info form with an email already used by another user shows "An account with that email already exists." and does not update the row (use the `seed-user` skill to create a second user to test this).
- [ ] Submitting the info form with the user's own unchanged email succeeds (self-exclusion in the duplicate check works).
- [ ] Submitting the password form with the wrong current password shows "Current password is incorrect." and does not change `password_hash`.
- [ ] Submitting the password form with a new password under 8 characters shows "Password must be at least 8 characters."
- [ ] Submitting the password form where new/confirm don't match shows "Passwords do not match."
- [ ] Submitting the password form with a correct current password and valid, matching new password updates `password_hash`, shows a success message, and — verified by logging out and back in — the new password works and the old one no longer does.
- [ ] The navbar shows "Profile" next to "Logout" when logged in, and neither link appears when logged out.
- [ ] No unhandled exceptions/500s for any of the above.
- [ ] App still starts cleanly via `python app.py`.
