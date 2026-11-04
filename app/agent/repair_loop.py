"""Evidence-driven repair loop for controlled local HTML fixtures."""

import difflib
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from app.agent.patch_engine import PatchError, apply_patch
from app.agent.schemas import RepairProposal
from app.browser_inspector import inspect_checkout
from app.root_cause_verifier import verify_element_id_mismatch


MAX_ATTEMPTS = 3
SUCCESS_MESSAGE = "Purchase completed successfully!"


def _is_verified(evidence: dict) -> bool:
    """Require functional, regression, and browser-health checks to pass."""

    return (
        evidence.get("page_loaded") is True
        and evidence.get("button_clicked") is True
        and evidence.get("message_text") == SUCCESS_MESSAGE
        and evidence.get("functional_passed") is True
        and evidence.get("regression_passed") is True
        and evidence.get("browser_healthy") is True
        and not evidence.get("browser_errors")
    )


def run_repair_cycle(
    html_path: str | Path,
    proposal_provider: Callable[..., RepairProposal],
    *,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict:
    """Investigate, request proposals, patch a temporary copy, and replay.

    The original fixture is never modified. The proposal provider is
    injected so the same orchestration can use a real model or a test
    provider without confusing the two.
    """

    original_path = Path(html_path).resolve(strict=True)

    if not original_path.is_file() or original_path.suffix.lower() != ".html":
        raise ValueError("A valid local HTML fixture is required.")

    if not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError("max_attempts must be between 1 and 3.")

    original_bytes = original_path.read_bytes()

    initial_evidence = inspect_checkout(original_path)
    source_check = verify_element_id_mismatch(original_path)

    attempts = []
    final_evidence = initial_evidence
    final_status = "inconclusive"
    final_reason = "No repair proposal was accepted."

    with tempfile.TemporaryDirectory(prefix="si-orbit-") as temp_dir:
        workspace = Path(temp_dir)
        working_file = workspace / "checkout.html"
        shutil.copy2(original_path, working_file)

        for attempt_number in range(1, max_attempts + 1):
            try:
                proposal = proposal_provider(
                    evidence=final_evidence,
                    source_check=source_check,
                    source_text=working_file.read_text(encoding="utf-8")[:20000],
                    attempt=attempt_number,
                    previous_attempts=attempts,
                )

                if not isinstance(proposal, RepairProposal):
                    raise TypeError(
                        "Proposal provider must return a RepairProposal."
                    )

            except Exception as exc:
                attempts.append({
                    "attempt": attempt_number,
                    "status": "proposal_error",
                    "error": type(exc).__name__,
                })
                final_status = "inconclusive"
                final_reason = "The proposal provider failed."
                break

            entry = {
                "attempt": attempt_number,
                "decision": proposal.decision,
                "summary": proposal.summary,
                "root_cause": proposal.root_cause,
                "evidence_refs": proposal.evidence_refs,
                "status": "proposal_received",
            }

            if proposal.decision == "need_more_evidence":
                entry["status"] = "needs_more_evidence"
                attempts.append(entry)
                final_status = "inconclusive"
                final_reason = proposal.summary
                break

            if proposal.decision == "cannot_fix":
                entry["status"] = "declined"
                attempts.append(entry)
                final_status = "failed"
                final_reason = proposal.summary
                break

            try:
                patch_result = apply_patch(
                    workspace,
                    proposal.patch,
                )
                entry["patch"] = patch_result
                entry["status"] = "patch_applied"

            except PatchError as exc:
                entry["status"] = "patch_rejected"
                entry["error"] = str(exc)
                attempts.append(entry)
                final_status = "failed"
                final_reason = "The proposed patch failed safety validation."
                break

            final_evidence = inspect_checkout(working_file)
            source_check = verify_element_id_mismatch(working_file)

            entry["verification"] = final_evidence

            if _is_verified(final_evidence):
                entry["status"] = "verified"
                final_status = "verified"
                final_reason = (
                    "The patched copy passed the browser interaction check."
                )
                attempts.append(entry)
                break

            entry["status"] = "verification_failed"
            attempts.append(entry)
            final_status = "failed"
            final_reason = (
                "The patched copy did not pass browser verification."
            )

        patched_text = working_file.read_text(encoding="utf-8")
        original_text = original_bytes.decode("utf-8")

        diff = "".join(difflib.unified_diff(
            original_text.splitlines(keepends=True),
            patched_text.splitlines(keepends=True),
            fromfile="original/checkout.html",
            tofile="patched/checkout.html",
        ))

    if original_path.read_bytes() != original_bytes:
        raise RuntimeError("Original fixture changed unexpectedly.")

    return {
        "status": final_status,
        "verified": final_status == "verified",
        "reason": final_reason,
        "model_generated": bool(
            getattr(proposal_provider, "model_generated", False)
            and any(item.get("decision") for item in attempts)
        ),
        "attempt_count": len(attempts),
        "attempts": attempts,
        "initial_evidence": initial_evidence,
        "final_evidence": final_evidence,
        "source_check": source_check,
        "patch_diff": diff,
        "original_unchanged": True,
    }
