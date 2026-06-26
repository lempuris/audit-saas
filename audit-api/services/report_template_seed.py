"""Standard ISA report templates. Produces the editable sections a new report
starts from: ISA 700/705/706 audit-report opinions (unmodified, qualified,
adverse, disclaimer) and a management letter. Bodies are the standard ISA
illustrative wording with [bracketed] placeholders the firm fills in.
"""

DEFAULT_LETTERHEAD = "[Firm Name]\n[Street Address]\n[City, Country]\n[Email] · [Phone]"

# --- Audit report: opinion + basis paragraphs vary by opinion type -----------

_OPINION_HEADINGS = {
    "unmodified": "Opinion",
    "qualified": "Qualified Opinion",
    "adverse": "Adverse Opinion",
    "disclaimer": "Disclaimer of Opinion",
}

_OPINION_BODIES = {
    "unmodified": (
        "We have audited the financial statements of [Entity] (the Company), which comprise the "
        "statement of financial position as at [date], and the statement of comprehensive income, "
        "statement of changes in equity and statement of cash flows for the year then ended, and "
        "notes to the financial statements, including a summary of significant accounting "
        "policies.\n\n"
        "In our opinion, the accompanying financial statements present fairly, in all material "
        "respects, the financial position of the Company as at [date], and its financial "
        "performance and its cash flows for the year then ended in accordance with International "
        "Financial Reporting Standards (IFRSs)."
    ),
    "qualified": (
        "We have audited the financial statements of [Entity] (the Company), which comprise the "
        "statement of financial position as at [date], and the related statements for the year "
        "then ended, and notes to the financial statements.\n\n"
        "In our opinion, except for the effects of the matter described in the Basis for Qualified "
        "Opinion section of our report, the accompanying financial statements present fairly, in "
        "all material respects, the financial position of the Company as at [date], and its "
        "financial performance and its cash flows for the year then ended in accordance with "
        "IFRSs."
    ),
    "adverse": (
        "We have audited the financial statements of [Entity] (the Company), which comprise the "
        "statement of financial position as at [date], and the related statements for the year "
        "then ended, and notes to the financial statements.\n\n"
        "In our opinion, because of the significance of the matter described in the Basis for "
        "Adverse Opinion section of our report, the accompanying financial statements do not "
        "present fairly the financial position of the Company as at [date], and its financial "
        "performance and its cash flows for the year then ended in accordance with IFRSs."
    ),
    "disclaimer": (
        "We were engaged to audit the financial statements of [Entity] (the Company), which "
        "comprise the statement of financial position as at [date], and the related statements "
        "for the year then ended, and notes to the financial statements.\n\n"
        "We do not express an opinion on the accompanying financial statements of the Company. "
        "Because of the significance of the matter described in the Basis for Disclaimer of "
        "Opinion section of our report, we have not been able to obtain sufficient appropriate "
        "audit evidence to provide a basis for an audit opinion on these financial statements."
    ),
}

_BASIS_HEADINGS = {
    "unmodified": "Basis for Opinion",
    "qualified": "Basis for Qualified Opinion",
    "adverse": "Basis for Adverse Opinion",
    "disclaimer": "Basis for Disclaimer of Opinion",
}

_BASIS_UNMODIFIED = (
    "We conducted our audit in accordance with International Standards on Auditing (ISAs). Our "
    "responsibilities under those standards are further described in the Auditor's "
    "Responsibilities for the Audit of the Financial Statements section of our report. We are "
    "independent of the Company in accordance with the International Code of Ethics for "
    "Professional Accountants (including International Independence Standards) (IESBA Code), and "
    "we have fulfilled our other ethical responsibilities in accordance with the IESBA Code. We "
    "believe that the audit evidence we have obtained is sufficient and appropriate to provide a "
    "basis for our opinion."
)

_BASIS_MODIFIED = (
    "[Describe the matter giving rise to the modification.]\n\n"
    "We conducted our audit in accordance with International Standards on Auditing (ISAs). Our "
    "responsibilities under those standards are further described in the Auditor's "
    "Responsibilities for the Audit of the Financial Statements section of our report. We are "
    "independent of the Company in accordance with the IESBA Code, and we have fulfilled our "
    "other ethical responsibilities in accordance with the IESBA Code. We believe that the audit "
    "evidence we have obtained is sufficient and appropriate to provide a basis for our {opinion} "
    "opinion."
)

_BASIS_DISCLAIMER = (
    "[Describe the matter that prevented obtaining sufficient appropriate audit evidence.]\n\n"
    "We conducted our audit in accordance with International Standards on Auditing (ISAs). We are "
    "independent of the Company in accordance with the IESBA Code, and we have fulfilled our "
    "other ethical responsibilities in accordance with the Code. We were unable to obtain "
    "sufficient appropriate audit evidence to provide a basis for an audit opinion."
)

