
"""Strict, validated data contracts for SI ORBIT agent proposals."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EvidenceReference = Literal[
    "browser_evidence",
    "source_analysis",
    "source_text",
    "previous_attempts",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchOperation(StrictModel):
    """A narrowly scoped exact-text replacement."""

    operation: Literal["replace_exact"]
    path: str = Field(min_length=1, max_length=240)
    old_text: str = Field(min_length=1, max_length=10000)
    new_text: str = Field(max_length=10000)

    @model_validator(mode="after")
    def validate_replacement(self):
        if self.old_text == self.new_text:
            raise ValueError("Replacement must change the source text.")

        if not self.path.strip():
            raise ValueError("Patch path cannot be empty.")

        if not self.old_text.strip():
            raise ValueError("Original text cannot be blank.")

        return self


class RepairProposal(StrictModel):
    """A model-generated proposal, never proof of a successful repair."""

    decision: Literal[
        "propose_patch",
        "need_more_evidence",
        "cannot_fix",
    ]

    summary: str = Field(min_length=1, max_length=1000)
    root_cause: str = Field(min_length=1, max_length=2000)

    evidence_refs: list[EvidenceReference] = Field(
        default_factory=list,
        max_length=30,
    )

    patch: PatchOperation | None = None

    test_plan: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_decision(self):
        if not self.summary.strip():
            raise ValueError("Summary cannot be blank.")

        if not self.root_cause.strip():
            raise ValueError("Root cause cannot be blank.")

        if self.decision == "propose_patch" and self.patch is None:
            raise ValueError(
                "A patch proposal must contain a patch operation."
            )

        if self.decision != "propose_patch" and self.patch is not None:
            raise ValueError(
                "A patch is only permitted with propose_patch."
            )

        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("Evidence references must be unique.")

        if any(not item.strip() for item in self.test_plan):
            raise ValueError("Test plan entries cannot be blank.")

        return self


class CustomDiagnosis(StrictModel):
    """Structured diagnosis for user-submitted evidence; never a verified fix."""

    decision: Literal[
        "diagnosis",
        "need_more_evidence",
        "cannot_determine",
    ]

    summary: str = Field(min_length=1, max_length=1500)
    root_cause: str = Field(min_length=1, max_length=3000)

    evidence_refs: list[
        Literal[
            "problem_description",
            "error_logs",
            "source_code",
            "static_analysis",
        ]
    ] = Field(default_factory=list, max_length=20)

    confidence: Literal["low", "medium", "high"] = "low"

    suggested_fix: str = Field(default="", max_length=4000)
    replacement_code: str = Field(default="", max_length=10000)

    test_plan: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_diagnosis(self):
        if not self.summary.strip() or not self.root_cause.strip():
            raise ValueError("Diagnosis summary and root cause cannot be blank.")

        if any(not item.strip() for item in self.test_plan):
            raise ValueError("Test plan entries cannot be blank.")

        if self.decision != "diagnosis" and self.replacement_code.strip():
            raise ValueError(
                "Replacement code requires a diagnosis decision."
            )

        return self
