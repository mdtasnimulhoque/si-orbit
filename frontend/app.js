
const form = document.getElementById("investigation-form");
const runButton = document.getElementById("run-button");
const runButtonText = document.getElementById("run-button-text");
const emptyRunButton = document.getElementById("empty-run-button");
const retryButton = document.getElementById("retry-button");

const emptyState = document.getElementById("empty-state");
const resultsContent = document.getElementById("results-content");
const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");
const resultsStatus = document.getElementById("results-status");

const reportTitle = document.getElementById("report-title");
const reportDescription = document.getElementById("report-description");
const verificationBadge = document.getElementById("verification-badge");
const errorCount = document.getElementById("error-count");
const mismatchStatus = document.getElementById("mismatch-status");
const fixStatus = document.getElementById("fix-status");

const evidenceList = document.getElementById("evidence-list");
const codeComparison = document.getElementById("code-comparison");
const hypothesisText = document.getElementById("hypothesis-text");
const verificationState = document.getElementById("verification-state");
const verificationDetails = document.getElementById("verification-details");
const rawReport = document.getElementById("raw-report");

const enableAiReasoning = document.getElementById("enable-ai-reasoning");
const aiReasoningStatus = document.getElementById("ai-reasoning-status");
const aiReasoningOutput = document.getElementById("ai-reasoning-output");

const targetSelect = document.getElementById("target-select");
const targetDescription = document.getElementById("target-description");
const customEvidenceFields = document.getElementById("custom-evidence-fields");
const problemDescription = document.getElementById("problem-description");
const errorLogs = document.getElementById("error-logs");
const sourceCode = document.getElementById("source-code");
const privacyNote = document.getElementById("privacy-note");

let investigationRunning = false;

function addTextElement(parent, tagName, className, text) {
  const element = document.createElement(tagName);

  if (className) {
    element.className = className;
  }

  element.textContent = text ?? "";
  parent.appendChild(element);

  return element;
}

function isCustomMode() {
  return targetSelect.value === "custom_evidence";
}

function updateInvestigationMode() {
  const customMode = isCustomMode();

  customEvidenceFields.hidden = !customMode;
  problemDescription.required = customMode;

  targetDescription.replaceChildren();

  if (customMode) {
    addTextElement(targetDescription, "span", "target-file-icon", "TEXT");
    addTextElement(
      targetDescription,
      "span",
      "",
      "User-provided evidence",
    );

    privacyNote.replaceChildren();

    addTextElement(privacyNote, "span", "lock-icon", "◇");
    addTextElement(
      privacyNote,
      "span",
      "",
      "Text-based preliminary analysis; no code execution",
    );

    runButtonText.textContent = "Analyze evidence";
  } else {
    addTextElement(targetDescription, "span", "target-file-icon", "HTML");
    addTextElement(
      targetDescription,
      "span",
      "",
      "Built-in reproducible test fixture",
    );
    addTextElement(
      targetDescription,
      "span",
      "target-separator",
      "·",
    );
    addTextElement(targetDescription, "span", "", "Chromium");

    privacyNote.replaceChildren();

    addTextElement(privacyNote, "span", "lock-icon", "◇");
    addTextElement(
      privacyNote,
      "span",
      "",
      "Runs against the local demo fixture",
    );

    runButtonText.textContent = "Run investigation";
  }

  if (customMode) {
    enableAiReasoning.checked = false;
  }
}

function setLoading(isLoading) {
  investigationRunning = isLoading;

  runButton.disabled = isLoading;
  emptyRunButton.disabled = isLoading;
  retryButton.disabled = isLoading;
  targetSelect.disabled = isLoading;

  runButtonText.textContent = isLoading
    ? "Investigating..."
    : isCustomMode()
      ? "Analyze evidence"
      : "Run investigation";

  resultsStatus.textContent = isLoading
    ? "INVESTIGATION RUNNING"
    : "AWAITING INVESTIGATION";

  resultsStatus.classList.toggle("is-running", isLoading);
}

function showError(message) {
  resultsContent.hidden = true;
  emptyState.hidden = true;
  errorPanel.hidden = false;

  errorMessage.textContent =
    message ||
    "An unexpected error occurred. Check the server logs and try again.";

  resultsStatus.textContent = "INVESTIGATION FAILED";
  resultsStatus.classList.remove("is-running");
}

