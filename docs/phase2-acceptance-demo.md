# Phase 2 Acceptance Demo — Audit Planning & Risk Assessment

End-to-end acceptance run for Phase 2 on the **deployed** app. Passing this is the
gate before Phase 3 starts (per `checklist.md`: *"do not start a phase until the
previous phase's acceptance criteria pass"*).

**Acceptance criterion (checklist.md):** *A demo engagement has an imported TB,
locked materiality, documented risks linked to programs, and lead schedules with
correct totals.*

Each step below has a **Do** (the action in the UI) and a **Validate** (what must
be true for the step to pass). Tick the box only when Validate passes.

---

## 0. Prerequisites

- [ ] App is reachable: `https://dn46rvtw2v7wc.cloudfront.net` loads the SPA and
      `/api/health` returns `200` with DB connectivity.
- [ ] **Two signed-in test users with roles assigned in Clerk** (this is the
      Phase 1 carry-over item — without it nothing below works):
  - One **Partner** or **Admin** (does the approvals/locking).
  - One **Auditor** or **Manager** (does the data entry; also used for the
    negative RBAC check in step 2).
  - Assign via the **Users** screen (Admin only) or Clerk `public_metadata`.
- [ ] A **client** and an **engagement** exist and the engagement is **not
      completed** (create via Clients → Engagements if needed). Note its URL —
      every Phase 2 screen hangs off `/engagements/<engagementId>/…`.
- [ ] Test data file: `docs/sample-trial-balance.csv` (balanced; current year sums
      to zero, prior year sums to zero).

> Sign convention: **debits positive, credits negative**; a valid TB sums to zero.
> The import rejects a TB that does not balance.

---

## 1. Trial balance import

**Screen:** Engagement detail → **Trial balance** (`/engagements/:id/trial-balance`).
Open to all staff roles (Admin/Partner/Manager/Auditor); import/regroup needs
Admin/Partner/Manager.

**Do**
1. Upload `docs/sample-trial-balance.csv`. The wizard calls `POST …/trial-balance/preview`
   and shows detected columns + a preview.
2. Map columns: **Account Code → code**, **Account Name → name**,
   **Current Year → balance**, **Prior Year → prior-year balance**. (Leave
   debit/credit unset — this file uses a single signed balance column.)
3. Confirm import (`POST …/trial-balance`).
4. Review auto-suggested FS areas; **refine grouping** for any line the keyword
   matcher left blank or mis-grouped (`PATCH …/trial-balance/fs-areas`).

**Validate**
- [ ] Import **succeeds** (no "Trial balance does not balance" error) — proves the
      ±0 balancing rule passed.
- [ ] 10 account lines imported.
- [ ] FS-area summary (`GET …/trial-balance/summary`) shows the lines grouped, with
      these expected areas after refinement:
  - PPE → `property_plant_equipment`, Inventory → `inventory`,
    Trade receivables → `trade_receivables`, Cash and bank → `cash_and_bank`,
    Trade payables → `trade_payables`, Borrowings → `borrowings`,
    Share capital… → `equity`, Revenue → `revenue`,
    Cost of sales → `cost_of_sales`, Operating expenses → `operating_expenses`.
- [ ] Prior-year column is populated (drives the comparison + lead-schedule movement).
- [ ] **Negative check:** re-importing with one line edited so the TB no longer
      sums to zero returns a 422 validation error naming the difference. (Optional
      but recommended — proves errors propagate, not swallowed.)

---

## 2. Materiality — save, then approve & lock

**Screen:** Engagement → **Materiality** (`/engagements/:id/materiality`).
Edit needs Admin/Partner/Manager; **approve/reopen needs Admin/Partner only**.

**Do (as Auditor/Manager first, for the RBAC check)**
1. As the **Auditor**, open Materiality and attempt to **Approve**. Expect it to be
   blocked (button hidden/disabled, or `POST …/materiality/approve` → 403).
2. As **Manager or Partner**, fill the assessment (`PUT …/materiality`):
   - Benchmark: **Revenue**; benchmark amount: **900000** (= revenue from the TB).
   - Overall materiality %: e.g. **5** → overall **45,000**.
   - Performance materiality %: e.g. **75** of overall → **33,750**.
   - Clearly-trivial threshold %: e.g. **5** of overall → **2,250**.
   - Save.
3. As **Partner/Admin**, **Approve** (`POST …/materiality/approve`).

**Validate**
- [ ] Auditor **cannot** approve (RBAC default-deny holds for the approval action).
- [ ] Saved assessment shows server-**computed** overall / performance / trivial
      amounts (computed from benchmark amount × percentages, not free-typed).
- [ ] After approval the record is **locked**: editing (`PUT`) returns
      *"Materiality is approved and locked; reopen it before editing"* (409), and
      the screen shows it read-only with approver + timestamp.
- [ ] Re-approving an already-approved assessment is rejected (409).
- [ ] (Optional) Partner/Admin **Reopen** (`POST …/materiality/reopen`) returns it
      to draft and is recorded in the audit trail.

---

## 3. Risks — document, then load the ISA program and link

**Screens:** **Risks** (`/engagements/:id/risks`) and **Audit program**
(`/engagements/:id/program`). Both editable by Admin/Partner/Manager (create/patch);
all roles can read.

**Do**
1. On **Risks**, create at least:
   - One **entity-level** risk (no FS area, no assertions) — e.g. "Management
     override of controls", inherent **High**, control **Medium**, mark
     **significant**.
   - One **assertion-level** risk tied to an FS area — e.g. Revenue,
     assertions **Occurrence/Accuracy**, inherent **High**, control **High**.
   (`POST …/risks`)
2. On **Audit program**, click **"Load standard ISA program"** — this seeds the
   firm template library (idempotent) and bulk-adds procedures to the engagement
   in one action (`POST …/procedures/from-templates`). No manual seed step needed.
3. Link procedures to risks: on a risk-response procedure (e.g. a revenue
   procedure), set its linked risks (`PUT …/procedures/{id}/risks`) to the
   assertion-level revenue risk.
4. Set a procedure's status and assignee/due date (`PATCH …/procedures/{id}` and
   `…/status`).

