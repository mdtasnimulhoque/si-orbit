# SI ORBIT

**Evidence-driven investigation of web UI bugs.**

SI ORBIT is an early-stage debugging prototype that investigates a sample checkout-page bug, gathers browser evidence, checks selected source-code issues, and produces a structured investigation report.

It is a learning and engineering project, not yet a general-purpose autonomous debugging agent.

## What it can do

- Inspect a sample checkout page using Playwright.
- Capture browser errors and relevant page behavior.
- Check for certain source-code issues, including element ID mismatches.
- Test a specific element-ID correction against a temporary copy of the sample checkout page using browser verification.
- Produce a structured report containing observations and hypotheses.
- Accept custom problem descriptions, logs, and source-code text for limited static analysis.
- Optionally request AI-assisted reasoning when a compatible model API is configured.

AI-generated suggestions are not proof that a bug or fix has been verified. Browser verification is a separate step.

## How it works

1. Collect evidence from the sample page or user-submitted text.
2. Inspect relevant behavior and source-code details.
3. Generate observations and possible explanations.
4. For the supported element-ID mismatch, test the correction on a temporary copy and check the result in a browser.
5. Return a structured report that distinguishes evidence from hypotheses.

## Requirements

- Python 3.10 or newer
- pip
- Git
- Playwright and its Chromium browser

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/mdtasnimulhoque/si-orbit.git
cd si-orbit
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and the Playwright browser:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run SI ORBIT

Start the local development server:

```bash
uvicorn app.main:app --reload
```

Open the local application at `http://127.0.0.1:8000`.

Additional endpoints:

- Health check: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Keep the development server bound to your local machine unless you have deliberately configured secure deployment.

## API usage

### 1. Run the sample checkout investigation

Send a POST request to `/api/investigate` with:

```json
{
  "mode": "checkout",
  "enable_ai_reasoning": false
}
```

### 2. Submit custom evidence

Send a POST request to `/api/investigate` with text evidence, for example:

```json
{
  "mode": "custom_evidence",
  "problem_description": "The submit button does not show a confirmation.",
  "error_logs": "Example browser error log",
  "source_code": "Example source code",
  "enable_ai_reasoning": false
}
```

Custom evidence is analyzed as text. It is not executed as arbitrary code, and a supplied filesystem path is not accepted as a substitute for evidence.

## Run tests

Run the test suite from the project root:

```bash
python -m pytest -q
```

The test suite covers the current implementation. Passing tests do not establish that an external model API or remote deployment is working.

## Project structure

```text
si-orbit/
├── app/
│   ├── main.py
│   ├── browser_inspector.py
│   ├── investigation_report.py
│   ├── investigator.py
│   ├── meta_model_client.py
│   ├── reasoning_stage.py
│   └── root_cause_verifier.py
├── frontend/
├── tests/
├── fixtures/
├── docs/
├── requirements.txt
└── README.md
```

## Optional model inference

AI-assisted reasoning is optional. The model client requires a compatible API endpoint and valid credentials before it can send a request.

Configure credentials locally in an environment file, if supported by your chosen provider. Never commit API keys, tokens, or other secrets.

The model integration has not been independently verified against a live provider in this project. Check the provider's current official documentation before enabling it. Do not assume that a successful local test proves live API access.

## Optional Modal experiment

The repository includes a minimal Modal smoke test intended to check remote execution. It is not the core investigation workflow and does not yet demonstrate a deployed, production-ready AI workload.

Before running remote code, review your account's available credits, applicable pricing, and potential charges. Do not assume a credit balance makes every operation free.

## Limitations and responsible use

- The browser workflow currently focuses on a sample checkout page.
- Detection and fix verification cover only selected cases.
- Custom evidence analysis is limited and does not replace running or testing a supplied application.
- AI-generated explanations can be incorrect.
- No claim of general-purpose autonomous debugging or production readiness is made.

Do not submit secrets, credentials, private customer information, or sensitive production logs.

## Contributing

Contributions, bug reports, reproducible test cases, and thoughtful feature proposals are welcome.

1. Open an issue describing the problem or proposed improvement.
2. Include reproduction steps and expected versus actual behavior.
3. Add or update tests for behavior changes.
4. Run `python -m pytest -q` before submitting a pull request.
5. Clearly distinguish tested results from assumptions.

Please avoid including secrets or private data in issues and pull requests.

## Project direction

The long-term goal is to make debugging workflows more evidence-driven, reproducible, and useful across development environments. Broader framework support, stronger verification, model-assisted analysis, and carefully evaluated remote execution are possible future directions, not claims about current capabilities.

## License

No license has been specified yet. Until a license is added, do not assume that the repository grants permission to redistribute or reuse its code. A license should be chosen and committed explicitly.

---

Built as an ongoing learning and engineering project.
