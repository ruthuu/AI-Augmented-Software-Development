# Feature Specification: SpendWise Personal Expense Tracker

**Feature Branch**: `001-spendwise-expense-tracker`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Build SpendWise, a personal expense tracking application. Users record and manage personal expenses (amount, description, category, date, payment method), filter them by month and category, set a monthly budget, see the remaining budget with an overspend warning, and view a dashboard of monthly spending grouped by category. Single-user, INR currency. Authentication, bank integrations, payment processing, and cloud deployment are out of scope. Deadline: 2026-11-15."

## Clarifications

### Session 2026-11-12

Resolved by documented defaults (see Assumptions).

- Q: Which payment methods are supported? -> A: Cash, Credit Card, Debit Card, UPI, Net Banking, Other.
- Q: Is the budget global or per month? -> A: One budget amount per calendar month.
- Q: Are future-dated expenses allowed? -> A: No; the date must not be later than today.
- Q: Should a monthly budget be saved permanently like expenses so it survives an application restart? → A: Yes; budgets are persisted, covered by a requirement, a scenario, and SC-008.

### Session 2026-11-13

- Q: What happens when a budget has more than two decimal places or exceeds the maximum? → A: Both are rejected with a specific message and never rounded; `0.01` and `99999999.99` are the accepted boundary values (same rule as expenses).
- Q: Which date examples are valid given that future dates are prohibited? → A: All examples must be on or before today; the leap-day example is `2024-02-29` and month-boundary examples use `2025-12-31` and `2026-01-01`.
- Q: How is SC-010 verified without a usability study? → A: By a scripted walkthrough (automated UI test or a reviewer following only the README) with objective pass criteria.
- Q: Which payment-method inputs are tested? → A: Each of the six valid methods is accepted; unsupported, differently-cased, and missing values are rejected with field messages.
- Q: Who decides what "today" is, and which date do automated tests use? → A: The backend determines the current date at runtime and exposes it to the interface; future-date validation uses that same date; automated tests use the fixed date `2026-11-12` (FR-041).
- Q: How is SC-005 (2 seconds with 1,000 expenses) verified? → A: A manual check on a database seeded with 1,000 expenses plus an automated in-process check that listing expenses and computing a monthly summary each finish in under 500 ms; what each measures is defined in SC-005.
- Q: What counts as an interaction in the 3-interaction rule? → A: One click, tap, or form submission is one interaction; typing text into a field is not (FR-043).
- Q: How are control characters in descriptions handled? → A: Tab, line-feed, and carriage-return characters become single spaces, other control characters are removed, then the text is trimmed; ordinary special characters are kept and shown as plain text (FR-042).
- Q: Is a zero amount ever valid? → A: No; expense amounts must be strictly greater than zero (smallest valid amount `0.01`), enforced both by validation and by the data store (FR-007, FR-015).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record and manage expenses (Priority: P1)

A user records each purchase as an expense with an amount, description, category, date, and payment
method. They can see all recorded expenses in one list, correct a mistake by editing an expense, and
remove an expense they entered by error.

**Why this priority**: Without recorded expenses there is nothing to filter, total, or budget.
This story alone is a usable expense log.

**Independent Test**: Add, view, edit, and delete expenses with no budget set and no dashboard.
Delivers a working record of spending.

**Acceptance Scenarios**:

1. **Given** no expenses exist, **When** the user adds an expense with amount `250.50`, description
   `Lunch`, category `Food`, date `2026-11-10`, payment method `UPI`, **Then** the expense appears in
   the list showing `₹250.50`, `Lunch`, `Food`, `10 Nov 2026`, `UPI`.
2. **Given** an expense exists, **When** the user edits its amount to `300.00` and saves, **Then**
   the list shows `₹300.00` for that expense and no additional expense is created.
3. **Given** an expense exists, **When** the user deletes it and confirms, **Then** it no longer
   appears in the list.
4. **Given** an expense exists, **When** the user starts to delete it and cancels, **Then** the
   expense remains unchanged.
5. **Given** the user submits the add form with the amount `0`, **Then** the expense is not saved
   and the message "Amount must be greater than zero" is shown next to the amount field.