_MANAGEMENT_RESPONSIBILITIES = (
    "Management is responsible for the preparation and fair presentation of the financial "
    "statements in accordance with IFRSs, and for such internal control as management determines "
    "is necessary to enable the preparation of financial statements that are free from material "
    "misstatement, whether due to fraud or error.\n\n"
    "In preparing the financial statements, management is responsible for assessing the Company's "
    "ability to continue as a going concern, disclosing, as applicable, matters related to going "
    "concern and using the going concern basis of accounting unless management either intends to "
    "liquidate the Company or to cease operations, or has no realistic alternative but to do "
    "so.\n\n"
    "Those charged with governance are responsible for overseeing the Company's financial "
    "reporting process."
)

_AUDITOR_RESPONSIBILITIES = (
    "Our objectives are to obtain reasonable assurance about whether the financial statements as "
    "a whole are free from material misstatement, whether due to fraud or error, and to issue an "
    "auditor's report that includes our opinion. Reasonable assurance is a high level of "
    "assurance, but is not a guarantee that an audit conducted in accordance with ISAs will "
    "always detect a material misstatement when it exists. Misstatements can arise from fraud or "
    "error and are considered material if, individually or in the aggregate, they could "
    "reasonably be expected to influence the economic decisions of users taken on the basis of "
    "these financial statements.\n\n"
    "As part of an audit in accordance with ISAs, we exercise professional judgement and maintain "
    "professional scepticism throughout the audit. We also identify and assess the risks of "
    "material misstatement, evaluate accounting policies and estimates, conclude on the "
    "appropriateness of the going concern basis of accounting, and evaluate the overall "
    "presentation of the financial statements."
)

_SIGNATURE_BLOCK = (
    "[Engagement partner name]\n[Firm name]\n[Auditor address]\n[Date of the auditor's report]"
)


def _audit_report_sections(opinion_type: str) -> list[dict[str, str]]:
    if opinion_type == "disclaimer":
        basis_body = _BASIS_DISCLAIMER
    elif opinion_type == "unmodified":
        basis_body = _BASIS_UNMODIFIED
    else:
        basis_body = _BASIS_MODIFIED.format(opinion=opinion_type)

    return [
        {"key": "addressee", "heading": "Addressee", "body": "To the Shareholders of [Entity]"},
        {
            "key": "opinion",
            "heading": _OPINION_HEADINGS[opinion_type],
            "body": _OPINION_BODIES[opinion_type],
        },
        {
            "key": "basis_for_opinion",
            "heading": _BASIS_HEADINGS[opinion_type],
            "body": basis_body,
        },
        {
            "key": "key_audit_matters",
            "heading": "Key Audit Matters",
            "body": "[Describe the key audit matters, or state that there are none to "
            "communicate.]",
        },
        {
            "key": "management_responsibilities",
            "heading": "Responsibilities of Management and Those Charged with Governance for the "
            "Financial Statements",
            "body": _MANAGEMENT_RESPONSIBILITIES,
        },
        {
            "key": "auditor_responsibilities",
            "heading": "Auditor's Responsibilities for the Audit of the Financial Statements",
            "body": _AUDITOR_RESPONSIBILITIES,
        },
        {
            "key": "other_reporting",
            "heading": "Report on Other Legal and Regulatory Requirements",
            "body": "[Report on other legal and regulatory requirements, if applicable, or remove "
            "this section.]",
        },
        {"key": "signature", "heading": "Signature", "body": _SIGNATURE_BLOCK},
    ]


def _management_letter_sections() -> list[dict[str, str]]:
    return [
        {
            "key": "introduction",
            "heading": "Introduction",
            "body": "We have recently completed our audit of the financial statements of [Entity] "
            "for the year ended [date]. In planning and performing our audit, we considered the "
            "Company's internal control to design audit procedures that are appropriate in the "
            "circumstances. The matters below are offered to assist management.",
        },
        {
            "key": "observations",
            "heading": "Observations and Implications",
            "body": "[Observation, the implication or risk it gives rise to, and the affected "
            "process.]",
        },
        {
            "key": "recommendations",
            "heading": "Recommendations",
            "body": "[Our recommendation to address the matter.]",
        },
        {
            "key": "management_response",
            "heading": "Management Response",
            "body": "[Management's response and planned action.]",
        },
        {
            "key": "conclusion",
            "heading": "Conclusion",
            "body": "We would like to express our appreciation for the cooperation extended to us. "
            "This letter is intended solely for the information and use of management and those "
            "charged with governance and is not intended to be, and should not be, used by anyone "
            "other than these parties.",
        },
    ]


def standard_sections(report_type: str, opinion_type: str | None) -> list[dict[str, str]]:
    """Editable sections for a freshly created report of the given type."""
    if report_type == "management_letter":
        return _management_letter_sections()
    return _audit_report_sections(opinion_type or "unmodified")


def opinion_headings(opinion_type: str) -> dict[str, str]:
    """The opinion-driven section headings (Opinion, Basis for Opinion) for an
    opinion type, keyed by section key — used to relabel those sections when the
    opinion changes on an existing report. The bodies are left as the firm has
    edited them.
    """
    return {
        "opinion": _OPINION_HEADINGS[opinion_type],
        "basis_for_opinion": _BASIS_HEADINGS[opinion_type],
    }


def default_title(report_type: str) -> str:
    if report_type == "management_letter":
        return "Management Letter"
    return "Independent Auditor's Report"