**Validate**
- [ ] Entity-level risk saved with **no** FS area/assertions; assertion-level risk
      saved **with** FS area + assertions (the model enforces this split).
- [ ] **Combined rating is derived, not entered**, per the two-factor matrix:
  - inherent High × control Medium → combined **High** (the entity risk above).
  - inherent High × control High → combined **High** (the revenue risk).
  - (Spot-check one Low×Low → **Low** if you add a third risk.)
- [ ] "Load standard ISA program" adds the procedure set; clicking it **again does
      not duplicate** (idempotent seed).
- [ ] At least one procedure shows its **linked risk(s)**, and at least one risk
      shows a planned response/linked procedure — i.e. risks↔procedures are
      connected end-to-end.
- [ ] Procedure status/assignee/due-date update persists and the assigned
      procedure appears under **My procedures** for that assignee.

---

## 4. Lead schedules — totals reconcile to the TB

**Screen:** **Lead schedules** (`/engagements/:id/lead-schedules`).
`GET …/lead-schedules` (list) and `…/lead-schedules/{fs_area}` (detail).

**Do**
1. Open Lead schedules — one schedule auto-generated per FS area from the imported TB.
2. Open the **Revenue** and **Cash and bank** detail schedules.

**Validate** (against the sample TB)
- [ ] Each FS-area schedule's **balance = sum of that area's TB lines**, e.g.:
  - Revenue → **-900,000** (PY -800,000, movement -100,000)
  - Cost of sales → **540,000** (PY 480,000)
  - Cash and bank → **100,000** (PY 90,000)
  - Trade receivables → **150,000**; Inventory → **200,000**; PPE → **500,000**
  - Trade payables → **-120,000**; Borrowings → **-300,000**; Equity → **-430,000**
- [ ] **Sum of all lead-schedule balances = 0** (mirrors the balanced TB) — this is
      the headline "correct totals" reconciliation check.
- [ ] **Movement = current − prior** on each schedule; matches by-hand arithmetic.
- [ ] Before any TB is imported on a fresh engagement, the screen reports
      *"No trial balance imported for this engagement"* (404) rather than an empty
      success — confirms empty ≠ error.

---

## 5. Cross-cutting checks (audit trail + RBAC)

- [ ] Every write above (TB import, FS-area regroup, materiality save/approve/reopen,
      risk create/update, procedure add/link/status) appears in the **Audit trail**
      screen (Admin/Partner) with who / what / when / before-after.
- [ ] The Auditor RBAC block in step 2 held (approval denied).

---

## Sign-off

- [ ] All boxes above ticked → **Phase 2 acceptance PASSED**; update
      `checklist.md` (Phase 2 status note) and proceed to Phase 3.
- [ ] If any box fails → log a defect, fix on a feature branch + draft PR (CI green
      to merge), re-run the affected step. **Do not start Phase 3 until this passes.**

| Field | Value |
|---|---|
| Engagement used | |
| Run by (Partner/Admin) | |
| Run by (Auditor/Manager) | |
| Date | |
| Result | PASS / FAIL |
| Notes / defects | |
