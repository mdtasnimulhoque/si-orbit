
import pytest

from app.agent.patch_engine import PatchError, apply_patch
from app.agent.schemas import PatchOperation


def operation(path="checkout.html", old="broken", new="fixed"):
    return PatchOperation(
        operation="replace_exact",
        path=path,
        old_text=old,
        new_text=new,
    )


def test_applies_exact_replacement_inside_workspace(tmp_path):
    target = tmp_path / "checkout.html"
    target.write_text("before broken after", encoding="utf-8")

    result = apply_patch(tmp_path, operation())

    assert target.read_text(encoding="utf-8") == "before fixed after"
    assert result["status"] == "applied"
    assert result["replacements"] == 1


def test_missing_text_is_rejected_without_modification(tmp_path):
    target = tmp_path / "checkout.html"
    target.write_text("nothing to replace", encoding="utf-8")

    with pytest.raises(PatchError, match="not found"):
        apply_patch(tmp_path, operation())

    assert target.read_text(encoding="utf-8") == "nothing to replace"


def test_ambiguous_text_is_rejected(tmp_path):
    target = tmp_path / "checkout.html"
    target.write_text("broken and broken", encoding="utf-8")

    with pytest.raises(PatchError, match="ambiguous"):
        apply_patch(tmp_path, operation())

    assert target.read_text(encoding="utf-8") == "broken and broken"


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.txt",
        "/tmp/outside.txt",
        "nested/../../outside.txt",
    ],
)
def test_unsafe_paths_are_rejected(tmp_path, unsafe_path):
    with pytest.raises(PatchError):
        apply_patch(tmp_path, operation(path=unsafe_path))


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(PatchError):
        apply_patch(tmp_path, operation())


def test_symlink_target_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside-si-orbit-test.txt"
    outside.write_text("broken", encoding="utf-8")

    link = tmp_path / "linked.txt"
    link.symlink_to(outside)

    try:
        with pytest.raises(PatchError, match="Symlinks"):
            apply_patch(tmp_path, operation(path="linked.txt"))

        assert outside.read_text(encoding="utf-8") == "broken"
    finally:
        outside.unlink(missing_ok=True)


def test_rejects_unlisted_file_even_inside_workspace(tmp_path):
    target = tmp_path / "other.html"
    target.write_text("broken", encoding="utf-8")

    with pytest.raises(PatchError, match="allowed file list"):
        apply_patch(
            tmp_path,
            operation(path="other.html"),
        )

    assert target.read_text(encoding="utf-8") == "broken"


def test_original_project_file_is_not_modified(tmp_path):
    original = tmp_path / "original"
    workspace = tmp_path / "workspace"

    original.mkdir()
    workspace.mkdir()

    (original / "checkout.html").write_text("broken", encoding="utf-8")
    (workspace / "checkout.html").write_text("broken", encoding="utf-8")

    apply_patch(workspace, operation())

    assert (original / "checkout.html").read_text(encoding="utf-8") == "broken"
    assert (workspace / "checkout.html").read_text(encoding="utf-8") == "fixed"