6. **Given** the user submits the add form with the amount `-5`, **Then** the expense is not saved
   and the message "Amount must be greater than zero" is shown.
7. **Given** the user submits the add form with an empty description, **Then** the expense is not
   saved and the message "Description is required" is shown next to the description field.
8. **Given** the user submits the add form with all fields empty, **Then** nothing is saved and a
   message is shown next to each of the five fields.
9. **Given** the user double-clicks the Save button once for one new expense, **Then** exactly one
   expense is created.
10. **Given** the user enters the amount `12.345`, **Then** the expense is not saved and the message
    "Amount can have at most 2 decimal places" is shown; the value is not silently rounded.
11. **Given** the user enters the date `2026-02-30`, **Then** the expense is not saved and the
    message "Enter a valid date" is shown.
12. **Given** the user enters a date later than today, **Then** the expense is not saved and the
    message "Date cannot be in the future" is shown.
13. **Given** expenses were saved, **When** the application is closed and reopened, **Then** all
    saved expenses are still present.
14. **Given** the user enters today's date, **Then** the expense is saved.
15. **Given** the user enters the date `2024-02-29` (a past leap day), **Then** the expense is saved.
16. **Given** the user enters the date `2025-02-29` (2025 is not a leap year), **Then** the expense
    is not saved and the message "Enter a valid date" is shown.
17. **Given** the user enters the date `2000-01-01`, **Then** the expense is saved; **Given** the
    date `1999-12-31`, **Then** it is not saved and the message "Date cannot be before 01 Jan 2000"
    is shown.
18. **Given** the user opens the payment method choice on the add form, **Then** exactly these
    options are offered: Cash, Credit Card, Debit Card, UPI, Net Banking, Other, and an expense
    can be saved with each of them.
19. **Given** a request with the payment method `Bitcoin`, **Then** it is rejected, no expense is
    saved, and the message "Select a valid payment method" is shown.
20. **Given** a request with the payment method `upi` (not matching `UPI` exactly) or an empty
    payment method, **Then** it is rejected, no expense is saved, and the message "Select a valid
    payment method" (unsupported) or "Payment method is required" (missing) is shown.
21. **Given** an existing expense, **When** the user edits its payment method to an unsupported
    value, **Then** the edit is rejected and the expense keeps its previous payment method.
22. **Given** the user enters the amount `0.01`, **Then** the expense is saved; **Given** the amount
    `9999999.99`, **Then** it is saved; **Given** the amount `10000000.00`, **Then** it is not
    saved and the message "Amount cannot exceed 9,999,999.99" is shown.
23. **Given** the user enters the description `<b>Tom & "Jerry's"</b>`, **Then** the expense is
    saved and the list shows exactly `<b>Tom & "Jerry's"</b>` as plain text, with no bold
    formatting and no characters altered.
24. **Given** the user enters a description containing a tab or line break between words (e.g.
    `Tea`, line break, `Snacks`), **Then** it is saved and shown as `Tea Snacks` (each tab, line
    feed, or carriage return becomes one space).
25. **Given** the user enters a description containing other control characters (e.g. the NUL
    character inside `Ab`), **Then** the control characters are removed and the text is saved as
    `Ab`.
26. **Given** the user enters a description made only of spaces and control characters, **Then**
    the expense is not saved and the message "Description is required" is shown.
27. **Given** an attempt to store an expense with an amount of `0.00` or a negative amount by any
    route that bypasses request validation, **Then** the data store itself refuses it and no row is
    created.

---

### User Story 2 - Categorize and filter expenses (Priority: P2)

A user assigns each expense to one of eight predefined categories and narrows the expense list to a
chosen category, a chosen month, or both.

**Why this priority**: Filtering turns a raw log into something the user can search; it also
supplies the data grouping the dashboard relies on.

**Independent Test**: With a mixed set of expenses across categories and months, apply each filter
and verify only matching expenses are shown.

**Acceptance Scenarios**:

1. **Given** the user opens the category choice on the add form, **Then** exactly these options are
   offered: Food, Transport, Shopping, Bills, Entertainment, Healthcare, Education, Other.
2. **Given** expenses in Food and Transport, **When** the user filters by `Food`, **Then** only Food
   expenses are listed.
