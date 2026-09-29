"""The school's children list: Arabic or English headers, Excel's two CSV encodings, friendly row reasons."""

import pytest

from qamra_api.portal.importer import check_row, decode, parse_csv, preview, template_csv


def test_arabic_excel_csv_in_windows_1256_and_semicolons_read_right() -> None:
    data = "اسم الطفل;الجنس;العمر;الجوال\nيوسف;ولد;5;0599123456\n".encode("cp1256")
    rows = parse_csv(decode(data))
    assert rows == [{"name": "يوسف", "gender": "ولد", "age": "5", "phone": "0599123456"}]
    english = parse_csv(decode(b"Child name,Sex,Birth year,Parent email\nAdam,boy,2021,a@b.co\n"))
    assert english == [{"name": "Adam", "gender": "boy", "birth_year": "2021", "email": "a@b.co"}]


def test_the_template_is_utf8_with_a_bom_and_reads_back() -> None:
    data = template_csv()
    assert data.startswith("﻿".encode())
    [row] = parse_csv(decode(data))
    assert check_row(row, 2, today=2026).ok


def test_a_file_without_a_name_column_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_csv("a,b\n1,2\n")


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"name": "", "gender": "ولد", "age": "5", "phone": "0599123456"}, "اسم الطفل فارغ"),
        ({"name": "سلمى", "gender": "؟", "age": "5", "phone": "0599123456"}, "الجنس غير واضح"),
        ({"name": "سلمى", "gender": "بنت", "age": "14", "phone": "0599123456"}, "سنة الميلاد"),
        ({"name": "سلمى", "gender": "بنت", "age": "5"}, "جوال ولي الأمر أو بريده"),
        ({"name": "سلمى", "gender": "بنت", "age": "5", "email": "not-an-email"}, "البريد"),
    ],
)
def test_rows_explain_what_is_wrong_in_arabic_and_english(values: dict[str, str], reason: str) -> None:
    row = check_row(values, 3, today=2026)
    assert not row.ok and reason in row.errors[0]["ar"] and row.errors[0]["en"]


def test_arabic_indic_digits_and_duplicates() -> None:
    [row] = preview(
        [{"name": "جنى", "gender": "أنثى", "birth_year": "٢٠٢١", "phone": "٠٥٩٩١٢٣٤٥٦"}], ["جنى"], 2026
    )
    assert row.ok and row.birth_year == 2021 and row.phone == "0599123456" and row.gender == "f"
    assert any("مكرّر" in w["ar"] for w in row.warnings)
