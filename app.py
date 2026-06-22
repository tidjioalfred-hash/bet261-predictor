#!/usr/bin/env python3
"""
BET 261 PREDICTOR — Flask version for Render.com deployment
"""

from flask import Flask, jsonify, request, render_template_string
import random, math, statistics
from collections import deque

app = Flask(__name__)

# ─── Moteur Aviator ──────────────────────────────────────────────────────────

class AviatorPredictor:
    def __init__(self):
        self.history = deque(maxlen=200)
        for v in [1.2,3.4,1.1,2.8,1.5,6.2,1.3,1.9,4.1,1.2,2.3,1.1,1.8,12.4,1.4,2.0,1.6,3.7,1.2,2.5]:
            self.history.append(v)

    def add_result(self, multiplier):
        self.history.append(round(multiplier, 2))

    def _pareto_cdf(self, x, alpha=1.5, xm=1.0):
        if x < xm: return 0
        return 1 - (xm / x) ** alpha

    def _analyze_streak(self):
        if len(self.history) < 5: return "neutre", 0.5
        recent = list(self.history)[-10:]
        low_count = sum(1 for x in recent if x < 1.5)
        high_count = sum(1 for x in recent if x >= 2.0)
        if low_count >= 7: return "froid", 0.72
        if high_count >= 5: return "chaud", 0.45
        return "neutre", 0.58

    def _cycle_detection(self):
        if len(self.history) < 20: return None
        vals = list(self.history)[-40:]
        big = [i for i, v in enumerate(vals) if v >= 2.0]
        if len(big) < 3: return None
        gaps = [big[i+1] - big[i] for i in range(len(big)-1)]
        avg_gap = statistics.mean(gaps)
        std_gap = statistics.stdev(gaps) if len(gaps) > 1 else 99
        if std_gap < avg_gap * 0.4:
            last_big = big[-1]
            rounds_since = len(vals) - 1 - last_big
            return avg_gap, rounds_since
        return None

    def predict(self, target_multiplier=2.0):
        streak_type, streak_prob = self._analyze_streak()
        cycle_info = self._cycle_detection()
        base_prob = 1 - self._pareto_cdf(target_multiplier, alpha=1.8)
        base_prob = max(0.05, min(0.92, base_prob))
        adjusted = base_prob * 0.6 + streak_prob * 0.4
        cycle_bonus = 0.0
        cycle_note = ""
        if cycle_info:
            avg_gap, rounds_since = cycle_info
            if abs(rounds_since - avg_gap) <= 2:
                cycle_bonus = 0.12
                cycle_note = f"⚡ Cycle détecté (~{avg_gap:.1f} rounds), moment favorable"
            elif rounds_since > avg_gap + 3:
                cycle_bonus = 0.08
                cycle_note = f"📈 Overdue: {rounds_since:.0f} rounds depuis dernier x{target_multiplier}"
        final_prob = min(0.92, adjusted + cycle_bonus)
        n = len(self.history)
        if n < 10: confidence, conf_val = "Faible", 30
        elif n < 30: confidence, conf_val = "Modéré", 55
        elif n < 80: confidence, conf_val = "Bon", 72
        else: confidence, conf_val = "Élevé", 88
        if final_prob >= 0.65: rec, rec_class = "✅ MISE RECOMMANDÉE", "green"
        elif final_prob >= 0.45: rec, rec_class = "⚠️ MISE PRUDENTE", "amber"
        else: rec, rec_class = "❌ ATTENDRE", "red"
        if final_prob >= 0.7: cashout = round(random.uniform(1.4, 1.9), 2)
        elif final_prob >= 0.5: cashout = round(random.uniform(1.2, 1.5), 2)
        else: cashout = 1.20
        return {
            "probability": round(final_prob * 100, 1),
            "confidence": confidence, "conf_val": conf_val,
            "recommendation": rec, "rec_class": rec_class,
            "cashout_advice": cashout, "target": target_multiplier,
            "details": {"streak": streak_type, "cycle_note": cycle_note, "n_samples": n, "base_prob": round(base_prob*100,1)},
        }

    def stats(self):
        if not self.history: return {}
        vals = list(self.history)
        return {
            "count": len(vals), "mean": round(statistics.mean(vals),2),
            "median": round(statistics.median(vals),2), "max": round(max(vals),2),
            "min": round(min(vals),2),
            "pct_above_2": round(sum(1 for v in vals if v>=2)/len(vals)*100,1),
            "pct_above_5": round(sum(1 for v in vals if v>=5)/len(vals)*100,1),
            "last_10": list(reversed(list(self.history)[-10:])),
        }