3. **Given** expenses in November 2026 and October 2026, **When** the user filters by `November
   2026`, **Then** only November 2026 expenses are listed.
4. **Given** the filters month = `November 2026` and category = `Food`, **Then** only expenses
   matching both are listed.
5. **Given** a filter combination matches no expenses, **Then** the list shows the message "No
   expenses match these filters" and a way to clear the filters.
6. **Given** a filter is applied, **When** the user selects "All" for category and clears the
   month, **Then** all expenses are listed again.
7. **Given** an expense dated `2026-10-31` and one dated `2026-11-01`, **When** the user filters by
   `October 2026`, **Then** only the `2026-10-31` expense is listed.
8. **Given** a request carrying a category not in the supported list, **Then** it is rejected and
   no expense is saved.

---

### User Story 3 - Monthly budget and overspend warning (Priority: P3)

A user sets a budget for a month, then sees how much was spent that month, how much budget remains,
and a clear warning when spending exceeds the budget.

**Why this priority**: Budget monitoring is the core value over a plain log, but depends on
recorded expenses (P1).

**Independent Test**: Set a budget for a month, add expenses totalling below, equal to, and above
that budget, and check spent, remaining, and the warning each time.

**Acceptance Scenarios**:

1. **Given** the user selects `November 2026` and sets the budget to `10000.00`, **Then** the budget
   is saved and shown for November 2026.
2. **Given** a November 2026 budget of `10000.00` and November expenses totalling `2500.75`,
   **Then** the page shows Spent `₹2,500.75` and Remaining `₹7,499.25`, and no warning.
3. **Given** a November 2026 budget of `10000.00` and November expenses totalling exactly
   `10000.00`, **Then** Remaining is `₹0.00` and no warning is shown.
4. **Given** a November 2026 budget of `10000.00` and November expenses totalling `10000.01`,
   **Then** a prominent warning is shown stating the budget is exceeded by `₹0.01`, and the
   overspend is shown as an amount over budget (not as a negative remaining value).
5. **Given** a November budget of `10000.00` and an October expense of `5000.00`, **Then** the
   October expense is not counted in the November spent amount.
6. **Given** a month with no budget set, **Then** Spent is shown, Remaining is replaced by the
   message "No budget set for this month", and no warning is shown.
7. **Given** a November budget exists, **When** the user sets a new budget of `12000.00` for
   November, **Then** the new value replaces the old one.
8. **Given** the user enters a budget of `0`, `-100`, an empty value, or `abc`, **Then** the budget
   is not saved and a message "Budget must be a number greater than zero" is shown.
9. **Given** a November budget of `5000.00` and spending of `6000.00`, **When** the user deletes a
   `2000.00` expense, **Then** Spent becomes `₹4,000.00`, Remaining becomes `₹1,000.00`, and the
   warning disappears.
10. **Given** a November 2026 budget of `10000.00` was saved, **When** the application is closed and
    reopened, **Then** the November 2026 budget is still `10000.00` and Remaining and the warning
    are calculated from it.
11. **Given** the user enters a budget of `0.01`, **Then** it is saved; **Given** a budget of
    `99999999.99`, **Then** it is saved.
12. **Given** the user enters a budget of `100000000.00`, **Then** it is not saved and the message
    "Budget cannot exceed 99,999,999.99" is shown.
13. **Given** the user enters a budget of `12000.999` (three decimal places), **Then** it is not
    saved, it is not rounded to `12001.00`, and the message "Budget can have at most 2 decimal
    places" is shown.
14. **Given** the user enters a budget of `12000` or `12000.5`, **Then** it is saved as `12000.00`
    or `12000.50` respectively.
15. **Given** a November 2026 budget of `10000.00` exists, **When** the user submits an invalid
    budget (`0`, `-100`, empty, `abc`, `12000.999`, or `100000000.00`), **Then** the November 2026
    budget remains `10000.00`.

---

### User Story 4 - Monthly dashboard (Priority: P4)

A user views a dashboard for a selected month (defaulting to the current month) showing total
spending, the number of expenses, and spending grouped by category.

**Why this priority**: Summarises the data for understanding spending habits; builds on P1 to P3.

