"""Permissões de grupo (bitflags), no estilo Discord."""


class Perm:
    VIEW_CHANNELS = 1 << 0
    SEND_MESSAGES = 1 << 1
    MANAGE_CHANNELS = 1 << 2
    MANAGE_ROLES = 1 << 3
    MANAGE_GROUP = 1 << 4
    CONNECT_VOICE = 1 << 5
    KICK_MEMBERS = 1 << 6
    ADMINISTRATOR = 1 << 30


MEMBER_PERMS = (
    Perm.VIEW_CHANNELS
    | Perm.SEND_MESSAGES
    | Perm.CONNECT_VOICE
)

ADMIN_PERMS = Perm.ADMINISTRATOR

ROLE_PRESETS = {
    "member": MEMBER_PERMS,
    "admin": ADMIN_PERMS,
}


def has_perm(permissions: int, flag: int) -> bool:
    if permissions & Perm.ADMINISTRATOR:
        return True
    return bool(permissions & flag)
