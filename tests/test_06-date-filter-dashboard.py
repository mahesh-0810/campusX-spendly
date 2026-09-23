"""
Tests for Step 06 — Date Filter Dashboard.

Spec: .claude/specs/06-date-filter-dashboard.md

Covers (see Definition of Done in the spec):
  - Unfiltered `/<user_id>` behaves exactly as before (all transactions,
    unfiltered stats/breakdown).
  - A valid start_date/end_date range filters transaction history, summary
    stats, and category breakdown together, with inclusive bounds.
  - One-sided filters (start_date only / end_date only) act as open-ended
    ranges.
  - Filter inputs are pre-filled with the submitted values after a
    successful filter.
  - The "Clear filter" link appears only when a filter is active.
  - An invalid range (start_date after end_date) shows a validation error
    and falls back to the unfiltered view.
  - A malformed date value shows a validation error and falls back to the
    unfiltered view.
  - A zero-match date range shows the existing empty-state markup with
    stats at Rs.0.00 / 0.
  - A mismatched/other user's id still redirects to /login (unchanged from
    Step 3), including when filter query params are present.
  - No unhandled exceptions/500s for any of the above.

No tests/ directory or conftest.py existed prior to this file, so all
fixtures are self-contained here. `database/db.py` hardcodes its sqlite
file path (no app.config['DATABASE'] hook and no in-memory-DB support), so
isolation is achieved by pointing `database.db.DB_PATH` at a throwaway
temp file *before* `app.py` is imported (app.py runs init_db()/seed_db()
at import time), and then giving every test its own freshly created user
id + expense rows rather than sharing/mutating global state.
"""

import os
import re
import sys
import tempfile

import pytest

# --------------------------------------------------------------------- #
# Make the project root importable regardless of how/where pytest is    #
# invoked from (no conftest.py exists yet to do this for us).           #
# --------------------------------------------------------------------- #
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TESTS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import database.db as db_module  # noqa: E402

# Point the DB layer at a throwaway sqlite file *before* importing app.py,
# since app.py's module-level `init_db()` / `seed_db()` calls run against
# whatever DB_PATH is active at import time.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="spendly_test_", suffix=".db")
os.close(_TEST_DB_FD)
db_module.DB_PATH = _TEST_DB_PATH

import app as app_module  # noqa: E402
from flask import url_for  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

flask_app = app_module.app
get_db = db_module.get_db
generate_user_id = db_module.generate_user_id


# --------------------------------------------------------------------- #
# URL helpers — build routes via url_for(), never hardcoded paths.      #
# --------------------------------------------------------------------- #

def dashboard_url(user_id, **query):
    with flask_app.test_request_context():
        return url_for("landing", user_id=user_id, **query)


def login_path():
    with flask_app.test_request_context():
        return url_for("login")


# --------------------------------------------------------------------- #
# Markup-structure helpers (regex over rendered HTML). These key off     #
# the template class names the spec itself calls out (dashboard-stats   #
# `.stat-value`, `.category-*`, `.expense-*`, and the shared             #
# `.auth-error` / `.empty-state` styling conventions used across the     #
# app's other pages) rather than any Python implementation detail.       #
# --------------------------------------------------------------------- #

STAT_VALUE_RE = re.compile(rb'<span class="stat-value">([^<]*)</span>')
EXPENSE_DESC_RE = re.compile(rb'<span class="expense-desc">([^<]*)</span>')
CATEGORY_NAME_RE = re.compile(rb'<span class="category-name">([^<]*)</span>')


def stat_values(response_data):
    """['<total>', '<count>'] as rendered in the two dashboard-stats cards."""
    return [v.decode("utf-8") for v in STAT_VALUE_RE.findall(response_data)]


def expense_descriptions(response_data):
    return [v.decode("utf-8") for v in EXPENSE_DESC_RE.findall(response_data)]


def category_names(response_data):
    return [v.decode("utf-8") for v in CATEGORY_NAME_RE.findall(response_data)]