**Independent Test**: With expenses across several months and categories, select a month and verify
the total, count, and category breakdown against a hand calculation.

**Acceptance Scenarios**:

1. **Given** today (the date provided by the backend; `2026-11-12` in automated tests) is in
   November 2026, **When** the user opens the dashboard, **Then** the selected month is
   `November 2026`.
2. **Given** November 2026 expenses: Food `100.10`, Food `200.20`, Transport `50.00`, **Then** the
   dashboard shows Total `₹350.30`, Expenses this month `3`, and category rows Food `₹300.30`,
   Transport `₹50.00`.
3. **Given** expenses in October and November 2026, **When** the user selects `October 2026`,
   **Then** only October figures are shown.
4. **Given** the selected month has no expenses, **Then** Total is `₹0.00`, count is `0`, and the
   message "No expenses recorded this month" is shown instead of the category rows.
5. **Given** a category has no spending in the selected month, **Then** it is not listed in the
   breakdown.
6. **Given** the dashboard is showing November 2026, **When** the user adds, edits (including
   changing the amount, category, or date), or deletes an expense, **Then** the total, count, and
   category breakdown reflect the change without a manual refresh.
7. **Given** an expense dated November is edited to an October date, **Then** the November totals
   decrease and the October totals increase by that amount.
8. **Given** `0.10` + `0.20` of expenses in one month, **Then** the total is exactly `₹0.30`.
9. **Given** the dashboard, **Then** the all-time count of recorded expenses is also displayed.

---

### Edge Cases

- **Amount boundaries**: amounts must be strictly greater than zero; `0.01` is the smallest
  accepted amount and is accepted; `0.00`, `0`, and negatives are rejected; `9999999.99`
  is accepted; `10000000.00` is rejected with "Amount cannot exceed 9,999,999.99".
- **Amount format**: `12`, `12.5`, and `12.50` are accepted (stored as `12.00`, `12.50`, `12.50`);
  `12.`, `.5`, `1,000`, `1e3`, `abc`, and whitespace-only values are rejected with a clear message.
- **Description**: control characters are cleaned first (FR-042), then leading and trailing spaces
  are removed; a description that is empty or whitespace-only after cleaning is treated as empty;
  more than 200 characters after cleaning is rejected with "Description cannot exceed 200
  characters" (exactly 200 is accepted). Ordinary special characters such as `<`, `>`, `&`, quotes,
  backslashes, accented letters, non-Latin scripts, and emoji are kept, stored, and displayed as
  plain text, never interpreted as formatting or markup.
- **Current date**: the server's date is authoritative. If the interface still holds an outdated
  "today" (for example after midnight), a date the server considers to be in the future is rejected
  with the normal message and nothing is saved.
- **Dates**: `2024-02-29` (a past leap day) is accepted; `2025-02-29`, `2026-02-29`, `2026-13-01`,
  and `abc` are rejected; `2000-01-01` is accepted and `1999-12-31` is rejected; today's date is
  accepted and tomorrow's date is rejected.
- **Month boundaries**: expenses on the first and last day of a month belong to that month; an
  expense on `2025-12-31` counts toward December 2025 and not January 2026, and an expense on
  `2026-01-01` counts toward January 2026 and not December 2025.
- **Budget boundaries**: `0.01` and `99999999.99` are accepted; `0.00`, negatives, `100000000.00`,
  and values with more than two decimal places (e.g. `12000.999`) are rejected and never rounded;
  a rejected budget leaves any existing budget for that month unchanged.
- **Payment method boundaries**: only the six exact names are accepted; any other value, a value
  that differs only in letter case, and an empty value are rejected.
- **Budget overage boundaries**: spending exactly equal to the budget is not an overage; one paisa
  more is.
- **Identical expenses**: two expenses with the same amount, description, category, date, and method
  are allowed when the user deliberately adds both, but never created automatically or by one
  action.
- **Concurrent edits**: editing or deleting an expense that no longer exists shows "This expense no
  longer exists" and refreshes the list.
- **Empty state**: with no expenses, the list shows a prompt to add the first expense and the
  dashboard shows zeros.
- **Failure to save**: if saving fails for any reason, the user sees an error message and the form
  keeps the entered values.
