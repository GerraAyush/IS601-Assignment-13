import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def base_url(fastapi_server):
    return fastapi_server.rstrip("/")

@pytest.fixture
def client():
    return TestClient(app)

def _register(client, base_url, user_data):
    r = client.post(f"{base_url}/auth/register", json=user_data)
    assert r.status_code == 201, f"Register failed: {r.text}"
    return r.json()


def _login(client, base_url, username, password):
    r = client.post(f"{base_url}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def _user_and_token(client, base_url):
    data = {
        "first_name": "Cover",
        "last_name": "Test",
        "email": f"cover_{uuid4().hex[:8]}@example.com",
        "username": f"covertest_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    _register(client, base_url, data)
    token = _login(client, base_url, data["username"], data["password"])
    return data, token


def test_main_health(client, base_url):
    r = client.get(f"{base_url}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_main_register_success(client, base_url):
    data = {
        "first_name": "Reg",
        "last_name": "User",
        "email": f"reg_{uuid4().hex[:8]}@example.com",
        "username": f"reguser_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    r = client.post(f"{base_url}/auth/register", json=data)
    assert r.status_code == 201
    assert r.json()["username"] == data["username"]


def test_main_register_duplicate_returns_400(client, base_url):
    data = {
        "first_name": "Dup",
        "last_name": "User",
        "email": f"dup_{uuid4().hex[:8]}@example.com",
        "username": f"dupuser_{uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    client.post(f"{base_url}/auth/register", json=data)
    r = client.post(f"{base_url}/auth/register", json=data)
    assert r.status_code == 400


def test_main_register_password_mismatch_returns_422(client, base_url):
    data = {
        "first_name": "X",
        "last_name": "Y",
        "email": "mismatch@example.com",
        "username": "mismatchuser",
        "password": "SecurePass123!",
        "confirm_password": "WrongPass999!",
    }
    r = client.post(f"{base_url}/auth/register", json=data)
    assert r.status_code == 422


def test_main_login_success(client, base_url):
    data, token = _user_and_token(client, base_url)
    assert isinstance(token, str) and len(token) > 0


def test_main_login_wrong_password_returns_401(client, base_url):
    data, _ = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/auth/login",
                      json={"username": data["username"], "password": "WrongPass999!"})
    assert r.status_code == 401


def test_main_login_unknown_user_returns_401(client, base_url):
    r = client.post(f"{base_url}/auth/login",
                      json={"username": "no_such_xyz", "password": "AnyPass123!"})
    assert r.status_code == 401


def test_main_login_response_fields(client, base_url):
    data, _ = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/auth/login",
                      json={"username": data["username"], "password": data["password"]})
    body = r.json()
    for field in ["access_token", "refresh_token", "token_type", "expires_at",
                  "user_id", "username", "email", "first_name", "last_name",
                  "is_active", "is_verified"]:
        assert field in body, f"Missing field: {field}"


def test_main_token_endpoint_success(client, base_url):
    data, _ = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/auth/token",
                      data={"username": data["username"], "password": data["password"]})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_main_token_endpoint_wrong_password_returns_401(client, base_url):
    data, _ = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/auth/token",
                      data={"username": data["username"], "password": "WrongPass999!"})
    assert r.status_code == 401


def test_main_create_addition(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "addition", "inputs": [1, 2, 3]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert r.json()["result"] == 6.0


def test_main_create_subtraction(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "subtraction", "inputs": [10, 3]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert r.json()["result"] == 7.0


def test_main_create_multiplication(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "multiplication", "inputs": [3, 4]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert r.json()["result"] == 12.0


def test_main_create_division(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "division", "inputs": [20, 4]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    assert r.json()["result"] == 5.0


def test_main_create_division_by_zero_returns_422(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "division", "inputs": [10, 0]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_main_create_calculation_invalid_type_returns_422(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.post(f"{base_url}/calculations",
                      json={"type": "modulus", "inputs": [10, 3]},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_main_create_calculation_unauthenticated_returns_401(client, base_url):
    r = client.post(f"{base_url}/calculations",
                      json={"type": "addition", "inputs": [1, 2]})
    assert r.status_code == 401


def test_main_list_calculations(client, base_url):
    _, token = _user_and_token(client, base_url)
    client.post(f"{base_url}/calculations",
                  json={"type": "addition", "inputs": [5, 5]},
                  headers={"Authorization": f"Bearer {token}"})
    r = client.get(f"{base_url}/calculations",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_main_get_calculation_success(client, base_url):
    _, token = _user_and_token(client, base_url)
    cr = client.post(f"{base_url}/calculations",
                       json={"type": "addition", "inputs": [7, 8]},
                       headers={"Authorization": f"Bearer {token}"})
    calc_id = cr.json()["id"]
    r = client.get(f"{base_url}/calculations/{calc_id}",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == calc_id


def test_main_get_calculation_invalid_uuid_returns_400(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.get(f"{base_url}/calculations/not-a-uuid",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_main_get_calculation_not_found_returns_404(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.get(f"{base_url}/calculations/{uuid4()}",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_main_update_calculation_success(client, base_url):
    _, token = _user_and_token(client, base_url)
    cr = client.post(f"{base_url}/calculations",
                       json={"type": "addition", "inputs": [1, 2]},
                       headers={"Authorization": f"Bearer {token}"})
    calc_id = cr.json()["id"]
    r = client.put(f"{base_url}/calculations/{calc_id}",
                     json={"inputs": [10, 20]},
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["result"] == 30.0


def test_main_update_calculation_no_inputs_field(client, base_url):
    """PUT with empty body (inputs=None) still returns 200 and bumps updated_at."""
    _, token = _user_and_token(client, base_url)
    cr = client.post(f"{base_url}/calculations",
                       json={"type": "addition", "inputs": [3, 4]},
                       headers={"Authorization": f"Bearer {token}"})
    calc_id = cr.json()["id"]
    r = client.put(f"{base_url}/calculations/{calc_id}",
                     json={},
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_main_update_calculation_invalid_uuid_returns_400(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.put(f"{base_url}/calculations/not-a-uuid",
                     json={"inputs": [1, 2]},
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_main_update_calculation_not_found_returns_404(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.put(f"{base_url}/calculations/{uuid4()}",
                     json={"inputs": [1, 2]},
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_main_delete_calculation_success(client, base_url):
    _, token = _user_and_token(client, base_url)
    cr = client.post(f"{base_url}/calculations",
                       json={"type": "addition", "inputs": [1, 1]},
                       headers={"Authorization": f"Bearer {token}"})
    calc_id = cr.json()["id"]
    r = client.delete(f"{base_url}/calculations/{calc_id}",
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204


def test_main_delete_calculation_invalid_uuid_returns_400(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.delete(f"{base_url}/calculations/not-a-uuid",
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_main_delete_calculation_not_found_returns_404(client, base_url):
    _, token = _user_and_token(client, base_url)
    r = client.delete(f"{base_url}/calculations/{uuid4()}",
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_main_delete_then_get_returns_404(client, base_url):
    """After deletion, the same ID can no longer be retrieved."""
    _, token = _user_and_token(client, base_url)
    cr = client.post(f"{base_url}/calculations",
                       json={"type": "multiplication", "inputs": [2, 5]},
                       headers={"Authorization": f"Bearer {token}"})
    calc_id = cr.json()["id"]
    client.delete(f"{base_url}/calculations/{calc_id}",
                    headers={"Authorization": f"Bearer {token}"})
    r = client.get(f"{base_url}/calculations/{calc_id}",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404

def test_uvicorn_main_block(monkeypatch):
    import app.main as main_module

    called = {}

    def fake_run(*args, **kwargs):
        called["run"] = True

    monkeypatch.setattr("uvicorn.run", fake_run)

    # simulate running file directly
    main_module.__name__ = "__main__"
    exec(open(main_module.__file__).read(), main_module.__dict__)

    assert called["run"] is True

def test_pages_load(client):
    for route in ["/", "/login", "/register", "/dashboard"]:
        response = client.get(route)
        assert response.status_code == 200

def test_login_invalid(client):
    response = client.post("/auth/login", json={
        "username": "wrong",
        "password": "Wrong123!"
    })
    assert response.status_code == 401

def test_get_calculation_invalid_uuid(client, base_url):
    _, token = _user_and_token(client, base_url)
    response = client.get(f"{base_url}/calculations/invalid-id", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400

def test_get_calculation_not_found(client, base_url):
    _, token = _user_and_token(client, base_url)
    fake_id = "11111111-1111-1111-1111-111111111111"
    response = client.get(f"{base_url}/calculations/{fake_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

def test_update_calculation_type_change(client, base_url):
    _, token = _user_and_token(client, base_url)
    # create first
    res = client.post(f"{base_url}/calculations",
        json={"type": "addition", "inputs": [2, 3]},
        headers={"Authorization": f"Bearer {token}"}
    )
    calc_id = res.json()["id"]

    # update TYPE (triggers recreate branch)
    response = client.put(f"{base_url}/calculations/{calc_id}",
        json={"type": "multiplication", "inputs": [2, 3]},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["type"] == "multiplication"

def test_update_calculation_inputs(client, base_url):
    _, token = _user_and_token(client, base_url)
    res = client.post(f"{base_url}/calculations",
        json={"type": "addition", "inputs": [2, 3]},
        headers={"Authorization": f"Bearer {token}"}
    )
    calc_id = res.json()["id"]

    response = client.put(f"{base_url}/calculations/{calc_id}",
        json={"inputs": [10, 5]},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["result"] == 15

def test_delete_not_found(client, base_url):
    _, token = _user_and_token(client, base_url)
    fake_id = "11111111-1111-1111-1111-111111111111"
    response = client.delete(f"/calculations/{fake_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
