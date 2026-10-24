"""Refresh the Hugging Face numbers in README.md and the badge JSON files. Run daily by the workflow."""
import json
import re
import urllib.request

USER = "Harsha001"
URL = (f"https://huggingface.co/api/models?author={USER}&limit=1000"
       "&expand[]=downloadsAllTime&expand[]=likes&expand[]=pipeline_tag")

with urllib.request.urlopen(URL, timeout=60) as r:
    models = json.load(r)
models.sort(key=lambda m: m.get("downloadsAllTime", 0), reverse=True)
total = sum(m.get("downloadsAllTime", 0) for m in models)
likes = sum(m.get("likes", 0) for m in models)


def badge(name, label, message, color):
    with open(name, "w") as f:
        json.dump({"schemaVersion": 1, "label": label, "message": message, "color": color,
                   "namedLogo": "huggingface", "logoColor": "white"}, f)


badge("hf-downloads.json", "Hugging Face downloads", f"{total:,}", "FFD21E")
badge("hf-models.json", "models", str(len(models)), "FF9D00")

rows = [f"| [{m['id'].split('/', 1)[1]}](https://huggingface.co/{m['id']}) | {m.get('pipeline_tag') or ''} "
        f"| {m.get('downloadsAllTime', 0):,} |" for m in models[:8]]
more = len(models) - len(rows)
block = "\n".join([
    f"**{total:,} downloads** across **{len(models)} models** and **{likes} likes** on "
    f"[Hugging Face](https://huggingface.co/{USER}) (all time, updated daily).",
    "",
    "| Model | Task | Downloads |",
    "|---|---|---:|",
    *rows,
    *([f"", f"[and {more} more on Hugging Face](https://huggingface.co/{USER}?sort_models=downloads#models)"] if more > 0 else []),
])

with open("README.md", encoding="utf-8") as f:
    readme = f.read()
readme = re.sub(r"(<!-- HF:START -->).*?(<!-- HF:END -->)", lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}",
                readme, flags=re.S)
with open("README.md", "w", encoding="utf-8", newline="\n") as f:
    f.write(readme)
print(total, len(models), likes)
