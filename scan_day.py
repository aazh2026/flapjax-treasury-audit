import json,urllib.request,time,datetime,sys,os

# ARCHIVE-ONLY source. Verified against ground truth: the 2026-11-18 window
# returns exactly 14 outgoing transfers and historical eth_call balance reads
# work. A source that cannot reproduce that is not usable for this audit.
ARCH="https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3"
FLAP="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df"
TREAS="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
T1="0x"+TREAS[2:].lower().rjust(64,'0')
T2="0x"+TREAS[2:].lower().rjust(64,'0')
STEP=9999

def arch(m,p,retry=6):
    body=json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode()
    last=None
    for a in range(retry):
        try:
            r=urllib.request.Request(ARCH,data=body,headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(r,timeout=50) as f:
                j=json.load(f)
            if "error" in j: raise RuntimeError(j["error"])
            return j["result"]
        except Exception as e:
            last=e; time.sleep(1.5)
    raise RuntimeError("ARCHIVE NODE FAILED: %s" % str(last)[:160])

def ts(b): return int(arch("eth_getBlockByNumber",[hex(b),False])["timestamp"],16)
def find_block(target):
    lo,hi=0,int(arch("eth_blockNumber",[]),16)
    while lo<hi:
        m=(lo+hi)//2
        if ts(m)<target: lo=m+1
        else: hi=m
    return lo

def logs(fr,to,topics):
    out=[];s=fr
    while s<=to:
        e=min(s+STEP-1,to)
        out+=arch("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"address":FLAP,"topics":topics}])
        s=e+1; time.sleep(0.08)
    return out

def bal(block):
    return int(arch("eth_call",[{"to":FLAP,"data":"0x70a08231"+TREAS[2:].lower().rjust(64,'0')},hex(block)]),16)

def audit(day):
    t0=int(datetime.datetime.fromisoformat(day+"T05:00:00+00:00").timestamp())
    b0=find_block(t0); b1=find_block(t0+86400)
    while ts(b1)>=t0+86400: b1-=1
    print(f"[{day}] blocks {b0}..{b1}",flush=True)
    out=logs(b0,b1,[T0,T1]); inn=logs(b0,b1,[T0,None,T2])
    sent=sum(int(l["data"],16) for l in out)/1e18
    bs=bal(b0-1); be=bal(b1)
    delta=(bs-be)/1e18
    ok = abs(delta-sent)<1e-6 and len(inn)==0
    print(f"[{day}] outgoing={len(out)} incoming={len(inn)} sum={sent:,.0f} delta={delta:,.0f} -> {'COMPLETE' if ok else 'INCOMPLETE'}",flush=True)
    rows=[]
    for l in out:
        b=int(l["blockNumber"],16); u=datetime.datetime.utcfromtimestamp(ts(b))
        rows.append({"block":b,"utc":u.isoformat()+"Z","cot":(u-datetime.timedelta(hours=5)).isoformat()+" COT",
                     "tx":l["transactionHash"],"to":"0x"+l["topics"][2][-40:],"amount":int(l["data"],16)/1e18})
    rows.sort(key=lambda r:r["block"])
    res={"day":day,"b0":b0,"b1":b1,"ts_b0":ts(b0),"ts_b1":ts(b1),"rows":rows,
         "incoming":len(inn),"balance_start":bs/1e18,"balance_end":be/1e18,
         "balance_delta":delta,"sum_transfers":sent,"complete":ok,
         "source":"archive node "+ARCH}
    json.dump(res,open(f"/tmp/flap_audit/audit_{day}.json","w"),indent=1)
    print(f"[{day}] wrote audit_{day}.json",flush=True)
    return res

if __name__=="__main__":
    for d in sys.argv[1:]: audit(d)
