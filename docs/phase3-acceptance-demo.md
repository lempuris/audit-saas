# Phase 3 — Fieldwork & Documentation: acceptance demo

This script verifies the Phase 3 acceptance criterion end-to-end on the deployed
app:

> A working paper can be prepared with evidence attached, cross-referenced to the
> TB, tick-marked, sampled, and has a raised-and-cleared review note.

It assumes a demo engagement already in **fieldwork** with a trial balance
imported (see `docs/phase2-acceptance-demo.md` and `docs/sample-trial-balance.csv`).

## Prerequisites

- The Phase 3 PR stack (#38–#49) is merged to `master` and deployed.
- **Documents `terraform apply` has run** (PR #40): the task has `DOCUMENTS_BUCKET`
  + `AWS_DEFAULT_REGION`, the task role has `s3:GetObjectVersion`, and the
  documents bucket has a CORS rule allowing `PUT`/`GET`/`HEAD` from the app origin.
  Without this, document upload/download fails in the browser.
- Sign in as a **Manager/Partner** for the reviewer steps; an **Auditor** account
  on the engagement team is handy for the preparer/respond steps.

## Steps

### 1. Working paper (PR #38/#39)
1. Open the engagement → **Fieldwork → Working papers**.
2. **New working paper**: FS area *Cash and bank*, index ref `C-1`, title
   "Bank reconciliation", objective text. Create.
3. **Edit** the paper, fill in Result and Conclusion, Save.
4. Open **History** — confirm ≥ 2 version snapshots (create + each edit).
5. Set status to **prepared** and confirm the preparer/timestamp shows.

### 2. Evidence document (PR #40/#41)
1. **Fieldwork → Documents**. Choose a file, attach it to working paper `C-1`,
   **Upload** (presign → S3 PUT → confirm). It appears as `available` with a size.
2. Click **Download** — the file opens via a presigned URL.
3. In **Audit trail** (Admin/Partner), confirm a `document` `read` row for the
   download and a `create` row for the upload.

### 3. Cross-reference to the TB (PR #42/#43)
1. Back on **Working papers**, open **Links** on `C-1`.
2. Add a link with target type **TB line** → pick the Cash account line. Add
   another to the uploaded **document**.
3. Click a chip and confirm it navigates to the trial-balance / documents screen.

### 4. Tick mark (PR #44/#45)
1. **Planning → Trial balance**. If the legend is empty, **Load standard tick
   marks** (Manager+).
2. On the Cash line, use the **+** dropdown to apply `✓ Agreed to supporting
   documentation`. The symbol chip shows; the legend lists it.
3. Click the chip to remove it, then re-apply (optional).

### 5. Sample (PR #46/#47)
1. **Fieldwork → Sampling**. Method **Monetary-unit (MUS)**, population value
   e.g. `1000000`, tolerable misstatement = performance materiality, 95%.
2. **Compute sample** — a size and reliability factor show. **Save sample**.
3. Repeat with **Random** and **Systematic** (supply a population item count).
4. Expand **Selection** on a saved sample and confirm the seed + selected
   items/monetary points are stored.

### 6. Review note (PR #48/#49)
1. As a reviewer, on `C-1` open **Notes**, **Raise** a note assigned to the
   auditor ("Explain the reconciling item").
2. The auditor sees it under **Dashboard → My open review notes**; they open the
   working paper and **Respond**.
3. A reviewer (or the note's author) **Clears** it. Confirm it leaves the open-notes
   dashboard and shows `cleared`.

## Result

When all six steps pass on the deployed app, tick the Phase 3 acceptance box in
`checklist.md` and note the verification date. Phase 4 (Review, Completion &
Reporting) may then begin.
