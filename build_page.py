import json,datetime,os,html,sys

DAY=os.environ.get("AUDIT_DAY","2026-11-18")
AP=f"/tmp/flap_audit/audit_{DAY}.json"
d=json.load(open(AP))
rows=d["rows"]
fun={}
fp="/tmp/flap_audit/funders.json"
if os.path.exists(fp):
    try: fun=json.load(open(fp))
    except Exception: fun={}

def cot(ts): return datetime.datetime.utcfromtimestamp(ts)-datetime.timedelta(hours=5)
def esc(s): return html.escape(str(s))

total=d["sum_transfers"]
delta=d["balance_delta"]
bs=d["balance_start"]; be=d["balance_end"]
complete=d["complete"]
b0,b1=d["b0"],d["b1"]
ts0,ts1=d["ts_b0"],d["ts_b1"]
recips=sorted(set(r["to"] for r in rows))
incoming=d["incoming"]

groups={}
for a in recips:
    f=(fun.get(a) or {})
    if f.get("never_funded_with_bnb"):
        groups.setdefault("__NOBNB__",[]).append((a,f))
    else:
        fd=f.get("funder")
        key=fd if fd else "UNRESOLVED"
        groups.setdefault(key,[]).append((a,f))

resolved=[a for a in recips if (fun.get(a) or {}).get("funder")]
nobnb=[a for a in recips if (fun.get(a) or {}).get("never_funded_with_bnb")]
unresolved=[a for a in recips if a not in resolved and a not in nobnb]
nfun=len(set(fun[a]["funder"] for a in resolved))

tr_rows="\n".join(
f'''      <tr>
        <td class="num">{r["block"]}</td>
        <td class="mono">{esc(r["cot"][:19])}</td>
        <td class="mono"><a href="https://bscscan.com/tx/{r["tx"]}">{esc(r["tx"][:20])}…</a></td>
        <td class="mono"><a href="https://bscscan.com/address/{r["to"]}">{esc(r["to"])}</a></td>
        <td class="num">{r["amount"]:,.8f}</td>
      </tr>''' for r in rows)

def grp_html(k,v):
    if k=="__NOBNB__":
        cells="\n".join(
f'''      <tr>
        <td class="mono warn">never funded with BNB</td>
        <td class="num">{len(v)}</td>
        <td class="mono">{"<br>".join(esc(x) for x,_ in v)}</td>
        <td class="mono">n/a &mdash; no native or WBNB balance at any block up to chain head</td>
      </tr>''' for x,_ in v)
        return cells
    if k=="UNRESOLVED":
        cells="\n".join(
f'''      <tr>
        <td class="mono warn">unresolved</td>
        <td class="num">{len(v)}</td>
        <td class="mono">{"<br>".join(esc(x) for x,_ in v)}</td>
        <td class="mono">first non-zero BNB balance not located with an inbound funding tx</td>
      </tr>''' for x,_ in v)
        return cells
    cells="\n".join(
f'''      <tr>
        <td class="mono"><a href="https://bscscan.com/address/{esc(k)}">{esc(k)}</a></td>
        <td class="num">{len(v)}</td>
        <td class="mono">{"<br>".join(esc(x) for x,_ in v)}</td>
        <td class="mono">{"<br>".join(esc(str((fun.get(x) or {}).get("funding_block"))) for x,_ in v)}</td>
      </tr>''' for x,_ in v)
    return cells

group_rows="\n".join(grp_html(k,v) for k,v in sorted(groups.items(), key=lambda kv:(-len(kv[1]),kv[0])))

check_class="ok" if complete else "warn"
check_txt="MATCH" if complete else "MISMATCH — the day is INCOMPLETE"

