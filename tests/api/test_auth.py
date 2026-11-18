import pytest

from api.models import ErrorResponse, User
from data.factories import unique_display_name, unique_email, unique_phone


@pytest.mark.api
def test_register_with_email_returns_user_and_session(anon):
    email = unique_email()

    response = anon.register(
        email=email,
        password="secret123",
        display_name=unique_display_name(),
    )

    assert response.status_code == 201, response.text
    user = User.model_validate(response.json())
    assert user.email == email
    assert user.role == "customer"
    assert user.id > 0

    me = anon.me()
    assert me.status_code == 200, me.text
    assert User.model_validate(me.json()).id == user.id


@pytest.mark.api
def test_register_with_phone(anon):
    phone = unique_phone()

    response = anon.register(
        phone=phone,
        password="secret123",
        display_name=unique_display_name(),
    )

    assert response.status_code == 201, response.text
    user = User.model_validate(response.json())
    assert user.phone == phone
    assert user.email == ""


@pytest.mark.api
def test_register_duplicate_email_is_rejected(anon, api_factory):
    email = unique_email()
    assert anon.register(email=email).status_code == 201

    # 换一个客户端 IP，避免触发注册接口的 60 次/分钟限流，
    # 确保 400 来自“邮箱已存在”而不是 429。
    other = api_factory()
    response = other.register(email=email)

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "register_failed"
    assert "already registered" in error.error.message


@pytest.mark.api
@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "", "phone": ""},
        {"email": "not-an-email"},
        {"email": unique_email(), "phone": "123"},
        {"email": unique_email(), "password": "short"},
        {"email": unique_email(), "display_name": ""},
    ],
)
def test_register_rejects_invalid_payload(anon, overrides):
    payload = {
        "email": unique_email(),
        "password": "secret123",
        "display_name": "QA User",
    }
    payload.update(overrides)

    response = anon.register(**payload)

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "register_failed"


@pytest.mark.api
def test_login_with_email(anon):
    email = unique_email()
    assert anon.register(email=email, password="secret123").status_code == 201
    assert anon.logout().status_code == 204

    response = anon.login(email, "secret123")

    assert response.status_code == 200, response.text
    user = User.model_validate(response.json())
    assert user.email == email
    assert anon.me().status_code == 200


@pytest.mark.api
def test_login_with_phone(anon):
    phone = unique_phone()
    assert anon.register(phone=phone, password="secret123").status_code == 201
    assert anon.logout().status_code == 204

    response = anon.login(phone, "secret123")

    assert response.status_code == 200, response.text
    assert User.model_validate(response.json()).phone == phone


@pytest.mark.api
def test_login_with_wrong_password_is_rejected(anon):
    email = unique_email()
    assert anon.register(email=email, password="secret123").status_code == 201
    assert anon.logout().status_code == 204

    response = anon.login(email, "wrong-password")

    assert response.status_code == 401, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "login_failed"


@pytest.mark.api
def test_me_requires_session(anon):
    response = anon.me()

    assert response.status_code == 401
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "unauthorized"


@pytest.mark.api
def test_logout_invalidates_session(anon):
    assert anon.register(email=unique_email()).status_code == 201
    assert anon.me().status_code == 200

    assert anon.logout().status_code == 204
    assert anon.me().status_code == 401
