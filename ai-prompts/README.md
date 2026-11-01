# AI Prompt History and Tool-Use Disclosure

This directory records the AI prompts associated with development of the
Supplier Reliability Scoring Engine. It is included to meet the YottaFlex
candidate-project requirement to disclose prompts submitted to AI tools.

## AI tools and attribution

| Tool | What is recorded here | Attribution status |
|---|---|---|
| **Gemini** | Prompts 1–3: database schema/tests, synthetic data generation, and generator corrections | Identified by the candidate as prompts sent to Gemini; retained as original prompt text |
| **ChatGPT** | Project FAQ interpretation and preparation of the prompt-history documentation | Used for documentation support; these interactions did not implement the supplier scoring project |
| **Other AI tools** | No additional tool attribution is confirmed in the retained records | Add the tool and its prompts if any other AI tool was used |

**Important:** Do not infer that a prompt was sent to Gemini, ChatGPT, or another
tool unless the original conversation or a reliable record confirms it.

## Prompt inventory

| File | Development stage | Record type | AI tool |
|---|---|---|---|
| [01_database_schema.md](01_database_schema.md) | Database schema and tests | Original prompt | Gemini |
| [02_synthetic_data_generator.md](02_synthetic_data_generator.md) | Synthetic data generator | Original prompt | Gemini |
| [03_generator_corrections.md](03_generator_corrections.md) | Generator debugging and validation | Original prompt | Gemini |
| [04_scoring_engine.md](04_scoring_engine.md) | Supplier scoring engine | Reconstructed summary prompt | Not verified |
| [05_evaluation_and_testing.md](05_evaluation_and_testing.md) | Ground truth, evaluation, and testing | Reconstructed summary prompt | Not verified |
| [06_documentation_and_ci.md](06_documentation_and_ci.md) | Documentation, reproducibility, and CI | Reconstructed summary prompt | Not verified |

## Original and reconstructed records

- Prompts 1–3 are retained as original prompt text supplied by the candidate.
- Prompts 4–6 are **reconstructed summaries from the project-development history**.
  They are not claimed to be verbatim historical prompts, and their original
  AI-tool attribution has not been verified.
- If the original prompt text or tool attribution becomes available, replace
  the reconstructed record with the exact prompt and identify the tool.
- Do not silently relabel reconstructed prompts as original or verbatim.

## How AI assistance was used

AI tools were used as development assistance for planning, code review,
implementation guidance, debugging, test design, documentation, and CI
workflow guidance. The candidate remains responsible for reviewing the code,
running the project, validating outputs, understanding design choices, and
explaining limitations.

The repository's tests and GitHub Actions results provide evidence of the
checks actually run; they do not replace the candidate's responsibility to
understand and own the submission.

## Updating this history

If any additional AI tool or editor-integrated assistant was used, add:
1. Tool name and model/version, if known.
2. Date/time, if available.
3. Exact prompt submitted.
4. A clear note if the prompt had to be reconstructed or could not be exported.

Do not include API keys, passwords, access tokens, personal sensitive
information, or proprietary material in prompt records.
