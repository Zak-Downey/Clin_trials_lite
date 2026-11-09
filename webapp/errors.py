"""API errors: a stable machine-readable `kind` and a human-readable message."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, kind: str, message: str):
        super().__init__(message)
        self.status = status
        self.kind = kind
        self.message = message

    def body(self) -> dict:
        return {"error": {"kind": self.kind, "message": self.message}}


def not_found(message: str = "There is nothing at this address.") -> ApiError:
    return ApiError(404, "not_found", message)