function renderEvidence(evidence) {
  evidenceList.replaceChildren();

  const observations = [
    {
      label: "Page loaded",
      value: evidence.page_loaded ? "Yes" : "No",
      passed: evidence.page_loaded,
    },
    {
      label: "Checkout button clicked",
      value: evidence.button_clicked ? "Yes" : "No",
      passed: evidence.button_clicked,
    },
    {
      label: "Success message",
      value: evidence.message_text || "Empty",
      passed: Boolean(evidence.message_text),
    },
  ];

  for (const item of observations) {
    const row = document.createElement("div");
    row.className = "evidence-item";

    addTextElement(row, "span", "evidence-label", item.label);
    addTextElement(
      row,
      "span",
      item.passed
        ? "evidence-value is-positive"
        : "evidence-value is-negative",
      item.value,
    );

    evidenceList.appendChild(row);
  }

  const browserErrors = Array.isArray(evidence.browser_errors)
    ? evidence.browser_errors
    : [];

  if (browserErrors.length > 0) {
    const heading = addTextElement(
      evidenceList,
      "div",
      "mini-label evidence-error-heading",
      "BROWSER CONSOLE ERRORS",
    );

    heading.setAttribute("aria-label", "Browser errors");

    for (const error of browserErrors) {
      addTextElement(evidenceList, "p", "browser-error-text", error);
    }
  } else {
    addTextElement(
      evidenceList,
      "p",
      "evidence-clean-message",
      "No browser errors were observed during this run.",
    );
  }
}

function renderSourceCheck(sourceCheck) {
  codeComparison.replaceChildren();

  const htmlIds = Array.isArray(sourceCheck.html_ids)
    ? sourceCheck.html_ids
    : [];

  const javascriptIds = Array.isArray(sourceCheck.javascript_ids)
    ? sourceCheck.javascript_ids
    : [];

  const missingIds = Array.isArray(sourceCheck.missing_ids)
    ? sourceCheck.missing_ids
    : [];

  const rows = [
    {
      label: "HTML IDs",
      value: htmlIds.length ? htmlIds.join(", ") : "No IDs detected",
      negative: false,
    },
    {
      label: "JavaScript IDs",
      value: javascriptIds.length
        ? javascriptIds.join(", ")
        : "No IDs detected",
      negative: false,
    },
    {
      label: "Missing from HTML",
      value: missingIds.length ? missingIds.join(", ") : "None detected",
      negative: missingIds.length > 0,
    },
  ];

  for (const item of rows) {
    const row = document.createElement("div");
    row.className = "code-row";

    addTextElement(row, "span", "code-label", item.label);
    addTextElement(
      row,
      "code",
      item.negative
        ? "code-value is-negative"
        : "code-value is-positive",
      item.value,
    );

    codeComparison.appendChild(row);
  }

  if (sourceCheck.finding) {
    addTextElement(
      codeComparison,
      "p",
      "source-finding",
      sourceCheck.finding,
    );
  }
}

function renderVerification(fixVerification, report) {
  verificationDetails.replaceChildren();

  const attempted = Boolean(fixVerification.attempted);
  const passed = Boolean(fixVerification.passed);

  verificationState.textContent = !attempted
    ? "NOT TESTED"
    : passed
      ? "PASSED"
      : "FAILED";

  verificationState.classList.toggle(
    "is-positive",
    attempted && passed,
  );

  verificationState.classList.toggle(
    "is-negative",
    attempted && !passed,
  );

  addTextElement(
    verificationDetails,
    "p",
    "verification-summary",
    attempted
      ? passed
        ? "The proposed correction passed the browser verification test."
        : "The proposed correction did not pass the browser verification test."
      : "No correction was tested.",
  );

  if (fixVerification.reason) {
    addTextElement(
      verificationDetails,
      "p",
      "verification-note",
      fixVerification.reason,
    );
  }

  const verificationErrors = Array.isArray(fixVerification.browser_errors)
    ? fixVerification.browser_errors
    : [];

  addTextElement(
    verificationDetails,
    "div",
    "mini-label",
    "BROWSER ERRORS AFTER CORRECTION",
  );

  if (verificationErrors.length > 0) {
    for (const error of verificationErrors) {
      addTextElement(
        verificationDetails,
        "p",
        "browser-error-text",
        error,
      );
    }
  } else if (attempted && passed) {
    addTextElement(
      verificationDetails,
      "p",
      "verification-clean",
      "No browser errors were observed in the corrected test.",
    );
  } else {
    addTextElement(
      verificationDetails,
      "p",
      "verification-note",
      "No verified error-free result is available.",
    );
  }

  if (fixVerification.message_text) {
    addTextElement(
      verificationDetails,
      "div",
      "mini-label",
      "RESULTING CHECKOUT MESSAGE",
    );

    addTextElement(
      verificationDetails,
      "p",
      "verification-message",
      fixVerification.message_text,
    );
  }

  const findings = Array.isArray(report.verified_findings)
    ? report.verified_findings
    : [];

  if (findings.length > 0) {
    addTextElement(
      verificationDetails,
      "div",
      "mini-label",
      "VERIFIED FINDINGS",
    );

    for (const finding of findings) {
      addTextElement(
        verificationDetails,
        "p",
        "verified-finding",
        finding,
      );
    }
  }
}

