"""Installed packages must not mask failures in repository-owned contracts."""
from tools import check_repository


def test_installed_markdown_is_excluded_but_owned_links_are_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(check_repository, "ROOT", tmp_path)
    installed = tmp_path / "adapters" / "node_modules" / "package"
    installed.mkdir(parents=True)
    (installed / "README.md").write_text("[missing](upstream-only.md)\n")
    owned = tmp_path / "docs"
    owned.mkdir()
    (owned / "README.md").write_text("[missing](broken-owned.md)\n")
    errors = []
    check_repository.check_markdown_links(errors)
    assert len(errors) == 1
    assert "docs/README.md" in errors[0]
    assert "broken-owned.md" in errors[0]


def test_owned_conflicts_remain_detected_with_packages_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(check_repository, "ROOT", tmp_path)
    installed = tmp_path / "node_modules"
    installed.mkdir()
    marker = "<" * 7 + " branch\n"
    (installed / "upstream.py").write_text(marker)
    (tmp_path / "owned.py").write_text(marker)
    errors = []
    check_repository.check_conflict_markers(errors)
    assert errors == ["unresolved merge-conflict marker: owned.py"]
