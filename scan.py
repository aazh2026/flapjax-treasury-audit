import json,urllib.request,time,datetime,sys
ARCH="https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3"
PUB="https://bsc-rpc.publicnode.com"
TREAS="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f"
FLAP="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df"
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def rpc(m,p,retry=5):
    body=json.dumps({"jsonrpc":"2.0","method":m,"params":p,"id":1}).encode()
    last=None
    for a in range(retry):
        for u in (ARCH,PUB):
            try:
                r=urllib.request.Request(u,data=body,headers={"Content-Type":"application/json"})
                with urllib.request.urlopen(r,timeout=45) as f:
                    j=json.load(f)
                if "error" in j: raise RuntimeError(j["error"])
                return j["result"]
            except Exception as e:
                last=e; time.sleep(0.7)
    raise last
def ts(b): return int(rpc("eth_getBlockByNumber",[hex(b),False])["timestamp"],16)
def find_block(target):
    lo,hi=0,int(rpc("eth_blockNumber",[]),16)
    while lo<hi:
        m=(lo+hi)//2
        if ts(m)<target: lo=m+1
        else: hi=m
    return lo
day=sys.argv[1] if len(sys.argv)>1 else "2026-11-18"
import sys
t0=int(datetime.datetime.fromisoformat(day+"T05:00:00+00:00").timestamp())
t1=t0+86400
b0=find_block(t0); b1=find_block(t1)
print("day",day,"blocks",b0,"..",b1,flush=True)
print("  ts",datetime.datetime.utcfromtimestamp(ts(b0)),"->",datetime.datetime.utcfromtimestamp(ts(b1)-1),flush=True)
t1t="0x"+TREAS[2:].lower().rjust(64,'0')
out=[]; errs=0; s=b0
while s<=b1:
    e=min(s+19999,b1)
    try:
        out+=rpc("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"address":FLAP,"topics":[T0,t1t]}])
    except Exception as ex:
        errs+=1; print("  err",s,str(ex)[:80],flush=True)
    s=e+1; time.sleep(0.05)
print("transfers:",len(out),"errors:",errs,flush=True)
rows=[]
for l in out:
    b=int(l["blockNumber"],16); u=datetime.datetime.utcfromtimestamp(ts(b))
    rows.append({"block":b,"utc":u.isoformat()+"Z","cot":(u-datetime.timedelta(hours=5)).isoformat()+" COT","tx":l["transactionHash"],"to":"0x"+l["topics"][2][-40:],"amount":int(l["data"],16)/1e18})
rows.sort(key=lambda r:r["block"])
json.dump({"day":day,"b0":b0,"b1":b1,"ts_b0":ts(b0),"ts_b1":ts(b1),"rows":rows},open("/tmp/flap_audit/day_%s.json"%day,"w"),indent=1)
print("distinct recipients:",len(set(r["to"] for r in rows)),"total:",sum(r["amount"] for r in rows),flush=True)
print("DONE",flush=True)