- **Large lists**: a list of 1,000 expenses remains usable and totals remain exact.

## Requirements *(mandatory)*

### Functional Requirements

**Expense management**

- **FR-001**: Users MUST be able to add an expense with an amount, description, category, date, and
  payment method; all five fields are required.
- **FR-002**: Users MUST be able to view all recorded expenses, ordered by date (newest first), and
  within the same date by most recently added first.
- **FR-003**: Users MUST be able to edit any field of an existing expense; saving MUST update the
  same record and MUST NOT create a new one.
- **FR-004**: Users MUST be able to delete an expense after an explicit confirmation step.
- **FR-005**: The system MUST persist expenses and monthly budgets so they remain available,
  unchanged, after the application is restarted.
- **FR-006**: The system MUST NOT create expenses automatically, and a single submit action MUST
  create at most one expense (repeated clicks while saving MUST NOT create duplicates).

**Validation**

- **FR-007**: The system MUST reject an amount that is empty, non-numeric, zero, or negative; a
  valid amount is strictly greater than zero (the smallest valid amount is `0.01`).
- **FR-008**: The system MUST accept amounts with at most two decimal places, MUST reject amounts
  with more, and MUST NOT round user-entered values.
- **FR-009**: The system MUST reject amounts above `9,999,999.99`.
- **FR-010**: The system MUST reject a description that is empty or contains only whitespace after
  trimming, and MUST reject descriptions longer than 200 characters.
- **FR-011**: The system MUST reject dates that are missing, not real calendar dates, earlier than
  `2000-01-01` (message "Date cannot be before 01 Jan 2000"), or later than today as defined in
  FR-041 (message "Date cannot be in the future").
- **FR-012**: The system MUST reject a category that is not one of the eight predefined categories.
- **FR-013**: The system MUST reject a payment method that is not exactly one of the six predefined
  methods (message "Select a valid payment method"), and MUST reject a missing one (message
  "Payment method is required").
- **FR-014**: Every validation failure MUST produce a message identifying the field and the problem
  in plain language, shown next to the field, and MUST leave stored data unchanged.
- **FR-015**: Validation rules MUST be enforced by the system itself independently of any checks
  performed in the user interface. The data store MUST additionally refuse any expense amount that
  is not strictly greater than zero or is above `9,999,999.99`, and any budget amount that is not
  strictly greater than zero or is above `99,999,999.99`, so that invalid amounts cannot be stored
  even if request validation is bypassed.

**Categories and payment methods**

- **FR-016**: The system MUST support exactly these categories: Food, Transport, Shopping, Bills,
  Entertainment, Healthcare, Education, Other.
- **FR-017**: The system MUST support exactly these payment methods: Cash, Credit Card, Debit Card,
  UPI, Net Banking, Other.

**Filtering**

- **FR-018**: Users MUST be able to filter the expense list by category.
- **FR-019**: Users MUST be able to filter the expense list by month.
- **FR-020**: When both filters are applied, the list MUST show only expenses that match both.
- **FR-021**: Users MUST be able to clear the filters and see all expenses.
- **FR-022**: The system MUST show a "No expenses match these filters" message when no expense
  matches.

**Monthly budget**

- **FR-023**: Users MUST be able to set a budget amount for any calendar month, and setting it again
  MUST replace the previous value for that month.
