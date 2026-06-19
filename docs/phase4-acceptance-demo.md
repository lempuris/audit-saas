# Phase 4 — Review, Completion & Reporting: walkthrough

> **Status: ⏳ To verify** on the live app once PRs #67–#69 are merged and
> deployed. Update this line to ✅ with the date once the steps below pass.

A short walkthrough to confirm an engagement can be closed end-to-end: sign off
working papers and financial-statement areas, complete the ISA checklist, write
and finalise the audit report, generate the PDF, and archive the file so it
becomes read-only — then see it all on the firm dashboard.

**Before you start:** use an engagement that has finished fieldwork — working
papers **prepared**, evidence attached, and review notes cleared (the Phase 3
demo leaves an engagement in exactly this state). Move it to **Review**. Sign in
as a **Manager** for the reviews, and as a **Partner or Admin** for the approvals,
completion, and report finalising; an **Auditor** login is handy to confirm the
locks.

## 1. Sign off working papers and areas (ISA 220)
- Open the engagement, go to **Fieldwork → Working papers**. Each prepared paper
  shows a status badge.
- As a **Manager**, **Mark reviewed** on a prepared paper — your name and the date
  stamp on it, and the paper locks from further editing. Use **Return** to send one
  back to the preparer if needed.
- As a **Partner or Admin**, **Approve** the reviewed paper. As an Auditor, confirm
  you *can't* review or approve — the buttons aren't available.
- Sign off the **financial-statement area** the same way (review then approve);
  the area shows its sign-off level.
- The sign-offs are immutable — each carries who and when.

## 2. Complete the ISA checklist (ISA 220/700)
- On the engagement page, open the **Completion checklist** panel (it appears once
  the engagement is in Review).
- Click **Load standard checklist** to seed the ISA items (subsequent events 560,
  going concern 570, management representations 580, misstatements 450, and so on).
  Clicking it again won't create duplicates.
- As a Manager or above, mark each item **Complete** (or **Not applicable** with a
  reason). The readiness banner tracks what's still open.

## 3. Write and finalise the audit report (ISA 700/705/706)
- From the engagement's **Reporting** section, open **Reports**.
- **Create an audit report** and pick the opinion type — *Unmodified* (700), or
  *Qualified / Adverse / Disclaimer* (705). The standard ISA wording loads into
  editable sections.
- Edit the title, firm letterhead, and any section heading or body, and **Save**.
- Also **create a management letter** from its template.
- As a **Partner or Admin**, **Finalise** the report. Once finalised, the fields
  are read-only to a Manager (a Partner can **Reopen**).

## 4. Generate the PDF
- On each report, click **Download PDF**.
- Confirm the audit report and the management letter download as PDFs with the
  firm letterhead and your edited sections. (A draft report is watermarked; a
  finalised one isn't.)

## 5. Try to close — the gate, then archive (ISA 230)
- With an item still open or a review note uncleared, set the engagement status to
  **Completed**. It's **blocked** with a clear message — the file can't close with
  open items.
- Resolve the checklist and clear any open notes, then set it to **Completed**
  again as a **Partner or Admin**. It succeeds.
- The engagement now shows an **"Archived & read-only"** banner: the completion
  date, who archived it, and the retention-until date (7 years).
- Confirm the file is **immutable**: try to edit a working paper, add a procedure,
  or change the report — the write is refused. (As an Auditor, the write controls
  are gone entirely.)

## 6. See it on the firm dashboard
- Open **Firm dashboard** (Admin / Partner / Manager only).
- Confirm the engagement now counts under **Completed**, and that it has dropped
  out of the **review queue** and **overdue procedures** — those list only active
  engagements.
- Pick another active engagement and confirm its prepared/reviewed papers show in
  the review queue and any past-due procedures show as overdue.

## Done
When all six steps work on the live app, the demo engagement has completed the
full lifecycle — sign-offs at every level, checklist done, final PDF generated,
file archived and immutable — so **Phase 4 is complete** and Phase 5 (Hardening,
Operations & Handover) can begin.
