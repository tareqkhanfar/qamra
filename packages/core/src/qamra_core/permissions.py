"""Staff permissions (Addendum 4 §3.6): which role may do what, in one map checked by every admin endpoint.

A permission is a dotted name ("books.review"). A role grants a name and everything under it, so "orders"
covers "orders.view" and "orders.edit". Staff are users with role `admin` (the admin area, with 2FA); their
roles come from `user_staff_roles`.
"""

from collections.abc import Iterable

from qamra_core.db.store import StaffRole

PERMISSIONS: dict[StaffRole, frozenset[str]] = {
    StaffRole.owner: frozenset({"*"}),
    StaffRole.admin: frozenset(
        {"settings", "prices", "catalog", "users", "reports", "orders.view", "books.view", "organizations"}
    ),
    StaffRole.editor: frozenset({"themes", "templates", "workbook", "journey", "books.view"}),
    StaffRole.reviewer: frozenset({"books", "content", "themes.view", "templates.view"}),
    StaffRole.production: frozenset({"print", "shipping", "orders.view", "books.view"}),
    StaffRole.support: frozenset({"orders", "customers", "refunds", "reprints", "books.view"}),
}


def allowed(roles: Iterable[StaffRole], permission: str) -> bool:
    for role in roles:
        grants = PERMISSIONS[role]
        if "*" in grants or any(permission == g or permission.startswith(g + ".") for g in grants):
            return True
    return False
