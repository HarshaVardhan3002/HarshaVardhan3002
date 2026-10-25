"""Write Claude Code usage totals to choom.json (totals only, no session data); the workflow draws assets/choom.svg.
Numbers come only from ~/.claude/stats-cache.json, which Claude Code refreshes itself (counting the raw session
logs gives different totals). With --push, the file is uploaded to the profile repo via the gh CLI instead."""
import base64
import json
import os
import subprocess
import sys
from datetime import date, timedelta

REPO = "HarshaVardhan3002/HarshaVardhan3002"
HOME = os.path.expanduser("~/.claude")
GH = os.environ.get("GH_EXE", "gh")


def build():
    d = json.load(open(os.path.join(HOME, "stats-cache.json"), encoding="utf-8"))
    last = d["lastComputedDate"]
    days = {x["date"]: x["messageCount"] for x in d["dailyActivity"] if x["date"] <= last}
    hours = {int(h): n for h, n in d["hourCounts"].items()}
    start, end = date.fromisoformat(min(days)), date.fromisoformat(max(days))
    usage = d["modelUsage"].values()
    return {
        "since": min(days),
        "updated": max(days),
        "days_active": sum(1 for n in days.values() if n),
        "sessions": d["totalSessions"],
        "messages": d["totalMessages"],
        "tool_calls": sum(x["toolCallCount"] for x in d["dailyActivity"] if x["date"] <= last),
        "tokens": sum(v[k] for v in usage for k in ("inputTokens", "outputTokens",
                                                               "cacheReadInputTokens", "cacheCreationInputTokens")),
        "peak_hour": max(hours, key=hours.get),
        "daily": [days.get((start + timedelta(i)).isoformat(), 0) for i in range((end - start).days + 1)],
    }


def push(text):
    def gh(*args, data=None):
        r = subprocess.run([GH, "api", *args], input=data, capture_output=True, text=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode, r.stdout
    code, out = gh(f"repos/{REPO}/contents/choom.json")
    sha = json.loads(out)["sha"] if code == 0 else None
    if sha and base64.b64decode(json.loads(out)["content"]).decode() == text:
        return "unchanged"
    body = {"message": "Refresh choom stats", "content": base64.b64encode(text.encode()).decode()}
    if sha:
        body["sha"] = sha
    code, out = gh("-X", "PUT", f"repos/{REPO}/contents/choom.json", "--input", "-", data=json.dumps(body))
    return "pushed" if code == 0 else f"failed: {out[:200]}"


if __name__ == "__main__":
    out = build()
    text = json.dumps(out, indent=1) + "\n"
    if "--push" in sys.argv:
        print(push(text))
    else:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "choom.json"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(text)
    print({k: v for k, v in out.items() if k != "daily"})
