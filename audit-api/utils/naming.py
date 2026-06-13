"""Display-name helpers.

Clerk does not require a name at sign-up, so invited users can land in the
mirror with null first/last names. Fall back to the email local-part (and then
a caller-supplied fallback) so the UI never shows a blank where a person
should be.
"""


def display_name(
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    fallback: str | None = None,
) -> str | None:
    """Best human-readable name: full name → email local-part → fallback."""
    full = " ".join(part for part in (first_name, last_name) if part)
    if full:
        return full
    if email:
        return email.split("@", 1)[0]
    return fallback
