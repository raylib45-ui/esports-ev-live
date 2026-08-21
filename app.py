from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import math
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BOARD = [
 {"player":"NiKo","game":"CS2","matchup":"Falcons vs Legacy 9:55am","prop_type":"MAPS 1-2 Kills","line":30.5,"proj":26.8},
 {"player":"ZywOo","game":"CS2","matchup":"Vitality vs Team Spirit 12:50pm","prop_type":"MAPS 1-2 AWP Kills","line":14.5,"proj":17.3},
 {"player":"s1mple","game":"CS2","matchup":"NAVI vs Falcons 11:30am","prop_type":"Kills","line":19.5,"proj":22.4},
 {"player":"ATF","game":"DOTA","matchup":"Falcons vs Liquid 0:45","prop_type":"MAPS 1-2 Kills","line":12.5,"proj":14.8},
 {"player":"OmaR","game":"DOTA","matchup":"NGX vs Yandex 7:00am","prop_type":"MAPS 1-2 Kills","line":5.0,"proj":7.2},
 {"player":"Nisha","game":"DOTA","matchup":"Liquid vs Falcons 0:45","prop_type":"MAPS 1-2 Kills","line":16.0,"proj":13.2},
 {"player":"HYUNMIN","game":"VAL","matchup":"DRX vs Sharper 4:00am","prop_type":"MAPS 1-2 Kills","line":34.5,"proj":30.1},
 {"player":"LarOk","game":"VAL","matchup":"BBL vs FUT 2:00pm","prop_type":"MAPS 1-2 Kills","line":32.5,"proj":36.2},
 {"player":"GIDEON","game":"LOL","matchup":"BRO vs BFX 4:00am","prop_type":"MAPS 1-2 Kills","line":7.0,"proj":5.4},
 {"player":"Naak Nako","game":"LOL","matchup":"VIT vs NAVI 1:15pm","prop_type":"MAPS 1-2 Kills","line":6.5,"proj":8.3},
]
def cdf(x): return (1.0+math.erf(x/math.sqrt(2.0)))/2.0
def calc(p,l,g,pt):
 sigma={"CS2":3.2,"DOTA":2.2,"VAL":4.0,"LOL":1.8}.get(g,2.5)
 if "MAPS" in pt: sigma*=1.5
 lean="OVER" if p>l else "UNDER"
 z=(l-p)/sigma
 prob=1-cdf(z) if lean=="OVER" else cdf(z)
 prob=max(0.4,min(0.85,prob))
 ev=(prob/0.543-1)*100
 return lean,round(prob,4),round(ev,2)
@app.get("/slate")
def slate():
 res=[]
 for r in BOARD:
  lean,prob,ev=calc(r["proj"],r["line"],r["game"],r["prop_type"])
  res.append({**r,"lean":lean,"hit_probability":prob,"ev_percentage":ev})
 res.sort(key=lambda x:x["ev_percentage"],reverse=True)
 return {"props":res,"best3":res[:3]}
@app.get("/")
def root(): return {"status":"LIVE 18 props"}
