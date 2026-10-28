"""Limite de tentativas por IP. Memória local basta no MVP de um processo."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled=False: o slowapi não injeta X-RateLimit numa resposta
# Pydantic (response_model). O limite de tentativas continua valendo.
limiter = Limiter(key_func=get_remote_address, default_limits=[], headers_enabled=False)
