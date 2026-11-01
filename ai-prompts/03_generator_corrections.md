> **AI tool:** Gemini (identified by the candidate). **Record status:** original prompt text.

# Original Prompt 3 — Generator Debugging and Corrections

I reviewed the generator carefully, and I found some issues we need to fix before I run it on my PC.

The most immediate problem is that the invoice_lines values are inserted in the wrong order. Our schema expects invoice_line_id, invoice_id, po_line_id, po_id, invoiced_qty, billed_unit_price, and system_available_at, but the generator currently passes po_id before po_line_id. Please fix this and check every other INSERT statement against the exact column order in schema.sql.

Please also address these issues:

1. The generator must be able to produce the requested number of inspections. The current code creates at most one inspection per delivery event, so it cannot generate 20,000 inspections from only 15,000 delivery events. Support multiple inspection records where appropriate, while ensuring inspected quantities are realistic and not accidentally counted multiple times during quality scoring.

2. Make reproducibility meaningful. Generate the same dataset twice with the same seed and configuration, then compare stable counts or checksums for all operational tables and compare the ground-truth and malformed-case files too.

3. Review database reset logic and foreign-key handling. Make repeated runs safe, use transactions where appropriate, and ensure foreign keys remain enabled on connections.

4. Fix date generation. Invoices must not precede their purchase orders, inspections must not precede deliveries, and valid records must obey the date rules in our schema. Please also explain which cross-table date rules need to be checked by a validator rather than SQL constraints.

5. The generator currently writes malformed examples to JSON but does not actually validate them. Add a small validator that examines each malformed payload, detects the relevant issue from its contents, and reports the detected reason. Do not simply trust the supplied error_reason label. Keep malformed records separate from valid operational tables.

6. Check the synthetic profiles. Sparse-history suppliers must genuinely have fewer usable historical records, and worsening-delivery and quality-issue suppliers must exhibit those behaviors in the generated source data. Keep the hidden profile labels separate from the scoring inputs.

7. Check the cost data and contract model. Explain whether the current schema can represent effective-dated contract prices. If it cannot, propose the smallest necessary schema change before implementing it.

8. Add a validation summary covering every requested target count, all foreign-key violations, key date and quantity checks, and malformed-case detection results. If a requested count cannot be achieved with a given configuration, raise a clear error instead of silently returning fewer records.

9. Add tests that cover invoice-line insertion, exact requested counts, reproducibility across every operational table, valid foreign keys, valid dates, malformed-case detection, and genuine differences between the synthetic supplier profiles. Run the tests if you can, but don't claim success without actually executing them.

Please show the complete revised files and exact Windows PowerShell commands. Keep the implementation beginner-friendly and compatible with the schema already in my project. Do not implement the scoring engine yet.