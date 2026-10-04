# Priority annotation rules

These are project triage labels for current unresolved issues. They are not legal findings, proof of fraud, or a universal severity measure. Apply the highest priority supported by the narrative and distinguish unresolved events from already resolved history.

| Label | Suggested human annotation standard | Examples |
|---|---|---|
| High | Explicit unresolved allegation of unauthorized financial activity, actual scam loss, unauthorized account opening or identity misuse, account takeover, compromised credentials or an unsecured lost/stolen card | Unauthorized card payment; money sent to a scammer and not recovered; accounts opened in the customer's name without authorization |
| Medium | Concrete unresolved billing, transaction or service issue without an explicit remaining security event | Fees or interest; merchant/refund dispute; erroneous security restriction; missing rewards; denied routine account access |
| Low | General enquiry or feedback, or an explicitly resolved incident with no remaining service/security problem | General information request; marketing feedback; completed refund with no remaining dispute |
| Pending review | Too little information or uncertain project scope to confidently assign H/M/L | Unspecified transaction issue or standalone virtual-currency complaint with unclear bank/payment involvement |

An allegation can justify urgent triage without documentary proof. A victim-authorized payment to a scammer can still be High. Large amounts, anger, hardship, a bank fraud flag or a customer's use of the word "fraud" alone do not establish an unresolved security event. Read negation carefully. Fully refunded fraudulent charges with only a remaining fee problem are Medium; unresolved scam reimbursement is still High.

Pending review is an annotation workflow state, not a fourth gold class in the final benchmark. **Escalate** is an application action when model confidence is below 0.80, information is insufficient, output is invalid/refused, or scope is unclear. The 200-row gold set contains only High, Medium and Low.

## Policy and implementation boundary

The table records the human annotation intent. The frozen evaluated V2 prompt is in `../prompts/v2.txt` and `../ticket_router.py`. It does not explicitly list identity theft or unauthorized account opening without a transaction as a standalone High category. Some final errors expose this policy-to-prompt gap. Do not silently change V2 and keep the old results; describe this limitation and develop a new version against new development cases.

Short annotation reasons are helpful for auditability but are not required in every final gold row. Preserve the supplied suggestion evidence and review provenance, and disclose that initial suggestions were AI-assisted and confirmed by one reviewer rather than independently labelled blind.
