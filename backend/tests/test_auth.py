"""Auth: convite obrigatório, sessão e painel de admin."""

from datetime import timedelta

from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME
from app.db.session import SessionLocal
from app.models import Group, GroupMember, InviteCode, User
from app.utils.time import utcnow
from sqlalchemy import func, select

from tests.helpers import user_by_name

NEW_PASSWORD = "SenhaForte1"


def _login(client, login: str = ADMIN_USERNAME, password: str = ADMIN_PASSWORD):
    return client.post("/api/auth/login", json={"login": login, "password": password})


def _register(
    client,
    code: str,
    username: str = "novo",
    email: str = "novo@example.com",
    password: str = NEW_PASSWORD,
    nickname: str = "Novo",
):
    return client.post(
        "/api/auth/register",
        json={
            "invite_code": code,
            "username": username,
            "email": email,
            "password": password,
            "nickname": nickname,
        },
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(client) -> str:
    return _login(client).json()["tokens"]["access_token"]


def _criar_convite(client, days: int = 7) -> str:
    response = client.post(
        "/api/auth/invites",
        headers=_auth(_admin_token(client)),
        json={"expires_in_days": days},
    )
    assert response.status_code == 201
    return response.json()["code"]


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_seed_so_admin_juninho(client, seeded):
    response = _login(client, "Juninho")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "juninho"
    assert body["user"]["nickname"] == "Juninho"
    assert body["user"]["is_admin"] is True
    assert "hashed_password" not in body["user"]

    db = SessionLocal()
    try:
        total = db.scalar(select(func.count()).select_from(User))
        assert total == 1
        names = set(db.scalars(select(Group.name)).all())
        assert "the-gang" in names
    finally:
        db.close()


def test_login_por_email(client, seeded):
    response = _login(client, "juninho@example.com")
    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True


def test_login_senha_errada_nao_revela_se_o_usuario_existe(client, seeded):
    wrong_user = _login(client, "naoexiste", "qualquer1")
    wrong_password = _login(client, "juninho", "senha-errada")
    assert wrong_user.status_code == 401
    assert wrong_password.status_code == 401
    assert wrong_user.json()["detail"] == wrong_password.json()["detail"]


def test_cadastro_exige_convite(client, seeded):
    response = _register(client, code="GANG-NAOEXISTE")
    assert response.status_code == 400
    assert "Convite" in response.json()["detail"]


def test_cadastro_entra_nos_grupos_publicos(client, seeded):
    admin_token = _admin_token(client)
    created = client.post(
        "/api/groups",
        headers=_auth(admin_token),
        json={"name": "tropa", "description": "time", "is_private": False},
    )
    assert created.status_code == 201
    private = client.post(
        "/api/groups",
        headers=_auth(admin_token),
        json={"name": "staff", "description": "privado", "is_private": True},
    )
    assert private.status_code == 201

    code = _criar_convite(client)
    response = _register(client, code=code.lower())
    assert response.status_code == 201
    user_id = response.json()["user"]["id"]

    db = SessionLocal()
    try:
        memberships = db.scalars(
            select(GroupMember).where(GroupMember.user_id == user_id)
        ).all()
        group_ids = [item.group_id for item in memberships]
        names = set(db.scalars(select(Group.name).where(Group.id.in_(group_ids))).all())
        assert "tropa" in names
        assert "the-gang" in names
        assert "staff" not in names
        stored = db.get(User, user_id)
        assert stored is not None
        assert stored.hashed_password.startswith("$2b$12$")
    finally:
        db.close()


def test_edita_perfil(client, seeded):
    token = _admin_token(client)
    response = client.patch(
        "/api/users/me",
        headers=_auth(token),
        json={"nickname": "Juninho FF", "username": "juninho_ff"},
    )
    assert response.status_code == 200
    assert response.json()["nickname"] == "Juninho FF"
    assert response.json()["username"] == "juninho_ff"
    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.json()["nickname"] == "Juninho FF"

    cleared = client.delete("/api/users/me/avatar", headers=_auth(token))
    assert cleared.status_code == 200
    assert cleared.json()["avatar_url"] is None


def test_membro_nao_cria_grupo(client, seeded):
    code = _criar_convite(client)
    member = _register(client, code=code, username="cria", email="cria@example.com")
    token = member.json()["tokens"]["access_token"]
    response = client.post(
        "/api/groups",
        headers=_auth(token),
        json={"name": "memes", "description": "risada", "is_private": False},
    )
    assert response.status_code == 403
    listing = client.get("/api/groups", headers=_auth(token))
    assert all(item["name"] != "memes" for item in listing.json())
    assert any(item["name"] == "the-gang" for item in listing.json())


def test_convite_usado_nao_serve_de_novo(client, seeded):
    code = _criar_convite(client)
    assert _register(client, code=code).status_code == 201
    again = _register(client, code=code, username="outro", email="outro@example.com")
    assert again.status_code == 400


def test_usuario_duplicado(client, seeded):
    code = _criar_convite(client)
    response = _register(client, code=code, username="juninho", email="outro@example.com")
    assert response.status_code == 409


def test_convite_expirado(client, seeded):
    db = SessionLocal()
    try:
        admin = user_by_name(db, ADMIN_USERNAME)
        db.add(
            InviteCode(
                code="GANG-EXPIRADO",
                created_by=admin.id,
                used_by=None,
                used_at=None,
                expires_at=utcnow() - timedelta(days=1),
                created_at=utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()

    response = _register(client, code="GANG-EXPIRADO")
    assert response.status_code == 400


def test_me_e_rotacao_de_refresh(client, seeded):
    logged = _login(client)
    tokens = logged.json()["tokens"]
    me = client.get("/api/auth/me", headers=_auth(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["username"] == "juninho"

    as_refresh = client.get("/api/auth/me", headers=_auth(tokens["refresh_token"]))
    assert as_refresh.status_code == 401

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()["tokens"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reused = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    family = client.post("/api/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert family.status_code == 401


def test_logout_revoga_refresh_e_access_curto_ainda_passa(client, seeded):
    tokens = _login(client).json()["tokens"]
    logout = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 204
    refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
    me = client.get("/api/auth/me", headers=_auth(tokens["access_token"]))
    assert me.status_code == 200


def test_so_admin_cria_e_lista_convite(client, seeded):
    code = _criar_convite(client, days=3)
    member = _register(client, code=code, username="membro", email="membro@example.com")
    assert member.status_code == 201
    member_token = member.json()["tokens"]["access_token"]

    forbidden = client.post(
        "/api/auth/invites",
        headers=_auth(member_token),
        json={"expires_in_days": 3},
    )
    assert forbidden.status_code == 403

    admin = _admin_token(client)
    created = client.post(
        "/api/auth/invites",
        headers=_auth(admin),
        json={"expires_in_days": 3},
    )
    assert created.status_code == 201
    assert created.json()["code"].startswith("GANG-")
    assert created.json()["used_by"] is None

    listing = client.get("/api/auth/invites", headers=_auth(admin))
    assert listing.status_code == 200
    assert len(listing.json()) >= 2


def test_login_rate_limit(client):
    statuses = []
    for _ in range(6):
        response = _login(client, "ninguem", "senha-errada")
        statuses.append(response.status_code)
    assert statuses[-1] == 429
    assert 429 not in statuses[:-1]


def test_stubs_de_fase_futura(client, seeded):
    # Sem token → 401. Com token e LiveKit off → 503 / canal inválido.
    assert client.post("/api/voice/token", json={"channel_id": 1}).status_code == 401
    login = _login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    token = login.json()["tokens"]["access_token"]
    voice = client.post(
        "/api/voice/token",
        headers=_auth(token),
        json={"channel_id": 1},
    )
    assert voice.status_code in {403, 404, 503}
    assert client.post("/api/push/subscribe", json={}).status_code in {401, 422}


def test_seed_idempotente(seeded):
    from app.db.seed import run_seed

    db = SessionLocal()
    try:
        assert run_seed(db) is False
        total = db.scalar(select(func.count()).select_from(User))
        assert total == 1
    finally:
        db.close()
