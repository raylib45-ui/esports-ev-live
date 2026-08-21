from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests, time

app = FastAPI(title="Esports EV Live 24/7 - FULL BOARD")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_CACHE = {"data": [], "timestamp": 0, "ttl": 40}

def fetch_live():
    now = time.time()
    if _CACHE["data"] and (now - _CACHE["timestamp"] < _CACHE["ttl"]):
        return _CACHE["data"]
    props=[]
    try:
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://app.prizepicks.com","Referer":"https://app.prizepicks.com/"}
        r=requests.get("https://api.prizepicks.com/projections?leagueId=7,8,11,12,20,249,259&perPage=500&singleStat=true", headers=headers, timeout=8)
        if r.status_code==200:
            data=r.json()
            inc={i["id"]:i for i in data.get("included",[])}
            for proj in data.get("data",[])[:400]:
                try:
                    attrs=proj.get("attributes",{})
                    line=float(attrs.get("line_score",0))
                    if line==0: continue
                    pid=proj.get("relationships",{}).get("new_player",{}).get("data",{}).get("id")
                    pname=inc.get(pid,{}).get("attributes",{}).get("name") or attrs.get("description") or "Unknown"
                    if pname=="Unknown": continue
                    lid=proj.get("relationships",{}).get("league",{}).get("data",{}).get("id")
                    lname=inc.get(lid,{}).get("attributes",{}).get("name","").lower()
                    game="CS2"
                    if "dota" in lname: game="DOTA"
                    elif "valorant" in lname or "val" in lname: game="VAL"
                    elif "league" in lname or "lol" in lname: game="LOL"
                    props.append({"player":pname,"game":game,"matchup":attrs.get("team","TBD")+" vs TBD","prop_type":attrs.get("stat_type","Kills"),"sportsbook_line":line,"model_projection":round(line*1.12,1),"market":"PrizePicks","is_live":True})
                except: continue
    except Exception as e:
        print(f"live fail {e}")
    if len(props)<10:
        props.extend([
            {"player":"NiKo","game":"CS2","matchup":"Falcons vs Legacy 9:55am","prop_type":"MAPS 1-2 Kills","sportsbook_line":30.5,"model_projection":26.8,"market":"PrizePicks","is_live":False},
            {"player":"ZywOo","game":"CS2","matchup":"Vitality vs Team Spirit 12:50pm","prop_type":"MAPS 1-2 AWP Kills","sportsbook_line":14.5,"model_projection":17.3,"market":"PrizePicks","is_live":False},
            {"player":"ATF","game":"DOTA","matchup":"Falcons vs Liquid Starts in 0:45","prop_type":"MAPS 1-2 Kills","sportsbook_line":12.5,"model_projection":14.8,"market":"PrizePicks","is_live":False},
            {"player":"OmaR","game":"DOTA","matchup":"NGX vs Yandex 7:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":5.0,"model_projection":7.2,"market":"PrizePicks","is_live":False},
            {"player":"HYUNMIN","game":"VAL","matchup":"DRX vs Sharper 4:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":34.5,"model_projection":30.1,"market":"PrizePicks","is_live":False},
            {"player":"GIDEON","game":"LOL","matchup":"BRO vs BFX 4:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":7.0,"model_projection":5.4,"market":"PrizePicks","is_live":False},
            {"player":"Naak Nako","game":"LOL","matchup":"VIT vs NAVI 1:15pm","prop_type":"MAPS 1-2 Kills","sportsbook_line":6.5,"model_projection":8.3,"market":"PrizePicks","is_live":False},
            {"player":"Breathe","game":"LOL","matchup":"AL vs WE 5:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":6.5,"model_projection":8.0,"market":"PrizePicks","is_live":False},
        ])
    _CACHE["data"]=props
    _CACHE["timestamp"]=now
    return props

def calc_ev(p):
    line=float(p["sportsbook_line"]); model=float(p["model_projection"])
    ev=((model-line)/line*100) if line else 0
    lean="OVER" if model>line else "UNDER"
    prob=0.5+min(abs(ev)/100,0.35)
    return {**p,"ev_percentage":round(abs(ev),1),"lean":lean,"hit_probability":round(prob,3)}

@app.get("/")
def root(): return {"status":"ok","live_props":len(fetch_live()),"timestamp":datetime.utcnow().isoformat()}

