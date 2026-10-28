"""Erros de negócio traduzidos em resposta HTTP."""


class AppError(Exception):
    """Falha esperada (credencial, convite, permissão) com status HTTP."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
