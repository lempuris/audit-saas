# Phase 2 — Audit Planning & Risk Assessment: walkthrough

> **Status: ✅ Verified 13 June 2026** on the live app — all steps below worked.

A short walkthrough to confirm an engagement can be planned end-to-end: import a
trial balance, set and lock materiality, document risks and link them to the
audit programme, and generate lead schedules that reconcile.

**Before you start:** have a client and an engagement that isn't completed yet.
Sign in as a Partner or Admin for the approvals; a Manager or Auditor for data
entry. Use the sample file `docs/sample-trial-balance.csv`.

## 1. Import the trial balance
- Open the engagement, go to **Trial balance**, and upload the sample file.
- Map the columns (account code, account name, current-year balance, prior-year
  balance) and import.
- Review the financial-statement-area grouping and fix any line that landed in
  the wrong area.
- Confirm all lines imported and the prior-year figures came through. (A trial
  balance that doesn't balance is rejected with a clear message.)

## 2. Set and lock materiality
- Open **Materiality**. As an Auditor, confirm you *can't* approve it — the
  option isn't available.
- As a Manager or Partner, choose a benchmark (e.g. *Revenue*) and enter the
  percentages; the system works out the overall, performance, and trivial
  amounts for you.
- As a Partner or Admin, **Approve** it. It then locks and can't be edited until
  a Partner reopens it.

## 3. Document risks and link the programme
- On **Risks**, add an entity-level risk (e.g. *Management override of controls*)
  and an assertion-level risk tied to an area (e.g. *Revenue*). The combined
  rating is worked out for you.
- On **Audit programme**, click **Load standard ISA programme** to add the
  standard procedures. Clicking it again won't create duplicates.
- Link a procedure to the risk it addresses, and assign it with a due date.

## 4. Check the lead schedules
- Open **Lead schedules** — one per financial-statement area, built from the
  trial balance.
- Confirm each area's total matches its trial-balance lines, and that all the
  totals together net to zero.

## Done
All steps work on the live app (verified 13 June 2026), so **Phase 2 is
complete**.
