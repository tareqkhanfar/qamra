from qamra_core.db.store import StaffRole
from qamra_core.permissions import allowed


def test_owner_can_do_everything() -> None:
    assert allowed([StaffRole.owner], "settings") and allowed([StaffRole.owner], "books.review")


def test_a_role_grants_a_name_and_everything_under_it() -> None:
    assert allowed([StaffRole.support], "orders.edit") and allowed([StaffRole.support], "orders")
    assert allowed([StaffRole.support], "books.view") and not allowed([StaffRole.support], "books.review")
    assert not allowed([StaffRole.editor], "prices") and allowed([StaffRole.admin], "prices")
    assert not allowed([StaffRole.support], "ordersx")  # a name, not a string prefix


def test_roles_add_up_and_no_roles_means_no_access() -> None:
    assert allowed([StaffRole.production, StaffRole.reviewer], "books.review")
    assert not allowed([], "books.view")
