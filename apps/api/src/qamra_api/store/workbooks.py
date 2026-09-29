"""Activity books (Addendum 9, WorkbookProduct): who can order what.

`orderable` is a product flag in `CatalogProduct.features`, switched in Admin → الكتالوج (products tab).
When it is missing, a product is orderable, except the educational lines («دوسية التأسيس» and
«رحلتي الأولى للتعلّم»): they stay «قريبًا» until the educator signs them off (Tareq's decision,
2026-09-29). The cart refuses a product that is not orderable, whichever page sent it.
"""

from qamra_core.db.store import CatalogProduct

EDUCATIONAL = ("workbook", "journey")
ACTIVITY = ("workbook", "journey", "family")


def orderable(product: CatalogProduct) -> bool:
    flag = (product.features or {}).get("orderable")
    if flag is None:
        return product.line.value not in EDUCATIONAL
    return bool(flag)