function renderAiReasoning(reasoning = {}) {
  const status = reasoning.status ?? "not_requested";

  const messages = {
    not_requested: "AI analysis not requested.",
    blocked_by_safety_gate:
      "Blocked by the server safety gate. No real model request was sent.",
    unavailable:
      "AI analysis is unavailable. The investigation results remain intact.",
    completed:
      "AI analysis completed. Suggestions are not proof of a fix.",
  };

  aiReasoningStatus.textContent =
    messages[status] ?? `AI reasoning status: ${status}`;

  aiReasoningOutput.replaceChildren();

  const analysis = reasoning.analysis;

  if (typeof analysis === "string" && analysis.trim()) {
    addTextElement(
      aiReasoningOutput,
      "p",
      "mini-label",
      "MODEL-ASSISTED ANALYSIS",
    );

    addTextElement(aiReasoningOutput, "p", "", analysis);
    aiReasoningOutput.hidden = false;
  } else {
    aiReasoningOutput.hidden = true;
  }

  if (reasoning.error && status !== "blocked_by_safety_gate") {
    addTextElement(
      aiReasoningOutput,
      "p",
      "verification-note",
      reasoning.error,
    );

    aiReasoningOutput.hidden = false;
  }
}

function renderInvestigation(result) {
  const customMode =
    result.mode === "custom_evidence" || isCustomMode();

  const evidence = result.evidence ?? {};
  const sourceCheck = result.source_check ?? {};
  const fixVerification = result.fix_verification ?? {};
  const report = result.report ?? {};

  emptyState.hidden = true;
  errorPanel.hidden = true;
  resultsContent.hidden = false;

  reportTitle.textContent = customMode
    ? "Custom evidence analysis"
    : "Checkout interaction failure";

  const findings = Array.isArray(report.verified_findings)
    ? report.verified_findings
    : [];

  const hypotheses = Array.isArray(report.hypotheses)
    ? report.hypotheses
    : [];

  if (customMode) {
    reportDescription.textContent =
      result.custom_analysis?.summary ||
      report.summary ||
      "Preliminary analysis of the evidence you provided. Findings have not been verified by executing your code.";

    errorCount.textContent = "N/A";

    mismatchStatus.textContent = sourceCheck.mismatch_detected
      ? "Potential mismatch"
      : "Not checked";

    fixStatus.textContent = "Not tested";

    verificationBadge.textContent = "PRELIMINARY";
    verificationBadge.classList.remove("is-positive");
    verificationBadge.classList.add("is-negative");

    evidenceList.replaceChildren();

    addTextElement(
      evidenceList,
      "p",
      "evidence-clean-message",
      "No browser execution was performed. The analysis uses only the submitted description, logs, and source code.",
    );

    if (result.custom_analysis?.observations?.length) {
      for (const observation of result.custom_analysis.observations) {
        addTextElement(
          evidenceList,
          "p",
          "source-finding",
          observation,
        );
      }
    }

    renderSourceCheck(sourceCheck);

    hypothesisText.textContent = hypotheses.length
      ? hypotheses.join(" ")
      : result.custom_analysis?.next_steps?.join(" ") ||
        "More evidence is needed to establish a likely cause.";

    verificationDetails.replaceChildren();

    verificationState.textContent = "NOT TESTED";
    verificationState.classList.remove("is-positive", "is-negative");

    addTextElement(
      verificationDetails,
      "p",
      "verification-summary",
      "The submitted source code was not executed. No correction has been applied or verified.",
    );

    if (result.custom_analysis?.limitations) {
      addTextElement(
        verificationDetails,
        "p",
        "verification-note",
        result.custom_analysis.limitations,
      );
    }

    renderAiReasoning(result.ai_reasoning);
  } else {
    reportDescription.textContent = findings.length
      ? findings[0]
      : "The investigation completed. Review the observations and verification results below.";

    const browserErrors = Array.isArray(evidence.browser_errors)
      ? evidence.browser_errors
      : [];

    errorCount.textContent = String(browserErrors.length);

    mismatchStatus.textContent = sourceCheck.mismatch_detected
      ? "Detected"
      : "Not detected";

    fixStatus.textContent = !fixVerification.attempted
      ? "Not tested"
      : fixVerification.passed
        ? "Passed"
        : "Failed";

    verificationBadge.textContent = fixVerification.passed
      ? "FIX VERIFIED"
      : "REVIEW REQUIRED";

    verificationBadge.classList.toggle(
      "is-positive",
      Boolean(fixVerification.passed),
    );

    verificationBadge.classList.toggle(
      "is-negative",
      !fixVerification.passed,
    );

    renderEvidence(evidence);
    renderSourceCheck(sourceCheck);

    hypothesisText.textContent = hypotheses.length
      ? hypotheses.join(" ")
      : "No hypothesis was returned by the investigation engine.";

    renderVerification(fixVerification, report);
    renderAiReasoning(result.ai_reasoning);
  }

  rawReport.textContent = JSON.stringify(result, null, 2);

  resultsStatus.textContent = customMode
    ? "PRELIMINARY ANALYSIS COMPLETE"
    : "INVESTIGATION COMPLETE";

  resultsStatus.classList.remove("is-running");
}