- **FR-024**: A budget MUST be greater than zero, at most `99,999,999.99`, and have at most two
  decimal places. The system MUST reject (never round) a budget that is empty, non-numeric, zero, or
  negative (message "Budget must be a number greater than zero"), has more than two decimal places
  (message "Budget can have at most 2 decimal places"), or exceeds the maximum (message "Budget
  cannot exceed 99,999,999.99"), and a rejected budget MUST leave any existing budget unchanged.
- **FR-025**: For the selected month, the system MUST display Spent (sum of that month's expenses)
  and Remaining (budget minus Spent).
- **FR-026**: When Spent is greater than the budget, the system MUST display a clear warning stating
  the amount by which the budget is exceeded; when Spent equals the budget, it MUST NOT.
- **FR-027**: When no budget is set for the selected month, the system MUST show Spent and a "No
  budget set for this month" message, and MUST NOT show a warning.

**Dashboard**

- **FR-028**: The dashboard MUST default to the current month (the month of today as defined in
  FR-041) and let the user select any other month.
- **FR-029**: The dashboard MUST show, for the selected month: total spending, the number of
  expenses, and total spending per category.
- **FR-030**: The dashboard MUST show the all-time number of recorded expenses.
- **FR-031**: The category breakdown MUST list only categories with spending in the selected month,
  ordered by amount (highest first), then by category name.
- **FR-032**: The category breakdown MUST NOT be affected by the expense list's category filter.

**Calculations and currency**

- **FR-033**: All amounts MUST be in Indian Rupees (INR), displayed with the `₹` symbol, two decimal
  places, and thousands separators (e.g. `₹10,000.00`).
- **FR-034**: Monthly totals, remaining budget, and category totals MUST be exact to the paisa,
  with no rounding drift regardless of how many expenses are summed.
- **FR-035**: An expense belongs to the calendar month of its date; the first and last day of the
  month are inclusive.
- **FR-036**: Adding, editing (amount, category, or date), or deleting an expense MUST update every
  affected total, remaining budget, warning, and count immediately, including both the old and new
  months when a date changes months.
- **FR-037**: The same stored data MUST always produce the same totals and breakdown.

**Usability**

- **FR-038**: The interface MUST work on screens from 360 px to 1440 px wide without horizontal
  scrolling.
- **FR-039**: Each of add, edit, delete, and filter MUST be reachable from the main screen in at
  most 3 user interactions, counted as defined in FR-043.
- **FR-040**: While data is loading or saving the user MUST see a progress indication, and any
  failure MUST be shown as an error message.

**Current date, text cleanup, and interaction counting**

- **FR-041**: The backend MUST determine the current date at runtime and make it available to the
  interface. "Today" everywhere in this specification means that date. The interface MUST use it
  for the dashboard's default month and for the latest selectable expense date, and the backend
  MUST use the same date for the future-date validation in FR-011. Automated tests MUST use the
  fixed reference date `2026-11-12` instead of the real clock, so that results are deterministic.
- **FR-042**: Before validation, the system MUST clean the description as follows, in this order:
  (1) replace each tab, line-feed, and carriage-return character with one space; (2) remove every
  other Unicode control character (general category "Cc", e.g. NUL and DEL); (3) trim leading and
  trailing spaces. The empty check and the 200-character limit apply to the cleaned text. All other
  characters, including `<`, `>`, `&`, quotes, accented letters, non-Latin scripts, and emoji, MUST
  be kept unchanged, and MUST be displayed as plain text and never interpreted as markup or
  formatting.
- **FR-043**: An *interaction* is one click, one tap, or one form submission (pressing a Save or
  Confirm button, or pressing Enter in a form). Typing text into a field is not an interaction.
  Choosing a value in a field of a form that is open (for example category, payment method, or
  date) is data entry and is not an interaction. Choosing a filter or month value from a list or
  picker as the operation itself counts as one interaction. Interactions are counted from the main
  screen with no form or dialog open, up to and including the one that completes the operation:
  add = open the form (1) + submit (2); edit = open the form (1) + submit (2); delete = choose
  Delete (1) + confirm (2); apply one filter = choose a value (1); set a budget = submit (1).

### Key Entities

- **Expense**: A single recorded spend. Attributes: unique identifier, amount (INR, 2 decimals,
  > 0), description (1 to 200 characters), category (one of eight), date (calendar date), payment
  method (one of six), and the time it was created and last changed.
- **Monthly Budget**: A spending limit for one calendar month. Attributes: month (year and month),
  amount (INR, 2 decimals, > 0). At most one budget exists per month.
- **Category**: A fixed, predefined label for grouping expenses (eight values).
- **Payment Method**: A fixed, predefined label for how an expense was paid (six values).
- **Monthly Summary** *(derived, not stored)*: For one month: total spent, expense count, spending
  per category, and, if a budget exists, remaining budget and over-budget status.

### Out of Scope

- User accounts, login, and multiple users.
- Bank, card, or wallet integrations; payment processing; importing statements.
- Currencies other than INR and currency conversion.
- Custom or user-defined categories and payment methods.
- Recurring expenses, receipts or attachments, notifications, and data export.
- Cloud hosting and deployment.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can add a new expense in under 30 seconds from the main screen, in at most 3
  interactions (counted as defined in FR-043; adding an expense takes 2).
- **SC-002**: 100% of the invalid inputs listed in the Acceptance Scenarios and Edge Cases are
  rejected with a field-specific message and no data change; 100% of the valid boundary inputs
  listed are accepted.
- **SC-003**: For a data set of at least 50 expenses spanning at least 3 months and all 8
  categories, the displayed monthly total, count, category totals, and remaining budget match an
  independent hand calculation to the exact paisa in 100% of checks.
- **SC-004**: After any add, edit, or delete, all affected figures are updated on screen within 1
  second, with no manual refresh.
- **SC-005**: Opening the main screen with 1,000 saved expenses displays the list and dashboard
  within 2 seconds. This is verified by two checks that measure different things:
  - **SC-005a (manual, end to end)**: Use a database seeded with exactly 1,000 expenses (a
    deterministic seed spanning at least 3 months and all 8 categories). On the developer machine
    with the browser cache disabled, load the main screen 5 times. Each run measures the elapsed
    time from the start of page navigation until both the expense list and the dashboard figures
    are visible. Pass: every one of the 5 runs is within 2 seconds; the median is also recorded.
    This includes browser rendering, the network round trip on the local machine, and the server
    work.
  - **SC-005b (automated, in process)**: A test seeds a fresh database with exactly 1,000
    expenses and, using the fixed reference date, calls the application in the same process (no
    browser, no network). After one warm-up call, it times two operations separately: listing
    all expenses, and computing the monthly summary for a month that has data. Pass: each
    operation completes in under 500 ms. This measures only the server-side work (validation of
    the query, database reads, calculations, and response building); it does not measure browser
    rendering or network time, which is why SC-005a is also required.
- **SC-006**: A budget overage warning appears in 100% of cases where Spent exceeds the budget by
  at least `0.01`, and in 0% of cases where Spent is at or below the budget.
- **SC-007**: Month and category filters return exactly the expenses matching them, with 0 missing
  and 0 extra expenses in all tested combinations, including month boundary dates.
- **SC-008**: 100% of saved expenses and saved monthly budgets are still present and unchanged
  after the application is restarted.
- **SC-009**: No expense is ever created without the user's explicit submit action; repeated
  submits of one form create exactly one expense in 100% of tests.
- **SC-010**: A scripted walkthrough "add an expense, set a budget for that expense's month, open
  the dashboard for that month" completes with 0 failed steps, using only the on-screen labels and
  the README (no verbal help), when run by an automated end-to-end UI test or by one reviewer
  following the walkthrough. Each of the three operations MUST be within the interaction limit of
  FR-039 (counted as defined in FR-043: add = 2, set budget = 1, open the dashboard for the month =
  at most 1), and the dashboard MUST show the expected Total, count, Spent, and Remaining for the
  data entered.

## Assumptions

- **Single local user**: there is no login; all data belongs to one person on one device.
- **Currency**: INR only, shown as `₹`; amounts have exactly two decimal places once saved.
- **Payment methods**: the predefined list is Cash, Credit Card, Debit Card, UPI, Net Banking,
  Other, since the request did not name them.
- **Budget scope**: the budget is set per calendar month; a budget set for one month does not carry
  over to other months.
- **Date rules**: expenses cannot be dated in the future or before 2000-01-01; "today" is the
  current local date of the machine running the backend, read at runtime and shared with the
  interface (FR-041). Time of day is not recorded for an expense.
- **Test reference date**: all automated tests use the fixed date `2026-11-12` as "today".
- **Month selection**: months are calendar months; the selected month applies to the budget panel
  and dashboard, and the expense list has its own optional month filter.
- **Limits**: maximum expense of 9,999,999.99, maximum budget of 99,999,999.99, and descriptions up
  to 200 characters are chosen defaults.
- **Delete**: deletion is permanent with no undo or recycle bin.
- **Language and format**: the interface is in English; dates are shown as `DD Mon YYYY`.
- **Deadline**: the initial release must be complete by 2026-11-15, so only the features listed
  above are in scope.
