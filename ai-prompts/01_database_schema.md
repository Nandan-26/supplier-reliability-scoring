> **AI tool:** Gemini (identified by the candidate). **Record status:** original prompt text.

# Original Prompt 1 — Database Schema and Tests

ME TO GEMINI
------------------------------------

I reviewed the updated files. The schema is getting closer, and I want to finish the database checks before starting the synthetic data generator.

Please make these final corrections:

1. Add an explicit test confirming that foreign-key enforcement is enabled on every connection.
2. Add a test proving that an invoice cannot reference a PO line belonging to a different purchase order. Right now, the invoice and PO-line foreign keys are separate, so please check whether the schema truly enforces that relationship.
3. Keep the existing tests for table creation, supplier-site consistency, supplier-contract consistency, and invalid inspection quantities.
4. Make the test database and schema paths relative to the project root, so the tests work reliably when run from the project folder.
5. Use a `try/finally` cleanup pattern for the test database.
6. Review the date rules carefully. Delivery events must not occur before dispatch, and inspections must not occur before delivery. Add database triggers where appropriate, or clearly explain which cross-table date checks belong in the data validator. Keep ISO-formatted dates consistent.
7. Keep intentionally malformed records available for anomaly-detection tests through staging or raw test inputs. Don't make the core database so strict that we cannot demonstrate detection and quarantine.
8. Show me the complete revised `data/schema.sql`, `src/db.py`, and `tests/test_db.py`, along with the exact Windows commands to run the tests.

Please keep this simple enough for a beginner to understand. Explain what changed and why. Do not start the synthetic data generator yet, and do not claim that tests pass unless you have actually run them.