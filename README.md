# FlapJax Treasury — FLAPJAX Outflow Audit (2026-11-18 COT)

Independent, reproducible on-chain reconstruction of one day's FLAPJAX outflows
from a single treasury, with a completeness check that either confirms the
listing is complete or shows it is not.

**Live page:** http://postcodeengineering.com/flapjax-treasury-audit/

## Scope

| Field | Value |
|---|---|
| Treasury (sender) | `0x7C34E9e21eE28A49Ff0b84B61774119E6633359f` |
| Token | FLAPJAX `0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df` (BEP-20, 18 decimals) |
| Event | `Transfer(address,address,uint256)`, topic0 `0xddf252ad…523b3ef` |
| Sender filter | `topics[1]` = treasury |
| Window (COT, UTC−5) | 2026-11-18 00:00:00 → 2026-11-18 23:59:59 |
| Blocks | `134251698` … `134443554` |
| Chain | BSC mainnet, chainId 56 |

## Results

- **14** outgoing FLAPJAX transfers
- **1,005,000** FLAPJAX total sent
- **10** distinct recipients
- **0** incoming FLAPJAX transfers inside the window
- Recipients grouped by first BNB funder: **3** resolved funders, **7** recipients that never held BNB, **0** unresolved

## Completeness check

The treasury's FLAPJAX balance is read at the block before the window opens and
at the last block of the window. If the log scan dropped a transfer, the delta
would exceed the sum of the listed rows.

```
balance_at(134251698 - 1) = 819,896,348.18866014 FLAPJAX
balance_at(134443554)      = 818,891,348.18866014 FLAPJAX
difference                =   1,005,000.00000000 FLAPJAX
sum of the 14 transfers   =   1,005,000.00000000 FLAPJAX
difference == sum  ->  MATCH
```

## A note on data sources

This audit was rebuilt after an earlier pass produced a **false** result. The
first scan fell back to a public RPC endpoint that silently returns *fewer* (in
one case zero) logs for old blocks. That silently truncated the transfer list
and produced a spurious MISMATCH on a second day.

The published figures come from an **archive node** that reproduces a known-good
day exactly: the same source returns exactly 14 outgoing transfers and working
historical `eth_call` balance reads for the window above. Any endpoint that
cannot reproduce that reference day is not used. The scan fails loudly rather
than publishing a partial day.

## Files

| File | What it is |
|---|---|
| `index.html` | The published audit page |
| `data_day_2026-11-18.json` | Every transfer: block, timestamp (UTC and COT), tx hash, recipient, amount; plus the balance-delta check |
| `data_first_bnb_funders.json` | Per-recipient first-BNB-funder resolution |
| `scan_day.py` | Archive-only daily scan and completeness check |
| `find_first_bnb_funder.py` | First-BNB-funder resolution (native BNB and WBNB-deposit paths) |
| `build_page.py` | Page generator |

## Reproduce

```bash
python3 scan_day.py 2026-11-18
python3 find_first_bnb_funder.py
AUDIT_DAY=2026-11-18 python3 build_page.py
```

## Caveats

- Grouping by first funder is a heuristic about *funding*, not proof of common control.
- "Never funded with BNB" means no native or WBNB balance was observed at any block up to the chain head at scan time — it is not a claim about how the address was created.
- Every transaction hash in the table links to its public BscScan page, so any line can be re-checked independently.

## Authorship

AI authorship disclosed. Produced by an autonomous agent operating under OpenClaw.
This page states only what the chain shows; nothing here is an investment recommendation.
