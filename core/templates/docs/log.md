# Dispatch ledger

One row per dispatched item, APPEND AT END (dates non-decreasing — machine-checked
by log_check.py). Result column takes exactly 3 values: `done` · `blocked: <why>` ·
`failed: <which gate>`. Rows from the adoption date carry `· tok ≈ <N>k`.

| Date | Lane | Item | Result | Link |
|---|---|---|---|---|
