import json,urllib.request,time,datetime
ARCH="https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3"
PUB="https://bsc-rpc.publicnode.com"
TREAS="0x7C34E9e21eE28A49Ff0b84B61774119E6633359f"
FLAP="0x90c8889f428F9Ebb77BB8f15CAD3a50a9aC680df"
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
def bal(block):
    data="0x70a08231"+TREAS[2:].lower().rjust(64,'0')
    return int(rpc("eth_call",[{"to":FLAP,"data":data},hex(block)]),16)
d=json.load(open("/tmp/flap_audit/day_2026-11-18.json"))
b0,b1=d["b0"],d["b1"]
rows=d["rows"]
sent=sum(r["amount"] for r in rows)
b_start=bal(b0-1); b_end=bal(b1)
print("window", b0, "..", b1, flush=True)
print("balance at b0-1 :", b_start/1e18, flush=True)
print("balance at b1   :", b_end/1e18, flush=True)
print("delta           :", (b_start-b_end)/1e18, flush=True)
print("sum of my transfers:", sent, flush=True)
print("MATCH" if abs((b_start-b_end)/1e18 - sent) < 1e-6 else "MISMATCH", flush=True)
# also: did anything else touch the treasury in the window?
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
t1="0x"+TREAS[2:].lower().rjust(64,'0')
t2="0x"+TREAS[2:].lower().rjust(64,'0')
inb=[]; out=[]
s=b0
while s<=b1:
    e=min(s+19999,b1)
    try:
        out+=rpc("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"address":FLAP,"topics":[T0,t1]}])
        inb+=rpc("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"address":FLAP,"topics":[T0,None,t2]}])
    except Exception: pass
    s=e+1; time.sleep(0.04)
print("outgoing events:",len(out)," incoming events:",len(inb), flush=True)
print("DONE",flush=True)
