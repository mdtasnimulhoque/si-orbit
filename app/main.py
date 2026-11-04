
import logging
import os
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app.investigator import investigate_checkout
from app.reasoning_stage import add_ai_reasoning
from app.agent.repair_loop import run_repair_cycle
from app.meta_model_client import diagnose_custom_evidence, propose_repair, MetaModelError

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
CHECKOUT_PAGE = BASE_DIR / "fixtures" / "buggy_sites" / "checkout.html"

app = FastAPI(
    title="SI ORBIT",
    description="An evidence-driven agent for investigating web UI bugs.",
    version="0.2.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


class InvestigationRequest(BaseModel):
    mode: Literal["checkout", "agent_checkout", "custom_evidence"] = "checkout"
    html_path: str | None = None
    enable_ai_reasoning: bool = False

    problem_description: str = Field(default="", max_length=5000)
    error_logs: str = Field(default="", max_length=10000)
    source_code: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def validate_request(self):
        if self.html_path is not None:
            raise ValueError(
                "Custom filesystem paths are not accepted. "
                "Use checkout mode or submit text evidence."
            )

        if (
            self.mode == "custom_evidence"
            and not self.problem_description.strip()
        ):
            raise ValueError(
                "Describe the problem before submitting custom evidence."
            )

        return self


def analyze_custom_evidence(request: InvestigationRequest) -> dict:
    """Analyze submitted text without executing the supplied source code."""
    description = request.problem_description.strip()
    logs = request.error_logs.strip()
    code = request.source_code.strip()

    observations = ["A problem description was provided."]
    next_steps = []

    if logs:
        observations.append("Error messages or logs were provided.")

        error_lines = [
            line.strip()
            for line in logs.splitlines()
            if line.strip()
        ]

        if error_lines:
            observations.append(
                f"The submitted logs contain {len(error_lines)} "
                "non-empty line(s)."
            )

        if re.search(
            r"\b(TypeError|ReferenceError|SyntaxError|ImportError|"
            r"ModuleNotFoundError|AttributeError|NameError)\b",
            logs,
            re.IGNORECASE,
        ):
            observations.append(
                "The logs contain a recognizable programming exception "
                "name. Inspect the associated message and stack trace "
                "to narrow down the cause."
            )

        if re.search(
            r"\b(404|not found|ECONNREFUSED|ETIMEDOUT|timeout)\b",
            logs,
            re.IGNORECASE,
        ):
            observations.append(
                "The logs contain a possible missing-resource or "
                "connection-failure indicator."
            )
    else:
        next_steps.append(
            "If available, provide the exact error message and relevant stack trace."
        )

    if code:
        observations.append(
            "Source code was provided for static text inspection."
        )

        # Detect simple HTML id="..." and id='...' declarations.
        html_ids = list(
            dict.fromkeys(
                re.findall(
                    r"""\bid\s*=\s*["']([^"']+)["']""",
                    code,
                    re.IGNORECASE,
                )
            )
        )

        # Detect common JavaScript references to element IDs.
        javascript_ids = list(
            dict.fromkeys(
                re.findall(
                    r"""getElementById\(\s*["']([^"']+)["']\s*\)""",
                    code,
                )
                + re.findall(
                    r"""querySelector\(\s*["']#([^"'\s]+)["']\s*\)""",
                    code,
                )
            )
        )

        html_id_set = set(html_ids)
        missing_ids = [
            element_id
            for element_id in javascript_ids
            if element_id not in html_id_set
        ]

        mismatch_detected = bool(missing_ids)

        if mismatch_detected:
            observations.append(
                "Potential HTML/JavaScript ID mismatches were found in "
                "the submitted text. Check whether the HTML and JavaScript "
                "belong to the same page and whether those elements should exist."
            )
            next_steps.append(
                "Check these JavaScript element references against the HTML: "
                + ", ".join(missing_ids)
                + "."
            )
        else:
            observations.append(
                "No missing HTML IDs were detected by the limited "
                "ID-reference check. This does not rule out other bugs."
            )

        source_check = {
            "html_ids": html_ids,
            "javascript_ids": javascript_ids,
            "missing_ids": missing_ids,
            "mismatch_detected": mismatch_detected,
            "finding": (
                "Potential missing HTML element IDs were detected by static "
                "text inspection."
                if mismatch_detected
                else "No missing IDs were detected by this limited check."
            ),
        }
    else:
        source_check = {
            "html_ids": [],
            "javascript_ids": [],
            "missing_ids": [],
            "mismatch_detected": False,
            "finding": (
                "No source code was provided, so source-code checks were skipped."
            ),
        }
        next_steps.append(
            "If relevant, provide the source code surrounding the failing behavior."
        )

    if not next_steps:
        next_steps.append(
            "Reproduce the problem and collect a complete error message "
            "or a minimal example to test the leading hypothesis."
        )

    summary = (
        "Preliminary analysis of the supplied description, logs, and source "
        "text. This pass uses limited deterministic checks and does not "
        "establish a verified root cause."
    )

    if len(observations) > 1:
        summary += " " + observations[1]

    return {
        "mode": "custom_evidence",
        "evidence": {
            "page_loaded": False,
            "button_clicked": False,
            "message_text": None,
            "browser_errors": [],
        },
        "source_check": source_check,
        "fix_verification": {
            "attempted": False,
            "passed": False,
            "browser_errors": [],
            "message_text": None,
            "reason": (
                "Custom source code was not executed, and no correction "
                "was applied or verified."
            ),
        },
        "report": {
            "verified_findings": [],
            "hypotheses": [
                "The submitted evidence may help narrow down the problem, "
                "but a root cause cannot be confirmed from these checks alone."
            ],
        },
        "custom_analysis": {
            "summary": summary,
            "observations": observations,
            "next_steps": next_steps,
            "limitations": (
                "This is a preliminary text-based analysis, not a full "
                "debugging engine. It does not execute submitted code, inspect "
                "your filesystem, reproduce the bug, or verify a fix."
            ),
            "description_received": bool(description),
            "logs_received": bool(logs),
            "source_code_received": bool(code),
        },
        "ai_reasoning": {
            "status": "not_requested",
            "analysis": None,
        },
    }


@app.get("/", include_in_schema=False)
def home():
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.is_file():
        raise HTTPException(
            status_code=500,
            detail="Frontend index.html was not found.",
        )

    return FileResponse(index_file)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/investigate")
def run_investigation(request: InvestigationRequest):
    try:
        if request.mode == "custom_evidence":
            result = analyze_custom_evidence(request)

            if request.enable_ai_reasoning:
                if os.getenv("SI_ORBIT_ALLOW_REAL_INFERENCE") != "true":
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Live Muse Spark analysis is disabled. "
                            "Explicitly enable it in the server configuration."
                        ),
                    )

                diagnosis = diagnose_custom_evidence(
                    problem_description=request.problem_description,
                    error_logs=request.error_logs,
                    source_code=request.source_code,
                    static_analysis=result["source_check"],
                )

                result["custom_diagnosis"] = diagnosis.model_dump()
                result["custom_analysis"]["summary"] = diagnosis.summary
                result["custom_analysis"]["next_steps"] = diagnosis.test_plan
                result["report"]["hypotheses"] = [diagnosis.root_cause]
                result["ai_reasoning"] = {
                    "enabled": True,
                    "status": "completed",
                    "analysis": (
                        diagnosis.summary + "\n\n" + diagnosis.root_cause
                    ),
                    "verified": False,
                }

            return result

        if request.mode == "agent_checkout":
            if os.getenv("SI_ORBIT_ALLOW_REAL_INFERENCE") != "true":
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Live Muse Spark repair is disabled. "
                        "Explicitly enable it in the server configuration."
                    ),
                )

            def meta_provider(**kwargs):
                return propose_repair(
                    kwargs["evidence"],
                    kwargs["source_check"],
                    source_text=kwargs["source_text"],
                    attempt=kwargs["attempt"],
                    previous_attempts=kwargs["previous_attempts"],
                )

            meta_provider.model_generated = True

            cycle = run_repair_cycle(CHECKOUT_PAGE, meta_provider)
            evidence = cycle["final_evidence"]
            verified = cycle["verified"]

            proposal_summaries = [
                item.get("summary", "")
                for item in cycle["attempts"]
                if item.get("summary")
            ]

            result = {
                "mode": "checkout",
                "evidence": evidence,
                "source_check": cycle["source_check"],
                "fix_verification": {
                    "attempted": any(
                        item.get("status") in {
                            "patch_applied",
                            "verified",
                            "verification_failed",
                            "patch_rejected",
                        }
                        for item in cycle["attempts"]
                    ),
                    "passed": verified,
                    "browser_errors": evidence.get("browser_errors", []),
                    "message_text": evidence.get("message_text"),
                    "reason": cycle["reason"],
                },
                "report": {
                    "verified_findings": (
                        [cycle["reason"]] if verified else []
                    ),
                    "hypotheses": proposal_summaries or [cycle["reason"]],
                },
                "repair_cycle": cycle,
            }

            return add_ai_reasoning(
                result,
                enabled=request.enable_ai_reasoning,
            )

        result = investigate_checkout(CHECKOUT_PAGE)
        return add_ai_reasoning(
            result,
            enabled=request.enable_ai_reasoning,
        )

    except HTTPException:
        raise
    except MetaModelError as exc:
        logger.warning("Meta repair request unavailable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Meta model inference is unavailable. Check the local API configuration.",
        ) from exc
    except Exception as exc:
        logger.exception("Investigation failed")
        raise HTTPException(
            status_code=500,
            detail="Investigation failed. Check the server log for details.",
        ) from exc