async function runInvestigation() {
  if (investigationRunning) {
    return;
  }

  const customMode = isCustomMode();

  if (customMode && !problemDescription.value.trim()) {
    problemDescription.setCustomValidity(
      "Describe the problem before submitting.",
    );
    problemDescription.reportValidity();
    problemDescription.setCustomValidity("");
    problemDescription.focus();
    return;
  }

  const payload = customMode
    ? {
        mode: "custom_evidence",
        problem_description: problemDescription.value.trim(),
        error_logs: errorLogs.value.trim(),
        source_code: sourceCode.value.trim(),
        enable_ai_reasoning: false,
      }
    : {
        mode: "checkout",
        html_path: null,
        enable_ai_reasoning: enableAiReasoning.checked,
      };

  setLoading(true);
  errorPanel.hidden = true;

  try {
    const response = await fetch("/api/investigate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    let result;

    try {
      result = await response.json();
    } catch {
      throw new Error(
        `The server returned an invalid response (HTTP ${response.status}).`,
      );
    }

    if (!response.ok) {
      const detail =
        typeof result.detail === "string"
          ? result.detail
          : `Server returned HTTP ${response.status}.`;

      throw new Error(detail);
    }

    renderInvestigation(result);
  } catch (error) {
    showError(
      error instanceof Error
        ? error.message
        : "Could not connect to the investigation server.",
    );
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runInvestigation();
});

targetSelect.addEventListener("change", updateInvestigationMode);

emptyRunButton.addEventListener("click", () => {
  document.getElementById("investigate").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });

  if (isCustomMode()) {
    problemDescription.focus();
  } else {
    runInvestigation();
  }
});

retryButton.addEventListener("click", runInvestigation);

// Keep the initial form consistent with the selected investigation mode.
updateInvestigationMode();

/* SI ORBIT theme preference: Light / Dark / System */
(() => {
  const key = "si-orbit-theme";
  const allowed = ["light", "dark", "system"];
  const root = document.documentElement;

  let saved = "system";

  try {
    const value = localStorage.getItem(key);

    if (allowed.includes(value)) {
      saved = value;
    }
  } catch (_) {
    // The application works even when browser storage is unavailable.
  }

  root.dataset.theme = saved;

  function mountThemeControl() {
    const host = document.querySelector(".topbar-right");

    if (!host || document.querySelector(".theme-control")) {
      return;
    }

    const group = document.createElement("div");
    group.className = "theme-control";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Color theme");

    const choices = [
      ["light", "Light"],
      ["dark", "Dark"],
      ["system", "System"],
    ];

    function update(value) {
      root.dataset.theme = value;

      try {
        localStorage.setItem(key, value);
      } catch (_) {
        // Theme selection still applies for the current page.
      }

      group.querySelectorAll("button").forEach((button) => {
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.themeChoice === value),
        );
      });
    }

    choices.forEach(([value, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.themeChoice = value;

      button.addEventListener("click", () => update(value));

      group.appendChild(button);
    });

    host.appendChild(group);
    update(saved);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountThemeControl);
  } else {
    mountThemeControl();
  }
})();
