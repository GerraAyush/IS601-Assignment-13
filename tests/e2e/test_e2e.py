import pytest
from uuid import uuid4
from playwright.sync_api import expect


def _base_url(fastapi_server: str) -> str:
    return fastapi_server.rstrip("/")


def _unique_user() -> dict:
    uid = uuid4().hex[:8]
    return {
        "first_name": "Test",
        "last_name": "User",
        "email": f"test_{uid}@example.com",
        "username": f"testuser_{uid}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }


def _register_via_ui(page, fastapi_server: str, user: dict) -> None:
    page.goto(f"{_base_url(fastapi_server)}/register")
    page.fill("#username", user["username"])
    page.fill("#email", user["email"])
    page.fill("#first_name", user["first_name"])
    page.fill("#last_name", user["last_name"])
    page.fill("#password", user["password"])
    page.fill("#confirm_password", user["confirm_password"])
    page.click('button[type="submit"]')
    page.wait_for_url("**/login", timeout=5000)


def _login_via_ui(page, fastapi_server: str, user: dict) -> None:
    page.goto(f"{_base_url(fastapi_server)}/login")
    page.fill("#username", user["username"])
    page.fill("#password", user["password"])
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=5000)


def _register_and_login(page, fastapi_server: str, user: dict) -> None:
    _register_via_ui(page, fastapi_server, user)
    _login_via_ui(page, fastapi_server, user)


@pytest.mark.e2e
def test_home_page_loads(page, fastapi_server):
    page.goto(_base_url(fastapi_server))
    expect(page).to_have_title("Home")
    expect(page.locator("h1")).to_contain_text("Calculations App")


@pytest.mark.e2e
def test_login_page_loads(page, fastapi_server):
    page.goto(f"{_base_url(fastapi_server)}/login")
    expect(page).to_have_title("Login")
    expect(page.locator("#loginForm")).to_be_visible()


@pytest.mark.e2e
def test_register_page_loads(page, fastapi_server):
    page.goto(f"{_base_url(fastapi_server)}/register")
    expect(page).to_have_title("Register")
    expect(page.locator("#registrationForm")).to_be_visible()


@pytest.mark.e2e
def test_dashboard_redirects_if_not_logged_in(page, fastapi_server):
    page.goto(f"{_base_url(fastapi_server)}/dashboard")
    page.wait_for_url("**/login", timeout=5000)


@pytest.mark.e2e
def test_register_success(page, fastapi_server):
    user = _unique_user()
    page.goto(f"{_base_url(fastapi_server)}/register")

    for field in ["username", "email", "first_name", "last_name", "password", "confirm_password"]:
        page.fill(f"#{field}", user[field])

    page.click('button[type="submit"]')
    expect(page.locator("#successAlert")).to_be_visible()
    page.wait_for_url("**/login", timeout=5000)


@pytest.mark.e2e
@pytest.mark.parametrize("username,password,confirm", [
    ("ab", "SecurePass123!", "SecurePass123!"),
    ("validuser", "weak", "weak"),
    ("validuser", "pass1", "pass2"),
])
def test_register_validation_errors(page, fastapi_server, username, password, confirm):
    page.goto(f"{_base_url(fastapi_server)}/register")
    page.fill("#username", username)
    page.fill("#email", "test@example.com")
    page.fill("#first_name", "Test")
    page.fill("#last_name", "User")
    page.fill("#password", password)
    page.fill("#confirm_password", confirm)
    page.click('button[type="submit"]')

    expect(page.locator("#errorAlert")).to_be_visible()


@pytest.mark.e2e
def test_register_duplicate_username(page, fastapi_server):
    user = _unique_user()
    _register_via_ui(page, fastapi_server, user)

    page.goto(f"{_base_url(fastapi_server)}/register")
    for field in user:
        page.fill(f"#{field}", user[field])
    page.click('button[type="submit"]')

    expect(page.locator("#errorAlert")).to_be_visible()


@pytest.mark.e2e
def test_login_success(page, fastapi_server):
    user = _unique_user()
    _register_via_ui(page, fastapi_server, user)
    _login_via_ui(page, fastapi_server, user)

    expect(page).to_have_url(f"{_base_url(fastapi_server)}/dashboard")


@pytest.mark.e2e
def test_login_remember_me(page, fastapi_server):
    user = _unique_user()
    _register_via_ui(page, fastapi_server, user)

    page.goto(f"{_base_url(fastapi_server)}/login")
    page.fill("#username", user["username"])
    page.fill("#password", user["password"])
    page.check("#remember")
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=5000)

    page.goto(f"{_base_url(fastapi_server)}/login")
    expect(page.locator("#username")).to_have_value(user["username"])


@pytest.mark.e2e
def test_dashboard_basic_elements(page, fastapi_server):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    expect(page.locator("#userWelcome")).to_contain_text(user["username"])
    expect(page.locator("#calculationForm")).to_be_visible()
    expect(page.locator("#calculationsTable")).to_be_visible()


@pytest.mark.e2e
def test_dashboard_empty_state(page, fastapi_server):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    expect(page.locator("#calculationsTable")).to_contain_text("No calculations found", timeout=5000)


@pytest.mark.e2e
@pytest.mark.parametrize("calc_type, inputs, expected", [
    ("addition", "10,5", "15"),
    ("subtraction", "20,8", "12"),
    ("multiplication", "4,5", "20"),
    ("division", "100,4", "25"),
])
def test_dashboard_create_calculations(page, fastapi_server, calc_type, inputs, expected):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    page.select_option("#calcType", calc_type)
    page.fill("#calcInputs", inputs)
    page.click('#calculationForm button[type="submit"]')

    expect(page.locator("#calculationsTable")).to_contain_text(calc_type, timeout=5000)
    expect(page.locator("#calculationsTable")).to_contain_text(expected)


@pytest.mark.e2e
def test_dashboard_invalid_inputs(page, fastapi_server):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    page.fill("#calcInputs", "42")
    page.click('#calculationForm button[type="submit"]')

    expect(page.locator("#errorAlert")).to_be_visible()


@pytest.mark.e2e
def test_dashboard_delete(page, fastapi_server):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    page.select_option("#calcType", "addition")
    page.fill("#calcInputs", "3,7")
    page.click('#calculationForm button[type="submit"]')

    page.on("dialog", lambda dialog: dialog.accept())
    page.locator(".delete-calc").first.click()

    expect(page.locator("#calculationsTable")).to_contain_text("No calculations found", timeout=5000)


@pytest.mark.e2e
def test_logout(page, fastapi_server):
    user = _unique_user()
    _register_and_login(page, fastapi_server, user)

    page.on("dialog", lambda dialog: dialog.accept())
    page.click("#logoutBtn")

    page.wait_for_url("**/login", timeout=5000)
