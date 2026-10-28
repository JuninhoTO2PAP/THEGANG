"""Grupos, canais, cargos e permissões."""

from app.core.permissions import Perm, has_perm
from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME

NEW_PASSWORD = "SenhaForte1"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, login: str = ADMIN_USERNAME, password: str = ADMIN_PASSWORD):
    return client.post("/api/auth/login", json={"login": login, "password": password})


def _admin(client) -> str:
    return _login(client).json()["tokens"]["access_token"]


def _member(client) -> str:
    admin = _admin(client)
    invite = client.post(
        "/api/auth/invites", headers=_auth(admin), json={"expires_in_days": 3}
    ).json()["code"]
    reg = client.post(
        "/api/auth/register",
        json={
            "invite_code": invite,
            "username": "membro1",
            "email": "membro1@example.com",
            "password": NEW_PASSWORD,
            "nickname": "Membro",
        },
    )
    assert reg.status_code == 201
    return reg.json()["tokens"]["access_token"]


def test_cria_grupo_com_canais_e_admin(client, seeded):
    token = _admin(client)
    response = client.post(
        "/api/groups",
        headers=_auth(token),
        json={"name": "tropa", "description": "time", "is_private": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "tropa"
    assert has_perm(body["my_permissions"], Perm.ADMINISTRATOR)

    channels = client.get(f"/api/groups/{body['id']}/channels", headers=_auth(token))
    assert channels.status_code == 200
    names = {c["name"] for c in channels.json()}
    types = {c["channel_type"] for c in channels.json()}
    assert "geral" in names
    assert "text" in types and "voice" in types

    roles = client.get(f"/api/groups/{body['id']}/roles", headers=_auth(token)).json()
    assert any(r["name"] == "Admin" for r in roles)
    assert any(r["is_default"] for r in roles)


def test_membro_nao_cria_cargo(client, seeded):
    admin = _admin(client)
    group = client.post(
        "/api/groups",
        headers=_auth(admin),
        json={"name": "base", "is_private": False},
    ).json()
    member = _member(client)

    forbidden = client.post(
        f"/api/groups/{group['id']}/roles",
        headers=_auth(member),
        json={"name": "Mod", "color": "#5865f2", "is_admin": False, "permissions": 0},
    )
    assert forbidden.status_code == 403

    created = client.post(
        f"/api/groups/{group['id']}/roles",
        headers=_auth(admin),
        json={"name": "Mod", "color": "#5865f2", "is_admin": False, "permissions": 3},
    )
    assert created.status_code == 201


def test_admin_cria_canal_e_membro_manda_mensagem(client, seeded):
    admin = _admin(client)
    group = client.post(
        "/api/groups",
        headers=_auth(admin),
        json={"name": "chat", "is_private": False},
    ).json()
    channel = client.post(
        f"/api/groups/{group['id']}/channels",
        headers=_auth(admin),
        json={"name": "avisos", "channel_type": "text"},
    ).json()
    member = _member(client)
    msg = client.post(
        f"/api/channels/{channel['id']}/messages",
        headers=_auth(member),
        json={"content": "salve @juninho"},
    )
    assert msg.status_code == 201
    assert msg.json()["content"] == "salve @juninho"

    edited = client.patch(
        f"/api/messages/{msg.json()['id']}",
        headers=_auth(member),
        json={"content": "salve editado"},
    )
    assert edited.status_code == 200
    assert edited.json()["edited_at"] is not None

    search = client.get(
        f"/api/messages/search?group_id={group['id']}&q=editado",
        headers=_auth(member),
    )
    assert search.status_code == 200
    assert any(m["id"] == msg.json()["id"] for m in search.json())

    invite = client.post(
        f"/api/groups/{group['id']}/invites",
        headers=_auth(admin),
        json={"expires_in_days": 3, "max_uses": 5},
    )
    assert invite.status_code == 201
    assert invite.json()["code"].startswith("GRP-")

    admin_id = client.get("/api/auth/me", headers=_auth(admin)).json()["id"]
    dm = client.post("/api/dm", headers=_auth(member), json={"user_id": admin_id})
    assert dm.status_code == 201
    dm_msg = client.post(
        f"/api/dm/{dm.json()['id']}/messages",
        headers=_auth(member),
        json={"content": "oi no privado"},
    )
    assert dm_msg.status_code == 201

    pwd = client.post(
        "/api/users/me/password",
        headers=_auth(member),
        json={"current_password": NEW_PASSWORD, "new_password": "OutraSenha2"},
    )
    assert pwd.status_code == 204


def test_apaga_grupo_e_protege_padrao(client, seeded):
    admin = _admin(client)
    member = _member(client)
    groups = client.get("/api/groups", headers=_auth(admin)).json()
    default = next(g for g in groups if g["name"] == "the-gang")
    blocked = client.delete(f"/api/groups/{default['id']}", headers=_auth(admin))
    assert blocked.status_code == 400

    created = client.post(
        "/api/groups",
        headers=_auth(admin),
        json={"name": "temporario", "description": "sumir", "is_private": True},
    ).json()
    forbidden = client.delete(f"/api/groups/{created['id']}", headers=_auth(member))
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/groups/{created['id']}", headers=_auth(admin))
    assert deleted.status_code == 204
    listing = client.get("/api/groups", headers=_auth(admin)).json()
    assert all(g["name"] != "temporario" for g in listing)
