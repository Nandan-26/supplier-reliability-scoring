> **AI tool:** Not verified from the retained record. **Record status:** reconstructed summary; not a verbatim historical prompt. See [the prompt-history README](README.md).

# Reconstructed Prompt 6 — Documentation, Reproducibility, and CI

I want to prepare the Supplier Reliability Scoring Engine repository for public GitHub presentation and entry-level software/data engineering portfolio review.

Please review the existing project before making changes. Preserve working functionality and avoid unnecessary redesign.

1. Review the repository structure and remove unnecessary duplication or temporary files, without deleting important project evidence.

2. Improve the README so that a new developer can understand:
   - Project purpose and scope
   - Architecture and data flow
   - Database schema
   - Synthetic data generation
   - Scoring methodology
   - Evaluation methodology
   - Validation and anomaly quarantine
   - Installation and execution
   - Testing and reproducibility
   - Limitations and future improvements

3. Ensure all commands work on Windows PowerShell and clearly distinguish development-sized runs from full dataset generation.

4. Review the data dictionary for completeness and consistency with the actual SQL schema. Document columns, data types, constraints, relationships, and important business rules.

5. Add or update a source manifest containing generated artifact paths, timestamps, random seeds, configuration details, and SHA-256 checksums where appropriate.

6. Make reproducibility verifiable. Provide commands or tests to regenerate data and compare stable outputs.

7. Configure GitHub Actions to run the relevant automated checks, including tests, database validation, reproducibility checks, and evaluation checks where appropriate.

8. Ensure CI runs use supported Python versions and install dependencies from requirements.txt.

9. Make CI failures visible and meaningful. Do not hide failed tests or allow validation failures to appear successful.

10. Review GitHub repository presentation: project description, topics, license, contribution guidance, and links to important reports.

11. Check that README claims, reported metrics, manifests, test results, and actual repository artifacts agree. Do not invent successful runs or metrics.

12. Clearly identify synthetic data, assumptions, limitations, and the need for real-world business validation.

13. Provide a final checklist of issues found, changes made, commands to run locally, and any remaining limitations.

Keep the project beginner-friendly, technically accurate, and suitable for a fresher portfolio. Do not claim that CI or tests passed unless the relevant run actually completed successfully.