"""Fail-fast secret resolution shared by the backend and frontend.

Candidate for upstreaming into ``aiweb_common`` alongside ``manage_sensitive``.
"""

from aiweb_common.WorkflowHandler import manage_sensitive


def require_secret(name: str) -> str:
    """Resolve a secret via ``manage_sensitive`` and fail fast if it is empty.

    A freshly copied ``.env.example`` defines every variable with an empty
    value, which Compose happily delivers as an empty Docker secret. Without
    this check that only surfaces later as an opaque auth failure on the first
    API call.

    Args:
      name: Secret name, e.g. ``"libkey_api_key"``.

    Returns:
      The non-empty secret value.

    Raises:
      RuntimeError: If the secret resolves to an empty or whitespace-only
        value.
      KeyError: If the secret is not found in any source (raised by
        ``manage_sensitive``).
    """
    value = manage_sensitive(name)
    if not value.strip():
        raise RuntimeError(
            f"Secret '{name}' is empty. Fill in its value in .env (see .env.example) "
            "or in your secrets files before starting the app."
        )
    return value
