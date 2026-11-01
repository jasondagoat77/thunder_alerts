"""Pings your phone (via ntfy.sh) about Oklahoma City Thunder games.

Sends one notification each for: 30 min before tip-off, tip-off, and final score.
Meant to be run every few minutes by a scheduler (GitHub Actions or Windows Task Scheduler).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TEAM = "OKC"
PREGAME_MINUTES = 30

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
HERE = Path(__file__).parent
STATE_FILE = HERE / "notified.json"
LOG_FILE = HERE / "thunder_alerts.log"
TOPIC_FILE = HERE / "ntfy_topic.txt"  # local fallback; kept out of git

# The ntfy topic you subscribe to in the phone app. Kept secret: anyone who knows it can read/send alerts.
TOPIC = os.environ.get("NTFY_TOPIC") or (TOPIC_FILE.read_text().strip() if TOPIC_FILE.exists() else None)


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def notify(title, message, tags="basketball"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Tags": tags},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=20).close()
    log(f"SENT  {title} | {message}")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def main():
    if not TOPIC:
        raise RuntimeError("No ntfy topic: set NTFY_TOPIC or create ntfy_topic.txt")

    if "--test" in sys.argv:
        notify("Thunder alerts are set up", "You'll get pinged before, during, and after OKC games.")
        return

    events = fetch_json(SCOREBOARD_URL)["events"]
    state = load_state()

    for e in events:
        teams = {t["homeAway"]: t for t in e["competitions"][0]["competitors"]}
        home, away = teams["home"], teams["away"]
        if TEAM not in (home["team"]["abbreviation"], away["team"]["abbreviation"]):
            continue

        gid = e["id"]
        sent = state.setdefault(gid, [])
        matchup = f'{away["team"]["displayName"]} @ {home["team"]["displayName"]}'
        score = (f'{away["team"]["abbreviation"]} {away["score"]} - '
                 f'{home["team"]["abbreviation"]} {home["score"]}')
        status = e["status"]["type"]["state"]  # "pre", "in", or "post"
        detail = e["status"]["type"]["shortDetail"]

        if status == "pre" and "pregame" not in sent:
            tip = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            minutes_left = (tip - datetime.now(timezone.utc)).total_seconds() / 60
            if 0 < minutes_left <= PREGAME_MINUTES:
                local_tip = tip.astimezone().strftime("%I:%M %p").lstrip("0")
                notify("Thunder game soon", f"{matchup} tips off at {local_tip}", "alarm_clock")
                sent.append("pregame")

        elif status == "in" and "live" not in sent:
            notify("Thunder game is ON", f"{matchup}\n{score} ({detail})", "basketball")
            sent.append("live")

        elif status == "post" and "final" not in sent:
            okc = home if home["team"]["abbreviation"] == TEAM else away
            opp = away if okc is home else home
            result = "WIN" if int(okc["score"]) > int(opp["score"]) else "Loss"
            notify(f"Thunder {result}", f"Final: {score}", "trophy" if result == "WIN" else "basketball")
            sent.append("final")
            sent.append("live")  # don't send a late "game is on" if we missed the live window

    # Keep only the most recent 20 games in state
    state = dict(list(state.items())[-20:])
    STATE_FILE.write_text(json.dumps(state, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR {type(e).__name__}: {e}")
        sys.exit(1)