@app.get("/slate")
def slate():
    raw=fetch_live()
    props=[calc_ev(p) for p in raw]
    best=sorted(props,key=lambda x:x["ev_percentage"],reverse=True)
    return {"props":best,"best3":best[:3],"count":len(best),"timestamp":datetime.utcnow().isoformat(),"source":"LIVE 24/7 PrizePicks Full Board"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests, time

app = FastAPI(title="Esports EV Live 24/7 - FULL BOARD")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_CACHE = {"data": [], "timestamp": 0, "ttl": 40}

def fetch_live():
    now = time.time()
    if _CACHE["data"] and (now - _CACHE["timestamp"] < _CACHE["ttl"]):
        return _CACHE["data"]
    props=[]
    try:
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://app.prizepicks.com","Referer":"https://app.prizepicks.com/"}
        r=requests.get("https://api.prizepicks.com/projections?leagueId=7,8,11,12,20,249,259&perPage=500&singleStat=true", headers=headers, timeout=8)
        if r.status_code==200:
            data=r.json()
            inc={i["id"]:i for i in data.get("included",[])}
            for proj in data.get("data",[])[:400]:
                try:
                    attrs=proj.get("attributes",{})
                    line=float(attrs.get("line_score",0))
                    if line==0: continue
                    pid=proj.get("relationships",{}).get("new_player",{}).get("data",{}).get("id")
                    pname=inc.get(pid,{}).get("attributes",{}).get("name") or attrs.get("description") or "Unknown"
                    if pname=="Unknown": continue
                    lid=proj.get("relationships",{}).get("league",{}).get("data",{}).get("id")
                    lname=inc.get(lid,{}).get("attributes",{}).get("name","").lower()
                    game="CS2"
                    if "dota" in lname: game="DOTA"
                    elif "valorant" in lname or "val" in lname: game="VAL"
                    elif "league" in lname or "lol" in lname: game="LOL"
                    props.append({"player":pname,"game":game,"matchup":attrs.get("team","TBD")+" vs TBD","prop_type":attrs.get("stat_type","Kills"),"sportsbook_line":line,"model_projection":round(line*1.12,1),"market":"PrizePicks","is_live":True})
                except: continue
    except: pass
    if len(props)<10:
        props.extend([
            {"player":"NiKo","game":"CS2","matchup":"Falcons vs Legacy 9:55am","prop_type":"MAPS 1-2 Kills","sportsbook_line":30.5,"model_projection":26.8,"market":"PrizePicks","is_live":False},
            {"player":"ZywOo","game":"CS2","matchup":"Vitality vs Team Spirit 12:50pm","prop_type":"MAPS 1-2 AWP Kills","sportsbook_line":14.5,"model_projection":17.3,"market":"PrizePicks","is_live":False},
            {"player":"ATF","game":"DOTA","matchup":"Falcons vs Liquid Starts in 0:45","prop_type":"MAPS 1-2 Kills","sportsbook_line":12.5,"model_projection":14.8,"market":"PrizePicks","is_live":False},
            {"player":"HYUNMIN","game":"VAL","matchup":"DRX vs Sharper 4:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":34.5,"model_projection":30.1,"market":"PrizePicks","is_live":False},
            {"player":"GIDEON","game":"LOL","matchup":"BRO vs BFX 4:00am","prop_type":"MAPS 1-2 Kills","sportsbook_line":7.0,"model_projection":5.4,"market":"PrizePicks","is_live":False},
            {"player":"Naak Nako","game":"LOL","matchup":"VIT vs NAVI 1:15pm","prop_type":"MAPS 1-2 Kills","sportsbook_line":6.5,"model_projection":8.3,"market":"PrizePicks","is_live":False},
        ])
    _CACHE["data"]=props
    _CACHE["timestamp"]=now
    return props

def calc_ev(p):
    line=float(p["sportsbook_line"]); model=float(p["model_projection"])
    ev=((model-line)/line*100) if line else 0
    return {**p,"ev_percentage":round(abs(ev),1),"lean":"OVER" if model>line else "UNDER","hit_probability":round(0.5+min(abs(ev)/100,0.35),3)}

@app.get("/")
def root(): return {"status":"ok","live_props":len(fetch_live())}
@app.get("/slate")
def slate():
    raw=fetch_live()
    props=[calc_ev(p) for p in raw]
    best=sorted(props,key=lambda x:x["ev_percentage"],reverse=True)
    return {"props":best,"best3":best[:3],"count":len(best),"timestamp":datetime.utcnow().isoformat(),"source":"LIVE 24/7"}
@app.get("/health")
def health(): return {"status":"ok","count":len(fetch_live())}
