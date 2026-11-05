"""Home THE GANG e perfil Free Fire."""

from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME

NEW_PASSWORD = "SenhaForte1"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin(client) -> str:
    return client.post(
        "/api/auth/login",
        json={"login": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    ).json()["tokens"]["access_token"]


def _member(client) -> str:
    admin = _admin(client)
    invite = client.post(
        "/api/auth/invites", headers=_auth(admin), json={"expires_in_days": 3}
    ).json()["code"]
    reg = client.post(
        "/api/auth/register",
        json={
            "invite_code": invite,
            "username": "ffplayer",
            "email": "ffplayer@example.com",
            "password": NEW_PASSWORD,
            "nickname": "FF Player",
        },
    )
    assert reg.status_code == 201
    return reg.json()["tokens"]["access_token"]


def test_home_e_perfil_ff(client, seeded):
    admin = _admin(client)
    home = client.get("/api/home", headers=_auth(admin))
    assert home.status_code == 200
    body = home.json()
    assert body["banner_title"] == "THE GANG"
    assert "online" in body

    patched = client.patch(
        "/api/home",
        headers=_auth(admin),
        json={
            "banner_title": "THE GANG Elite",
            "banner_subtitle": "Scrims toda noite",
            "admin_note": "Hoje tem treino.",
            "next_event_title": "Ranked 22h",
            "next_event_at": None,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["banner_title"] == "THE GANG Elite"

    member = _member(client)
    forbidden = client.patch(
        "/api/home",
        headers=_auth(member),
        json={
            "banner_title": "Hack",
            "banner_subtitle": "",
            "admin_note": "",
            "next_event_title": None,
            "next_event_at": None,
        },
    )
    assert forbidden.status_code == 403

    profile = client.patch(
        "/api/users/me",
        headers=_auth(member),
        json={
            "nickname": "FF Player",
            "username": "ffplayer",
            "ff_id": "99887766",
            "ff_nick": "JuninFF",
            "ff_role": "cpt",
            "ff_region": "BR",
            "banner_theme": "ember",
        },
    )
    assert profile.status_code == 200
    data = profile.json()
    assert data["ff_id"] == "99887766"
    assert data["ff_role"] == "cpt"
    assert data["banner_theme"] == "ember"