class VirtualMatchPredictor:
    TEAMS = ["Manchester City","Real Madrid","Bayern Munich","PSG","Liverpool","Barcelona",
             "Juventus","Atletico Madrid","Chelsea","Dortmund","Inter Milan","Arsenal",
             "Lyon","Porto","Ajax","Benfica"]

    def __init__(self):
        self.team_stats = {
            t: {"attack": round(random.uniform(0.8,2.2),2),
                "defense": round(random.uniform(0.6,1.8),2),
                "form": [random.choice(["W","D","L"]) for _ in range(5)]}
            for t in self.TEAMS
        }

    def _form_score(self, form):
        return sum({"W":3,"D":1,"L":0}[r] for r in form)/15

    def _poisson_pmf(self, k, lam):
        return (lam**k)*math.exp(-lam)/math.factorial(k)

    def predict_match(self, home, away):
        h = self.team_stats.get(home, {"attack":1.2,"defense":1.0,"form":["W","D","W","L","W"]})
        a = self.team_stats.get(away, {"attack":1.1,"defense":1.0,"form":["D","W","L","W","D"]})
        lh = max(0.3, min(4.0, h["attack"]/a["defense"]*1.3))
        la = max(0.3, min(4.0, a["attack"]/h["defense"]*0.9))
        p_home=p_draw=p_away=0.0
        for gh in range(8):
            for ga in range(8):
                p = self._poisson_pmf(gh,lh)*self._poisson_pmf(ga,la)
                if gh>ga: p_home+=p
                elif gh==ga: p_draw+=p
                else: p_away+=p
        adj = (self._form_score(h["form"])-self._form_score(a["form"]))*0.08
        p_home=max(0.05,min(0.85,p_home+adj))
        p_away=max(0.05,min(0.85,p_away-adj))
        total=p_home+p_draw+p_away
        p_home/=total; p_draw/=total; p_away/=total
        probs=[("1 (Domicile)",p_home,home),("X (Nul)",p_draw,"Match nul"),("2 (Extérieur)",p_away,away)]
        best=max(probs,key=lambda x:x[1])
        kelly=max(0,(best[1]*(1/best[1]+0.1)-1)/(1/best[1]+0.1-1))
        spread=max(p_home,p_draw,p_away)-min(p_home,p_draw,p_away)
        conf_val=min(95,max(35,int(40+spread*120)))
        return {
            "home":home,"away":away,
            "p_home":round(p_home*100,1),"p_draw":round(p_draw*100,1),"p_away":round(p_away*100,1),
            "pred_score":f"{round(lh)} - {round(la)}",
            "lambda_home":round(lh,2),"lambda_away":round(la,2),
            "best_bet":best[0],"best_team":best[2],"best_prob":round(best[1]*100,1),
            "kelly_pct":round(kelly*100,1),
            "confidence":"Élevé" if conf_val>=70 else "Modéré" if conf_val>=50 else "Faible",
            "conf_val":conf_val,
            "form_home":h["form"],"form_away":a["form"],
        }

    def get_teams(self): return sorted(self.TEAMS)


aviator = AviatorPredictor()
virtual = VirtualMatchPredictor()

# ─── Routes API ──────────────────────────────────────────────────────────────

@app.route("/api/aviator/add")
def aviator_add():
    try:
        v = float(request.args.get("v", 0))
        if v < 1.0: raise ValueError
        aviator.add_result(v)
        return jsonify(aviator.stats())
    except: return jsonify({"error":"invalid"}), 400

@app.route("/api/aviator/predict")
def aviator_predict():
    target = float(request.args.get("target", 2.0))
    return jsonify(aviator.predict(max(1.1, min(20.0, target))))

@app.route("/api/aviator/stats")
def aviator_stats():
    return jsonify(aviator.stats())

@app.route("/api/virtual/teams")
def virtual_teams():
    return jsonify({"teams": virtual.get_teams()})

@app.route("/api/virtual/predict")
def virtual_predict():
    home = request.args.get("home", "Manchester City")
    away = request.args.get("away", "Real Madrid")
    return jsonify(virtual.predict_match(home, away))

# ─── Page principale ──────────────────────────────────────────────────────────

HTML = open("index.html").read()

@app.route("/")
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8261))
    app.run(host="0.0.0.0", port=port, debug=False)
