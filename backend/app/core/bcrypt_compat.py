"""Ajuste para o passlib 1.7 conviver com o pacote bcrypt moderno.

O passlib ainda lê ``bcrypt.__about__``, atributo removido no bcrypt 4.1+.
Mantemos o pin em 4.0.1 no requirements; este gancho evita quebra se a
versão instalada for mais nova.
"""


def ensure_bcrypt_compat() -> None:
    import bcrypt

    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = type(
            "about",
            (),
            {"__version__": getattr(bcrypt, "__version__", "4")},
        )
