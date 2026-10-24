"""Write Claude Code usage totals to choom.json (totals only, no session data); the workflow draws assets/choom.svg.
Base numbers come from ~/.claude/stats-cache.json. Days after the cache's last date are counted from the session
logs in ~/.claude/projects. With --push, the file is uploaded to the profile repo via the gh CLI instead."""
import base64
import glob
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

REPO = "HarshaVardhan3002/HarshaVardhan3002"
HOME = os.path.expanduser("~/.claude")
GH = os.environ.get("GH_EXE", "gh")


def recent(after):
    """Totals from the session logs for days after `after` (YYYY-MM-DD)."""
    cutoff = datetime.fromisoformat(after).timestamp() + 86400
    days, hours, sessions, seen = {}, {}, {}, set()
    tools = tokens = 0
    for path in glob.glob(os.path.join(HOME, "projects", "**", "*.jsonl"), recursive=True):
        if os.path.getmtime(path) < cutoff:
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"type":"user"' not in line and '"type":"assistant"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                ts = d.get("timestamp", "")
                if d.get("type") not in ("user", "assistant") or ts[:10] <= after:
                    continue
                days[ts[:10]] = days.get(ts[:10], 0) + 1
                sid = d.get("sessionId")
                if sid and (sid not in sessions or ts < sessions[sid]):
                    sessions[sid] = ts
                m = d.get("message") or {}
                if d["type"] == "assistant" and isinstance(m.get("content"), list):
                    tools += sum(1 for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_use")
                    u = m.get("usage") or {}
                    if m.get("id") and m["id"] not in seen:
                        seen.add(m["id"])
                        tokens += sum(u.get(k) or 0 for k in ("input_tokens", "output_tokens",
                                                              "cache_read_input_tokens", "cache_creation_input_tokens"))
    for ts in sessions.values():
        h = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().hour
        hours[h] = hours.get(h, 0) + 1
    return days, hours, len(sessions), tools, tokens


def build():
    d = json.load(open(os.path.join(HOME, "stats-cache.json"), encoding="utf-8"))
    last = d["lastComputedDate"]
    days = {x["date"]: x["messageCount"] for x in d["dailyActivity"] if x["date"] <= last}
    hours = {int(h): n for h, n in d["hourCounts"].items()}
    new_days, new_hours, n_sessions, n_tools, n_tokens = recent(last)
    for k, v in new_days.items():
        days[k] = days.get(k, 0) + v
    for k, v in new_hours.items():
        hours[k] = hours.get(k, 0) + v
    start, end = date.fromisoformat(min(days)), date.fromisoformat(max(days))
    usage = d["modelUsage"].values()
    return {
        "since": min(days),
        "updated": max(days),
        "days_active": sum(1 for n in days.values() if n),
        "sessions": d["totalSessions"] + n_sessions,
        "messages": d["totalMessages"] + sum(new_days.values()),
        "tool_calls": sum(x["toolCallCount"] for x in d["dailyActivity"] if x["date"] <= last) + n_tools,
        "tokens": n_tokens + sum(v[k] for v in usage for k in ("inputTokens", "outputTokens",
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
