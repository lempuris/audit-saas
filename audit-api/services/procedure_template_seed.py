"""Built-in ISA-referenced procedure library, seeded into procedure_templates
via POST /api/procedure-templates/seed. A starting point the firm tailors per
engagement — not an exhaustive ISA methodology."""

SEED_TEMPLATES: list[dict] = [
    # Property, plant & equipment
    {
        "fs_area": "property_plant_equipment",
        "title": "PPE additions vouching",
        "description": "Select a sample of additions and vouch to supporting invoices, "
        "verifying capitalisation criteria, ownership and correct cost.",
        "isa_reference": "ISA 500",
        "assertions": ["existence", "accuracy", "rights_and_obligations"],
        "sort_order": 10,
    },
    {
        "fs_area": "property_plant_equipment",
        "title": "Depreciation recalculation",
        "description": "Recalculate depreciation for a sample of assets and assess the "
        "reasonableness of useful lives and residual values.",
        "isa_reference": "ISA 540",
        "assertions": ["accuracy", "valuation"],
        "sort_order": 20,
    },
    {
        "fs_area": "property_plant_equipment",
        "title": "Physical inspection of assets",
        "description": "Physically inspect a sample of recorded assets and trace assets "
        "observed on site back to the register.",
        "isa_reference": "ISA 501",
        "assertions": ["existence", "completeness"],
        "sort_order": 30,
    },
    # Intangibles
    {
        "fs_area": "intangible_assets",
        "title": "Capitalisation criteria review",
        "description": "Review capitalised intangibles against recognition criteria and "
        "test amortisation; consider impairment indicators.",
        "isa_reference": "ISA 540",
        "assertions": ["valuation", "accuracy"],
        "sort_order": 10,
    },
    # Investments
    {
        "fs_area": "investments",
        "title": "Investment confirmation and valuation",
        "description": "Confirm investments with custodians/registrars and agree "
        "valuations to market or other supportable evidence.",
        "isa_reference": "ISA 505",
        "assertions": ["existence", "valuation", "rights_and_obligations"],
        "sort_order": 10,
    },
    # Inventory
    {
        "fs_area": "inventory",
        "title": "Inventory count attendance",
        "description": "Attend the physical inventory count, perform test counts both "
        "ways, and follow up count-to-record differences.",
        "isa_reference": "ISA 501",
        "assertions": ["existence", "completeness"],
        "sort_order": 10,
    },
    {
        "fs_area": "inventory",
        "title": "Inventory valuation testing",
        "description": "Test cost of a sample of inventory lines to purchase records and "
        "assess net realisable value for slow-moving or obsolete items.",
        "isa_reference": "ISA 500",
        "assertions": ["valuation", "accuracy"],
        "sort_order": 20,
    },
    # Trade receivables
    {
        "fs_area": "trade_receivables",
        "title": "Receivables circularisation",
        "description": "Select a sample of balances and request external confirmations; "
        "perform alternative procedures for non-replies.",
        "isa_reference": "ISA 505",
        "assertions": ["existence", "rights_and_obligations", "accuracy"],
        "sort_order": 10,
    },
    {
        "fs_area": "trade_receivables",
        "title": "Expected credit loss assessment",
        "description": "Review the ageing, test subsequent receipts and assess the "
        "adequacy of the loss allowance.",
        "isa_reference": "ISA 540",
        "assertions": ["valuation"],
        "sort_order": 20,
    },
    # Cash and bank
    {
        "fs_area": "cash_and_bank",
        "title": "Bank confirmations",
        "description": "Obtain standard bank confirmations for all accounts, including "
        "facilities, security and signatories.",
        "isa_reference": "ISA 505",
        "assertions": ["existence", "completeness", "rights_and_obligations"],
        "sort_order": 10,
    },
    {
        "fs_area": "cash_and_bank",
        "title": "Bank reconciliation testing",
        "description": "Test year-end bank reconciliations, tracing reconciling items to "
        "subsequent clearance.",
        "isa_reference": "ISA 500",
        "assertions": ["existence", "accuracy", "cutoff"],
        "sort_order": 20,
    },
    # Other assets
    {
        "fs_area": "other_assets",
        "title": "Other assets substantiation",
        "description": "Obtain a breakdown of other assets, vouch material items to "
        "support and assess recoverability.",
        "isa_reference": "ISA 500",
        "assertions": ["existence", "valuation"],
        "sort_order": 10,
    },
    # Trade payables
    {
        "fs_area": "trade_payables",
        "title": "Unrecorded liabilities search",
        "description": "Review post-year-end payments and unprocessed invoices for "
        "liabilities that should have been recorded at year end.",
        "isa_reference": "ISA 500",
        "assertions": ["completeness", "cutoff"],
        "sort_order": 10,
    },
    {
        "fs_area": "trade_payables",
        "title": "Supplier statement reconciliation",
        "description": "Reconcile a sample of supplier statements to the ledger and "
        "investigate differences.",
        "isa_reference": "ISA 500",
        "assertions": ["completeness", "accuracy"],
        "sort_order": 20,
    },
    # Borrowings
    {
        "fs_area": "borrowings",
        "title": "Loan confirmations and covenant review",
        "description": "Confirm borrowings with lenders, recalculate interest, and review "
        "covenant compliance and disclosure of terms.",
        "isa_reference": "ISA 505",
        "assertions": ["completeness", "accuracy", "presentation"],
        "sort_order": 10,
    },
    # Provisions
    {
        "fs_area": "provisions",
        "title": "Provisions recognition and measurement",
        "description": "Assess the basis for provisions against recognition criteria, "
        "test underlying calculations and consider legal correspondence.",
        "isa_reference": "ISA 540",
        "assertions": ["completeness", "valuation"],
        "sort_order": 10,
    },
    # Other liabilities
    {
        "fs_area": "other_liabilities",
        "title": "Accruals testing",
        "description": "Obtain a breakdown of accruals, test material items to support "
        "and compare with prior year for completeness.",
        "isa_reference": "ISA 500",
        "assertions": ["completeness", "accuracy"],
        "sort_order": 10,
    },
    # Equity
    {
        "fs_area": "equity",
        "title": "Equity movements verification",
        "description": "Agree share capital to statutory records and verify dividends "
        "and other equity movements to authorisation.",
        "isa_reference": "ISA 500",
        "assertions": ["completeness", "accuracy", "presentation"],
        "sort_order": 10,
    },
    # Revenue
    {
        "fs_area": "revenue",
        "title": "Revenue cutoff testing",
        "description": "Test transactions either side of year end to delivery/service "
        "evidence to confirm recognition in the correct period.",
        "isa_reference": "ISA 500",
        "assertions": ["cutoff", "occurrence"],
        "sort_order": 10,
    },
    {
        "fs_area": "revenue",
        "title": "Revenue substantive analytical procedures",
        "description": "Build an expectation of revenue from independent data, compare "
        "with recorded revenue and investigate significant variances.",
        "isa_reference": "ISA 520",
        "assertions": ["occurrence", "completeness", "accuracy"],
        "sort_order": 20,
    },
    {
        "fs_area": "revenue",
        "title": "Journal entries to revenue review",
        "description": "Identify and test unusual manual journals to revenue accounts, "
        "responding to the presumed fraud risk in revenue recognition.",
        "isa_reference": "ISA 240",
        "assertions": ["occurrence"],
        "sort_order": 30,
    },
    # Cost of sales
    {
        "fs_area": "cost_of_sales",
        "title": "Cost of sales testing",
        "description": "Test a sample of cost of sales transactions to supplier invoices "
        "and assess gross margin against expectation.",
        "isa_reference": "ISA 500",
        "assertions": ["occurrence", "accuracy", "cutoff"],
        "sort_order": 10,
    },
    # Operating expenses
    {
        "fs_area": "operating_expenses",
        "title": "Expense vouching",
        "description": "Vouch a sample of operating expenses to invoices, checking "
        "classification, authorisation and period.",
        "isa_reference": "ISA 500",
        "assertions": ["occurrence", "classification", "cutoff"],
        "sort_order": 10,
    },
    {
        "fs_area": "operating_expenses",
        "title": "Payroll analytical review",
        "description": "Reconcile payroll cost to returns and build a month-on-month "
        "expectation, investigating variances.",
        "isa_reference": "ISA 520",
        "assertions": ["occurrence", "completeness", "accuracy"],
        "sort_order": 20,
    },
    # Other income
    {
        "fs_area": "other_income",
        "title": "Other income verification",
        "description": "Obtain a breakdown of other income and vouch material items to "
        "supporting agreements or receipts.",
        "isa_reference": "ISA 500",
        "assertions": ["occurrence", "accuracy"],
        "sort_order": 10,
    },
    # Finance costs
    {
        "fs_area": "finance_costs",
        "title": "Finance cost recalculation",
        "description": "Recalculate interest expense from loan terms and agree to the "
        "ledger; check completeness against confirmed facilities.",
        "isa_reference": "ISA 500",
        "assertions": ["accuracy", "completeness"],
        "sort_order": 10,
    },
    # Tax
    {
        "fs_area": "tax",
        "title": "Tax provision review",
        "description": "Test the current and deferred tax computations, agree payments "
        "to assessments and review correspondence with the revenue authority.",
        "isa_reference": "ISA 540",
        "assertions": ["accuracy", "completeness", "valuation"],
        "sort_order": 10,
    },
]
