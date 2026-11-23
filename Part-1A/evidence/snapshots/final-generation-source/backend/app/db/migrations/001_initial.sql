CREATE TABLE expenses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_cents   INTEGER NOT NULL CHECK (amount_cents > 0 AND amount_cents <= 999999999),
    description    TEXT    NOT NULL CHECK (length(description) BETWEEN 1 AND 200),
    category       TEXT    NOT NULL,
    payment_method TEXT    NOT NULL,
    expense_date   TEXT    NOT NULL
        CHECK (expense_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);

CREATE INDEX idx_expenses_date ON expenses (expense_date DESC, id DESC);
CREATE INDEX idx_expenses_category ON expenses (category);

CREATE TABLE monthly_budgets (
    month        TEXT PRIMARY KEY CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0 AND amount_cents <= 9999999999),
    updated_at   TEXT NOT NULL
);
