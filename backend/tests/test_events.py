"""Eventos Diário/Intensivo/Campeonato + MVP + stats."""

from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME

NEW_PASSWORD = "SenhaForte1"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin(client) -> str:
    return client.post(
        "/api/auth/login",
        json={"login": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    ).json()["tokens"]["access_token"]


def _member(client, username="membroev") -> tuple[str, int]:
    admin = _admin(client)
    invite = client.post(
        "/api/auth/invites", headers=_auth(admin), json={"expires_in_days": 3}
    ).json()["code"]
    reg = client.post(
        "/api/auth/register",
        json={
            "invite_code": invite,
            "username": username,
            "email": f"{username}@example.com",
            "password": NEW_PASSWORD,
            "nickname": username.title(),
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    return body["tokens"]["access_token"], body["user"]["id"]


def test_fluxo_evento_call_mvp_e_stats(client, seeded):
    admin = _admin(client)
    member_token, member_id = _member(client, username="membroev")
    other_token, _ = _member(client, username="outroev")

    groups = client.get("/api/groups", headers=_auth(admin)).json()
    group = None
    voice = None
    for candidate in groups:
        channels = client.get(
            f"/api/groups/{candidate['id']}/channels", headers=_auth(admin)
        ).json()
        found = next((c for c in channels if c["channel_type"] == "voice"), None)
        if found is not None:
            group = candidate
            voice = found
            break
    assert group is not None and voice is not None

    # membro comum NÃO inicia
    denied_start = client.post(
        "/api/events/start",
        headers=_auth(member_token),
        json={"channel_id": voice["id"], "event_type": "diario"},
    )
    assert denied_start.status_code == 403

    # dono/admin inicia
    started = client.post(
        "/api/events/start",
        headers=_auth(admin),
        json={"channel_id": voice["id"], "event_type": "diario"},
    )
    assert started.status_code == 200
    event = started.json()
    assert event["status"] == "live"
    admin_id = client.get("/api/auth/me", headers=_auth(admin)).json()["id"]
    assert event["owner_id"] == admin_id

    deny = client.post(
        f"/api/events/{event['id']}/finish",
        headers=_auth(other_token),
        json={"placement": 1, "booyah_count": 2, "kills": 15, "points": 40},
    )
    assert deny.status_code == 403

    finished = client.post(
        f"/api/events/{event['id']}/finish",
        headers=_auth(admin),
        json={"placement": 1, "booyah_count": 2, "kills": 15, "points": 40},
    )
    assert finished.status_code == 200
    body = finished.json()
    assert body["status"] == "voting"
    assert body["is_win"] is True

    vote = client.post(
        f"/api/events/{event['id']}/mvp-vote",
        headers=_auth(member_token),
        json={"candidate_id": admin_id},
    )
    assert vote.status_code == 200

    deny_close = client.post(
        f"/api/events/{event['id']}/close-mvp",
        headers=_auth(member_token),
    )
    assert deny_close.status_code == 403

    done = client.post(
        f"/api/events/{event['id']}/close-mvp",
        headers=_auth(admin),
    )
    assert done.status_code == 200
    assert done.json()["mvp_user_id"] == admin_id

    started2 = client.post(
        "/api/events/start",
        headers=_auth(admin),
        json={"channel_id": voice["id"], "event_type": "campeonato"},
    )
    assert started2.status_code == 200
    ev2 = started2.json()
    client.post(
        f"/api/events/{ev2['id']}/finish",
        headers=_auth(admin),
        json={"placement": 2, "booyah_count": 1, "kills": 8, "points": 22},
    )
    client.post(f"/api/events/{ev2['id']}/close-mvp", headers=_auth(admin))

    stats = client.get("/api/events/stats", headers=_auth(admin)).json()
    assert stats["events_total"] >= 2
    assert stats["wins"] >= 1
    assert stats["booyah_total"] >= 3
    assert member_id  # usado no fluxo

    history = client.get(
        f"/api/events/history?group_id={group['id']}",
        headers=_auth(admin),
    )
    assert history.status_code == 200
    body = history.json()
    assert body["events_total"] >= 2
    assert body["points_total"] >= 62
    assert body["kills_avg"] >= 11
    assert body["ranking"][0]["mvp_count"] >= 1

    denied_kick = client.post(
        "/api/voice/kick",
        headers=_auth(member_token),
        json={"channel_id": voice["id"], "user_id": admin_id},
    )
    assert denied_kick.status_code == 403
    self_kick = client.post(
        "/api/voice/kick",
        headers=_auth(admin),
        json={"channel_id": voice["id"], "user_id": admin_id},
    )
    assert self_kick.status_code == 400
