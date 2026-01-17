"""Initialize a new RAG2F plugin repo cloned from this template.

This script renames the Python import package, distribution name, and plugin id
across the repository and renames the package folder under src/.

Designed to be run once after copying the template.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_IMPORT_NAME = "rag2f_plugin_template"
TEMPLATE_PACKAGE_NAME = "rag2f-plugin-template"


_IMPORT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class RenamePlan:
    import_name: str
    package_name: str
    plugin_id: str
    description: str | None
    display_name: str | None


def _validate(plan: RenamePlan) -> None:
    if not _IMPORT_RE.fullmatch(plan.import_name):
        raise SystemExit(
            "Invalid --import-name. Expected a valid Python identifier like 'rag2f_my_plugin'."
        )
    if not _PACKAGE_RE.fullmatch(plan.package_name):
        raise SystemExit(
            "Invalid --package-name. Expected PEP 508-ish name like 'rag2f-my-plugin'."
        )
    if not plan.plugin_id:
        raise SystemExit("Invalid --plugin-id (cannot be empty)")

    if plan.plugin_id != plan.import_name:
        raise SystemExit(
            "For this template, --plugin-id must match --import-name to keep Spock config keys, "
            "tests, and plugin registration consistent."
        )


def _is_text_file(path: Path) -> bool:
    if path.is_dir():
        return False
    if "/.git/" in str(path):
        return False

    # keep it simple: treat common source/config files as text
    return path.suffix in {
        ".py",
        ".toml",
        ".json",
        ".jsonc",
        ".yml",
        ".yaml",
        ".md",
        ".txt",
        ".sh",
        ".cfg",
        ".in",
        "",
    } or path.name in {"LICENSE", "NEXT_VERSION"}


def _replace_in_files(root: Path, replacements: dict[str, str], *, dry_run: bool) -> list[Path]:
    changed: list[Path] = []
    for path in root.rglob("*"):
        if not _is_text_file(path):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue

        new_text = text
        for old, new in replacements.items():
            new_text = new_text.replace(old, new)

        if new_text != text:
            changed.append(path)
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")

    return changed


def _rename_package_dir(root: Path, plan: RenamePlan, *, dry_run: bool) -> None:
    src_dir = root / "src"
    old_dir = src_dir / TEMPLATE_IMPORT_NAME
    new_dir = src_dir / plan.import_name

    if not old_dir.exists():
        # Template may already have been renamed or customized.
        if new_dir.exists():
            return
        raise SystemExit(f"Expected template package folder at {old_dir}")

    if old_dir.resolve() == new_dir.resolve():
        return

    if new_dir.exists():
        raise SystemExit(f"Target package folder already exists: {new_dir}")

    if dry_run:
        return

    old_dir.rename(new_dir)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a repo copied from rag2f_plugin_template"
    )
    parser.add_argument(
        "--import-name", required=True, help="Python import package, e.g. rag2f_my_plugin"
    )
    parser.add_argument(
        "--package-name", required=True, help="Distribution name, e.g. rag2f-my-plugin"
    )
    parser.add_argument(
        "--plugin-id",
        default=None,
        help="Plugin id / entry point key (default: same as --import-name)",
    )
    parser.add_argument(
        "--description", default=None, help="Project description (updates pyproject.toml)"
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Human-readable plugin name (updates plugin.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")

    args = parser.parse_args()
    plan = RenamePlan(
        import_name=args.import_name,
        package_name=args.package_name,
        plugin_id=args.plugin_id or args.import_name,
        description=args.description,
        display_name=args.display_name,
    )
    _validate(plan)

    root = Path(__file__).resolve().parents[1]

    replacements = {
        TEMPLATE_IMPORT_NAME: plan.import_name,
        TEMPLATE_PACKAGE_NAME: plan.package_name,
    }

    # Update text files first, then rename directory.
    changed = _replace_in_files(root, replacements, dry_run=args.dry_run)
    _rename_package_dir(root, plan, dry_run=args.dry_run)

    # Entry point key is a bit special: change "rag2f_plugin_template = ..." to "<plugin_id> = ...".
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        new_text = re.sub(
            rf'^(\s*){re.escape(plan.import_name)}\s*=\s*"{re.escape(plan.import_name)}:get_plugin_path"\s*$',
            rf'\g<1>{plan.plugin_id} = "{plan.import_name}:get_plugin_path"',
            text,
            flags=re.MULTILINE,
        )
        if new_text != text:
            if not args.dry_run:
                pyproject.write_text(new_text, encoding="utf-8")
            if pyproject not in changed:
                changed.append(pyproject)

        if plan.description:
            text2 = pyproject.read_text(encoding="utf-8")
            new_text2 = re.sub(
                r'^(\s*description\s*=\s*)"[^"]*"\s*$',
                rf'\g<1>"{plan.description}"',
                text2,
                flags=re.MULTILINE,
            )
            if new_text2 != text2:
                if not args.dry_run:
                    pyproject.write_text(new_text2, encoding="utf-8")
                if pyproject not in changed:
                    changed.append(pyproject)

    plugin_json = root / "plugin.json"
    if plugin_json.exists() and plan.display_name:
        text = plugin_json.read_text(encoding="utf-8")
        new_text = re.sub(
            r'^(\s*"name"\s*:\s*)"[^"]*"(\s*,?)\s*$',
            rf'\g<1>"{plan.display_name}"\g<2>',
            text,
            flags=re.MULTILINE,
        )
        if new_text != text:
            if not args.dry_run:
                plugin_json.write_text(new_text, encoding="utf-8")
            if plugin_json not in changed:
                changed.append(plugin_json)

    print("\n".join(str(p.relative_to(root)) for p in sorted(set(changed))))
    if args.dry_run:
        print(f"\nDry run: {len(set(changed))} files would change.")
    else:
        print(f"\nDone: updated {len(set(changed))} files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