# --------------------------------------------------------------------- #
# Fixtures                                                               #
# --------------------------------------------------------------------- #

# Fixed, non-relative dates so range-filter assertions never flake across
# month/year boundaries the way "today - N days" seed data would.
FIXTURE_EXPENSES = [
    # (amount, category, date, description)
    (10.00, "Food", "2026-01-05", "Groceries"),
    (20.00, "Transport", "2026-01-15", "Bus pass"),
    (30.00, "Bills", "2026-01-25", "Electricity"),
    (40.00, "Health", "2026-02-05", "Pharmacy"),
    (50.00, "Entertainment", "2026-02-15", "Movie night"),
]
ALL_DESCRIPTIONS = [d for _, _, _, d in FIXTURE_EXPENSES]
UNFILTERED_TOTAL = sum(a for a, _, _, _ in FIXTURE_EXPENSES)  # 150.00
UNFILTERED_COUNT = len(FIXTURE_EXPENSES)  # 5


@pytest.fixture
def app():
    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _insert_user(name, email):
    conn = get_db()
    try:
        uid = generate_user_id()
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (uid, name, email, generate_password_hash("testpass123")),
        )
        conn.commit()
        return uid
    finally:
        conn.close()


def _insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def new_user():
    """A fresh, otherwise-empty user id."""
    uid = _insert_user("Filter Test User", f"filtertest-{generate_user_id()}@example.com")
    return uid


@pytest.fixture
def other_user():
    """A second, distinct user id, unrelated to any logged-in client."""
    uid = _insert_user("Other User", f"otheruser-{generate_user_id()}@example.com")
    return uid


@pytest.fixture
def seeded_user(new_user):
    """`new_user`, with FIXTURE_EXPENSES inserted."""
    for amount, category, expense_date, description in FIXTURE_EXPENSES:
        _insert_expense(new_user, amount, category, expense_date, description)
    return new_user


