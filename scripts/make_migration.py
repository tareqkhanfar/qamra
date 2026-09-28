"""Autogenerate a migration against TEST_DATABASE_URL (or DATABASE_URL): `make migration m="add x"`.

Post-processes two known autogenerate quirks:
- enum columns (VARCHAR + CHECK) get their CHECK rendered twice → keep only the naming-convention one;
- FKs marked `use_alter` are emitted inline → move them to `op.create_foreign_key` after all tables.
"""

import os
import re
import sys
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
from qamra_core.migrations import alembic_config

FK_INLINE = re.compile(
    r"\n    sa\.ForeignKeyConstraint\(\['(?P<col>\w+)'\], \['(?P<ref>\w+)\.(?P<refcol>\w+)'\], "
    r"name=op\.f\('(?P<name>\w+)'\), ondelete='(?P<ondelete>[A-Z ]+)', use_alter=True\),"
)


def tidy(path: Path) -> None:
    s = path.read_text()
    s = re.sub(r"\n    sa\.CheckConstraint\([^\n]*, name='[a-z_]+'\),", "", s)
    s = s.replace("native_enum=False, create_constraint=True,", "native_enum=False, create_constraint=False,")
    moved = []
    for m in FK_INLINE.finditer(s):
        table = s[: m.start()].rsplit("op.create_table('", 1)[1].split("'", 1)[0]
        moved.append((table, m))
    for table, m in moved:
        s = s.replace(m.group(0), "")
        up_end = s.index("    # ### end Alembic commands ###")
        s = (
            s[:up_end] + f"    op.create_foreign_key(op.f('{m['name']}'), '{table}', '{m['ref']}', "
            f"['{m['col']}'], ['{m['refcol']}'], ondelete='{m['ondelete']}')\n" + s[up_end:]
        )
        down = s.index("def downgrade() -> None:")
        first = s.index("\n", s.index("# ### commands auto generated", down)) + 1
        s = (
            s[:first]
            + f"    op.drop_constraint(op.f('{m['name']}'), '{table}', type_='foreignkey')\n"
            + s[first:]
        )
    path.write_text(s)


if __name__ == "__main__":
    url = os.environ.get("TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    command.revision(cfg, message=" ".join(sys.argv[1:]) or "change", autogenerate=True)
    head = ScriptDirectory.from_config(cfg).get_current_head()
    [path] = (Path(str(cfg.get_main_option("script_location"))) / "versions").glob(f"*_{head}_*.py")
    tidy(path)
    print(f"tidied {path.name}")
