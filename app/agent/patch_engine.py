
"""Apply validated exact-text patches inside an isolated workspace."""

import os
import tempfile
from pathlib import Path

from app.agent.schemas import PatchOperation


MAX_FILE_SIZE = 1_000_000
ALLOWED_PATCH_PATHS = frozenset({"checkout.html"})


class PatchError(RuntimeError):
    """Raised when a patch is unsafe or cannot be applied."""


def apply_patch(
    workspace_root: Path,
    operation: PatchOperation,
) -> dict:
    """Apply one exact replacement inside an existing isolated workspace.

    Only explicitly allowed files can be modified. The caller is responsible
    for creating the workspace as a temporary copy. This function never
    intentionally modifies the original project.
    """

    root = Path(workspace_root)

    # 1. Validate the workspace.
    if root.is_symlink():
        raise PatchError("Workspace root cannot be a symlink.")

    if not root.exists() or not root.is_dir():
        raise PatchError("Workspace does not exist or is not a directory.")

    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PatchError("Workspace could not be resolved.") from exc

    # 2. Validate the supplied relative path.
    relative_path = Path(operation.path)

    if relative_path.is_absolute():
        raise PatchError("Absolute paths are not permitted.")

    if (
        not relative_path.parts
        or any(part in ("", ".", "..") for part in relative_path.parts)
    ):
        raise PatchError("Unsafe relative path.")

    # 3. Walk the path and reject symlinks before applying the allowlist.
    target = root

    for part in relative_path.parts:
        target = target / part

        if target.is_symlink():
            raise PatchError("Symlinks are not permitted in patch paths.")

    # 4. Enforce the file allowlist independently of upstream validation.
    if operation.path not in ALLOWED_PATCH_PATHS:
        raise PatchError("Patch target is not in the allowed file list.")

    # 5. Resolve and validate the target.
    try:
        resolved_target = target.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PatchError("Patch target could not be resolved.") from exc

    if not resolved_target.is_relative_to(resolved_root):
        raise PatchError("Patch target escapes the workspace.")

    if not resolved_target.is_file():
        raise PatchError("Patch target must be an existing regular file.")

    # 6. Read the target safely.
    try:
        if resolved_target.stat().st_size > MAX_FILE_SIZE:
            raise PatchError("Patch target exceeds the maximum file size.")

        original = resolved_target.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as exc:
        raise PatchError("Patch target is not readable UTF-8 text.") from exc

    # 7. Require exactly one occurrence of the original text.
    occurrences = original.count(operation.old_text)

    if occurrences == 0:
        raise PatchError("Original text was not found; patch not applied.")

    if occurrences != 1:
        raise PatchError(
            f"Patch is ambiguous: original text occurs {occurrences} times."
        )

    updated = original.replace(
        operation.old_text,
        operation.new_text,
        1,
    )

    # 8. Write to a temporary file, then atomically replace the target.
    temporary_path = None
    file_descriptor = None

    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".si-orbit-patch-",
            dir=str(resolved_target.parent),
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            file_descriptor = None
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_path, resolved_target)
        temporary_path = None

    except OSError as exc:
        raise PatchError("Could not safely write the patched file.") from exc

    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)

        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "status": "applied",
        "path": operation.path,
        "replacements": 1,
        "original_size": len(original),
        "updated_size": len(updated),
    }
