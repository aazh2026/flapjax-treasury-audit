import json,urllib.request,time,datetime,os,sys

# Final funder resolution for the 10 FLAPJAX recipients of the 2026-11-18 COT day.
#
# For each recipient: find the first block at which it held ANY BNB (native + WBNB).
# If that never happens up to the current chain head, the honest answer is
# "never funded with BNB" -- a distinct category, not an unresolved row.
# Then read the funding tx:
#   (a) native BNB  -> tx whose `to` is the recipient
#   (b) WBNB deposit-> tx to the WBNB contract; the WBNB Transfer log's
#                      topics[1] (the depositor) is the real funder

ARCH="https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3"
WBNB="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def arch(m,p,retry=10):
    body=json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode()
    last=None
    for a in range(retry):
        try:
            r=urllib.request.Request(ARCH,data=body,headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(r,timeout=60) as f:
                j=json.load(f)
            if "error" in j: raise RuntimeError(j["error"])
            return j["result"]
        except Exception as e:
            last=e; time.sleep(2.0)
    raise RuntimeError("ARCHIVE FAILED: %s"%str(last)[:150])

def pad(a): return a[2:].lower().rjust(64,'0')
def nat(a,b): return int(arch("eth_getBalance",[a,hex(b)]),16)
def wbal(a,b):
    r=arch("eth_call",[{"to":WBNB,"data":"0x70a08231"+pad(a)},hex(b)])
    return int(r,16) if r and r!="0x" else 0
def total(a,b): return nat(a,b)+wbal(a,b)

def wb_logs_to(addr,fr,to):
    tp=["0x"+pad(addr)]
    out=[];s=fr
    while s<=to:
        e=min(s+4999,to)
        out+=arch("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"address":WBNB,"topics":[T0,None,tp]}])
        s=e+1; time.sleep(0.08)
    return out

def blk_txs(b):
    return (arch("eth_getBlockByNumber",[hex(b),True]) or {}).get("transactions") or []

d=json.load(open("/tmp/flap_audit/audit_2026-11-18.json"))
recs=sorted(set(r["to"] for r in d["rows"]))
HEAD=int(arch("eth_blockNumber",[]),16)
FP="/tmp/flap_audit/funders.json"
out={}
if os.path.exists(FP):
    try: out=json.load(open(FP))
    except Exception: out={}
def save(): json.dump(out,open(FP,"w"),indent=1)
print("recipients:",len(recs),"head:",HEAD,flush=True)

for a in recs:
    e=out.get(a) or {}
    if e.get("funder"):
        print("skip resolved",a,flush=True); continue
    # first non-zero BNB anywhere in history
    lo,hi=1,HEAD
    while lo<hi:
        mid=(lo+hi)//2
        if total(a,mid)>0: hi=mid
        else: lo=mid+1
    fb=lo
    if total(a,fb)==0 and total(a,HEAD)==0:
        out[a]={"first_block":None,"never_funded_with_bnb":True,
                "funder":None,"funding_tx":None,"kind":"no BNB/WBNB balance observed at any block up to chain head",
                "balance_native_now":nat(a,HEAD)/1e18,"balance_wbnb_now":wbal(a,HEAD)/1e18,
                "search_method":"binary search over full chain history for first non-zero native+WBNB balance"}
        save(); print(f"{a} NEVER FUNDED WITH BNB (native={nat(a,HEAD)/1e18:.9f} wbnb={wbal(a,HEAD)/1e18:.9f})",flush=True)
        continue
    for cand in range(fb-1,max(fb-6,0),-1):
        if total(a,cand)>0: fb=cand
        else: break
    fr=max(fb-4,1); to=min(fb+4,HEAD)
    funder=None;kind=None;txh=None;val=None;sb=None
    try: wl=wb_logs_to(a,fr,to)
    except Exception: wl=[]
    if wl:
        w=sorted(wl,key=lambda l:int(l["blockNumber"],16))[0]
        funder="0x"+w["topics"][1][-40:]; kind="WBNB deposit"
        txh=w["transactionHash"]; sb=int(w["blockNumber"],16); val=int(w["data"],16)/1e18
    if not funder:
        for cand in range(fr,to+1):
            try: txs=blk_txs(cand)
            except Exception: continue
            for t in txs:
                if (t.get("to") or "").lower()==a.lower():
                    v=int(t.get("value") or 0,16)
                    if v>0:
                        funder=t["from"];kind="native BNB";txh=t["hash"];sb=cand;val=v/1e18
                        break
            if funder: break
    b=arch("eth_getBlockByNumber",[hex(fb),False])
    out[a]={"first_block":fb,
            "utc":datetime.datetime.utcfromtimestamp(int(b["timestamp"],16)).isoformat()+"Z",
            "funder":funder,"funding_tx":txh,"funding_block":sb,"value":val,"kind":kind,
            "never_funded_with_bnb":False,
            "search_method":"first non-zero native+WBNB balance over full chain history, then inbound funding tx"}
    save()
    print(f"{a} fb={fb} funder={funder} kind={kind} tx={txh}",flush=True)
    sys.stdout.flush()
print("DONE",flush=True)