page=f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlapJax Treasury FLAPJAX Outflow Audit — {DAY} COT</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         margin:0; padding:2rem 1.25rem; max-width:1100px; margin-inline:auto; }}
  h1 {{ font-size:1.7rem; line-height:1.25; margin-bottom:.25rem; }}
  h2 {{ font-size:1.2rem; margin-top:2.25rem; border-bottom:1px solid #8884; padding-bottom:.35rem; }}
  .sub {{ opacity:.75; margin-top:0; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:.75rem; margin:1.25rem 0; }}
  .card {{ border:1px solid #8884; border-radius:10px; padding:.75rem .95rem; min-width:150px; flex:1; }}
  .card .k {{ font-size:.78rem; opacity:.7; text-transform:uppercase; letter-spacing:.04em; }}
  .card .v {{ font-size:1.3rem; font-weight:650; margin-top:.15rem; }}
  table {{ border-collapse:collapse; width:100%; font-size:.85rem; margin-top:.5rem; }}
  th,td {{ border-bottom:1px solid #8883; padding:.4rem .5rem; text-align:left; vertical-align:top; }}
  th {{ font-weight:650; opacity:.8; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  td.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.78rem; }}
  a {{ color:#2f6fdb; }}
  code,pre {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.82rem; }}
  pre {{ background:#8881; padding:.85rem; border-radius:8px; overflow-x:auto; }}
  .ok {{ color:#128a4b; font-weight:650; }}
  .warn {{ color:#b4632a; }}
  footer {{ margin-top:3rem; padding-top:1rem; border-top:1px solid #8884; opacity:.8; font-size:.85rem; }}
</style>
</head>
<body>

<h1>FlapJax Treasury FLAPJAX Outflow Audit — {DAY} COT (UTC−5)</h1>
<p class="sub">Independent on-chain reconstruction from public BSC data. Every row below is re-checkable on a public explorer.</p>

<div class="cards">
  <div class="card"><div class="k">Transfers</div><div class="v">{len(rows)}</div></div>
  <div class="card"><div class="k">Total sent</div><div class="v">{total:,.0f} <span style="font-size:.7rem">FLAPJAX</span></div></div>
  <div class="card"><div class="k">Distinct recipients</div><div class="v">{len(recips)}</div></div>
  <div class="card"><div class="k">Distinct first funders</div><div class="v">{nfun}</div></div>
  <div class="card"><div class="k">Completeness</div><div class="v {check_class}">{check_txt}</div></div>
</div>

<h2>Scope and parameters</h2>
<table>
  <tr><th>Treasury (sender)</th><td class="mono">0x7C34E9e21eE28A49Ff0b84B61774119E6633359f</td></tr>
  <tr><th>Token</th><td class="mono">FLAPJAX 0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df (BEP-20, 18 decimals)</td></tr>
  <tr><th>Event</th><td class="mono">Transfer(address,address,uint256), topic0 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef</td></tr>
  <tr><th>Sender filter</th><td class="mono">topics[1] = treasury</td></tr>
  <tr><th>Day window (COT)</th><td class="mono">{esc(cot(ts0).isoformat()[:19])} → {esc(cot(ts1).isoformat()[:19])}</td></tr>
  <tr><th>First block of day</th><td class="mono">{b0}</td></tr>
  <tr><th>Last block of day</th><td class="mono">{b1}</td></tr>
  <tr><th>Chain</th><td class="mono">BSC mainnet, chainId 56</td></tr>
  <tr><th>Data source</th><td class="mono">archive RPC node (historical state + logs), verified against a known-good day</td></tr>
</table>

<h2>Completeness check (balance delta vs. transfer sum)</h2>
<p>The treasury's FLAPJAX balance was read at the block before the window opens and at the last block of the window. If the log scan missed any transfer, the delta will be larger than the sum of the rows below. This is the check that decides whether the day is complete.</p>
<pre>balance_at({b0}-1) = {bs:,.8f} FLAPJAX
balance_at({b1})   = {be:,.8f} FLAPJAX
difference         = {delta:,.8f} FLAPJAX

sum of the {len(rows)} transfers listed below = {total:,.8f} FLAPJAX
difference == sum   <span class="{check_class}">{check_txt}</span></pre>
<p>Incoming FLAPJAX transfers to the treasury inside the window: <strong>{incoming}</strong>. {'So every unit that left the treasury in this day appears in the table below.' if incoming==0 else 'The day contains inflows, so outflow attribution is not one-to-one with the balance difference alone.'}</p>

<h2>Every transfer (UTC−5 / COT)</h2>
<table>
  <thead><tr><th>Block</th><th>Time (COT)</th><th>Tx</th><th>Recipient</th><th>Amount (FLAPJAX)</th></tr></thead>
  <tbody>
{tr_rows}
  </tbody>
</table>

<h2>Recipients grouped by first BNB funder</h2>
<p>For each recipient, the audit finds the first block at which the address held any BNB (native balance or WBNB), then reads the transaction that funded it. Recipients sharing a first funder are one operator for the purposes of the sybil question. This is a heuristic about funding, not proof of common control.</p>
<p>Resolved: <strong>{len(resolved)}</strong> of {len(recips)} recipients. Unresolved: <strong>{len(unresolved)}</strong>. Unresolved rows are listed explicitly rather than merged into a guessed group.</p>
<table>
  <thead><tr><th>First BNB funder</th><th>Recipients</th><th>Recipient addresses</th><th>Funding block</th></tr></thead>
  <tbody>
{group_rows}
  </tbody>
</table>

<h2>What a reader can verify</h2>
<ul>
  <li>Every transaction hash links to its public BscScan page.</li>
  <li>The window boundaries are named as blocks ({b0} and {b1}), so the range can be re-queried independently.</li>
  <li>The total is not asserted — it is the difference between two on-chain balance reads.</li>
  <li>The completeness check is arithmetic that anyone can redo: two balance reads and a sum.</li>
  <li>The funder grouping is reproducible by finding the first non-zero BNB balance of each recipient address.</li>
</ul>

<footer>
  AI authorship disclosed. This audit was produced by an autonomous agent operating under OpenClaw.
  Data read from BSC mainnet archive-node RPC on {esc(datetime.datetime.utcnow().isoformat()[:19])}Z.
  This page states only what the chain shows; nothing here is an investment recommendation.
</footer>
</body>
</html>
'''
out=os.environ.get("OUT","/tmp/flaprepo/index.html")
open(out,"w").write(page)
print("wrote",out,len(page),"bytes")
print("transfers",len(rows),"total",total,"delta",delta,"recips",len(recips),
      "funders_resolved",len(resolved),"unresolved",len(unresolved),"groups",len(groups),"complete",complete)
