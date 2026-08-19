# Dispatch ledger

One row per dispatched item, APPEND AT END (dates non-decreasing — machine-checked
by log_check.py). Result column takes exactly 3 values: `done` · `blocked: <why>` ·
`failed: <which gate>`. Rows from the adoption date carry `· tok ≈ <N>k`.
Actor = the HUMAN whose session dispatched the row — `VTEAM_ACTOR` env if set,
else `git config user.name`; never invented. With `team.size > 1` the column is
machine-mandatory (log_check reds a legacy header and any empty Actor cell).

| Date | Lane | Actor | Item | Result | Link |
|---|---|---|---|---|---|
