"""Copy Claude Code usage totals from ~/.claude/stats-cache.json into choom.json (totals only, no session data).
Run on the PC, then commit choom.json; the workflow draws assets/choom.svg from it."""
import json
import os
from datetime import date, timedelta

d = json.load(open(os.path.expanduser("~/.claude/stats-cache.json"), encoding="utf-8"))
days = {x["date"]: x["messageCount"] for x in d["dailyActivity"]}
start, end = date.fromisoformat(min(days)), date.fromisoformat(d["lastComputedDate"])
usage = d["modelUsage"].values()
hours = {int(h): n for h, n in d["hourCounts"].items()}
out = {
    "since": min(days),
    "updated": d["lastComputedDate"],
    "days_active": sum(1 for n in days.values() if n),
    "sessions": d["totalSessions"],
    "messages": d["totalMessages"],
    "tool_calls": sum(x["toolCallCount"] for x in d["dailyActivity"]),
    "tokens": sum(v[k] for v in usage for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")),
    "peak_hour": max(hours, key=hours.get),
    "daily": [days.get((start + timedelta(i)).isoformat(), 0) for i in range((end - start).days + 1)],
}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "choom.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, indent=1)
print({k: v for k, v in out.items() if k != "daily"})