@pytest.fixture
def auth_client(client, seeded_user):
    """A test client with a real session logged in as `seeded_user`."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user
        sess["user_name"] = "Filter Test User"
    return client


# --------------------------------------------------------------------- #
# Tests                                                                  #
# --------------------------------------------------------------------- #

class TestUnfilteredDashboard:
    """DoD: `/<user_id>` with no query params renders exactly as before —
    all transactions, unfiltered stats and breakdown."""

    def test_no_query_params_shows_all_transactions(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user))
        assert response.status_code == 200
        descriptions = expense_descriptions(response.data)
        assert sorted(descriptions) == sorted(ALL_DESCRIPTIONS), (
            "Unfiltered dashboard should list every expense for the user"
        )

    def test_no_query_params_shows_unfiltered_stats(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user))
        assert stat_values(response.data) == [
            f"₹{UNFILTERED_TOTAL:.2f}", str(UNFILTERED_COUNT)
        ], "Unfiltered stats should total/count every expense for the user"

    def test_no_query_params_shows_unfiltered_category_breakdown(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user))
        names = category_names(response.data)
        expected = sorted({c for _, c, _, _ in FIXTURE_EXPENSES})
        assert sorted(names) == expected, "Unfiltered category breakdown should cover every category"

    def test_no_query_params_hides_clear_filter_link(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user))
        assert b"Clear filter" not in response.data, (
            "Clear filter affordance must only appear when a filter is active"
        )

    def test_no_query_params_shows_no_filter_error(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user))
        assert b'class="auth-error"' not in response.data


class TestValidDateRangeFilter:
    """DoD: a valid start_date/end_date range filters history, stats, and
    breakdown together, with inclusive bounds."""

    def test_full_range_filters_transactions_inclusively(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-01-01", end_date="2026-01-31")
        )
        assert response.status_code == 200
        descriptions = expense_descriptions(response.data)
        assert sorted(descriptions) == sorted(["Groceries", "Bus pass", "Electricity"]), (
            "Only January transactions should be present in the filtered range"
        )
        assert "Pharmacy" not in descriptions
        assert "Movie night" not in descriptions

    def test_full_range_filters_boundary_dates_inclusively(self, auth_client, seeded_user):
        # 2026-01-05 and 2026-01-25 are the exact boundary dates of the
        # fixture data — both must be included ("inclusive" per spec).
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-01-05", end_date="2026-01-25")
        )
        descriptions = expense_descriptions(response.data)
        assert "Groceries" in descriptions, "start_date boundary itself must be included"
        assert "Electricity" in descriptions, "end_date boundary itself must be included"

    def test_full_range_recomputes_stats(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-01-01", end_date="2026-01-31")
        )
        assert stat_values(response.data) == ["₹60.00", "3"]

    def test_full_range_recomputes_category_breakdown(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-01-01", end_date="2026-01-31")
        )
        names = category_names(response.data)
        assert sorted(names) == sorted(["Food", "Transport", "Bills"])
        assert "Health" not in names
        assert "Entertainment" not in names


class TestOneSidedDateFilter:
    """DoD: supplying only start_date filters from that date onward;
    supplying only end_date filters up to that date."""

    def test_start_date_only_is_open_ended(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, start_date="2026-01-25"))
        descriptions = expense_descriptions(response.data)
        assert sorted(descriptions) == sorted(["Electricity", "Pharmacy", "Movie night"])
        assert stat_values(response.data) == ["₹120.00", "3"]

    def test_end_date_only_is_open_ended(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, end_date="2026-01-15"))
        descriptions = expense_descriptions(response.data)
        assert sorted(descriptions) == sorted(["Groceries", "Bus pass"])
        assert stat_values(response.data) == ["₹30.00", "2"]


class TestFilterFormPersistenceAndClearLink:
    """DoD: filter inputs are pre-filled after filtering; Clear filter link
    is shown only when a filter is active and returns to the unfiltered view."""

    def test_inputs_prefilled_after_successful_filter(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-01-01", end_date="2026-01-31")
        )
        assert b'value="2026-01-01"' in response.data
        assert b'value="2026-01-31"' in response.data

    def test_clear_filter_link_shown_when_filter_active(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, start_date="2026-01-01"))
        assert b"Clear filter" in response.data
        unfiltered_url = dashboard_url(seeded_user)
        assert f'href="{unfiltered_url}"'.encode() in response.data, (
            "Clear filter link should point back to the unfiltered dashboard URL"
        )

    def test_clear_filter_link_shown_for_end_date_only(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, end_date="2026-01-31"))
        assert b"Clear filter" in response.data


class TestInvalidFilterFallback:
    """DoD: an invalid range or a malformed date shows a validation error
    and falls back to the unfiltered view (never a 500 or a partial/wrong
    filter)."""

    def test_start_after_end_shows_error(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-02-01", end_date="2026-01-01")
        )
        assert response.status_code == 200
        assert b'class="auth-error"' in response.data, "Invalid range must show a validation error"

    def test_start_after_end_falls_back_to_unfiltered_data(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-02-01", end_date="2026-01-01")
        )
        assert sorted(expense_descriptions(response.data)) == sorted(ALL_DESCRIPTIONS), (
            "An invalid range must not apply a partial/wrong filter"
        )
        assert stat_values(response.data) == [
            f"₹{UNFILTERED_TOTAL:.2f}", str(UNFILTERED_COUNT)
        ]

    def test_malformed_start_date_shows_error_and_falls_back(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, start_date="not-a-date"))
        assert response.status_code == 200
        assert b'class="auth-error"' in response.data
        assert sorted(expense_descriptions(response.data)) == sorted(ALL_DESCRIPTIONS)

    def test_malformed_end_date_shows_error_and_falls_back(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, end_date="2026-13-40"))
        assert response.status_code == 200
        assert b'class="auth-error"' in response.data
        assert sorted(expense_descriptions(response.data)) == sorted(ALL_DESCRIPTIONS)

    def test_malformed_date_falls_back_with_unfiltered_stats(self, auth_client, seeded_user):
        response = auth_client.get(dashboard_url(seeded_user, start_date="2026/01/01"))
        assert stat_values(response.data) == [
            f"₹{UNFILTERED_TOTAL:.2f}", str(UNFILTERED_COUNT)
        ], "Fallback must recompute stats over the full unfiltered set, not a partial one"


class TestZeroMatchDateRange:
    """DoD: a range with zero matching expenses shows the existing
    empty-state messages, with stats at Rs.0.00 / 0."""

    def test_zero_match_range_shows_empty_states(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-03-01", end_date="2026-03-31")
        )
        assert response.status_code == 200
        assert response.data.count(b'class="empty-state"') == 2, (
            "Both the category-breakdown and transaction-list empty states should render"
        )
        assert expense_descriptions(response.data) == []
        assert category_names(response.data) == []

    def test_zero_match_range_shows_zero_stats(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-03-01", end_date="2026-03-31")
        )
        assert stat_values(response.data) == ["₹0.00", "0"]

    def test_zero_match_range_is_not_treated_as_a_validation_error(self, auth_client, seeded_user):
        response = auth_client.get(
            dashboard_url(seeded_user, start_date="2026-03-01", end_date="2026-03-31")
        )
        assert b'class="auth-error"' not in response.data, (
            "A valid but empty-matching range is not a validation failure"
        )


class TestAuthGuardUnchanged:
    """DoD: `/<user_id>` for an id that doesn't match the signed-in user's
    session still redirects to /login (unchanged from Step 3), with or
    without filter query params."""

    def test_mismatched_user_id_redirects_to_login(self, auth_client, seeded_user, other_user):
        response = auth_client.get(dashboard_url(other_user), follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith(login_path())

    def test_mismatched_user_id_with_filter_params_redirects_to_login(
        self, auth_client, seeded_user, other_user
    ):
        response = auth_client.get(
            dashboard_url(other_user, start_date="2026-01-01", end_date="2026-01-31"),
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith(login_path()), (
            "Filter query params must not bypass the same-user auth guard"
        )

    def test_unauthenticated_request_redirects_to_login(self, client, seeded_user):
        response = client.get(dashboard_url(seeded_user), follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith(login_path())

    def test_unauthenticated_request_with_filter_params_redirects_to_login(self, client, seeded_user):
        response = client.get(
            dashboard_url(seeded_user, start_date="2026-01-01", end_date="2026-01-31"),
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith(login_path())


class TestNoUnhandledExceptions:
    """DoD: no unhandled exceptions/500s for any filter input."""

    @pytest.mark.parametrize(
        "start_date, end_date",
        [
            ("2026-01-01", "2026-01-31"),             # valid full range
            ("2026-02-01", None),                       # start only
            (None, "2026-01-15"),                        # end only
            ("2026-02-01", "2026-01-01"),                 # invalid: start after end
            ("not-a-date", None),                          # malformed start
            (None, "2026-13-40"),                           # malformed end
            ("", ""),                                        # blank values (treated as absent)
            ("2026-01-01' OR '1'='1", "2026-01-31"),          # injection-style malformed start
            ("2026/01/01", None),                              # wrong date separator
            ("2026-01-01", "not-a-date"),                       # valid start, malformed end
        ],
    )
    def test_no_500_for_any_filter_input(self, auth_client, seeded_user, start_date, end_date):
        query = {}
        if start_date is not None:
            query["start_date"] = start_date
        if end_date is not None:
            query["end_date"] = end_date
        response = auth_client.get(dashboard_url(seeded_user, **query))
        assert response.status_code == 200, (
            f"Expected 200 (never a 500) for start_date={start_date!r}, end_date={end_date!r}"
        )


def test_app_module_imports_and_starts_cleanly():
    """Smoke check for the DoD's 'App still starts cleanly' item: importing
    app.py (done at module load, above) runs its module-level init_db()/
    seed_db() without raising, and produces a usable Flask app object."""
    assert flask_app is not None
    assert flask_app.name == "app"
