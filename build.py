"""Build the profile SVGs in assets/. Run daily by the workflow (live numbers from the GitHub and Hugging Face APIs)."""
import json
import os
import urllib.request
from xml.sax.saxutils import escape

GH_USER = "HarshaVardhan3002"
HF_USER = "Harsha001"

Y, C, R, BG, PANEL, DIM, TXT = "#FCEE0A", "#02D7F2", "#FF003C", "#07080B", "#0E1015", "#5C6370", "#C9D1D9"
MONO = "font-family=\"'Courier New',Consolas,'DejaVu Sans Mono',monospace\""
# repos that are mostly upstream code, left out of the language stats
UPSTREAM_FORKS = {"ROCmFPX"}
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Shell", "PowerShell", "Batchfile", "Makefile", "CMake", "Dockerfile"}
LANG_COLORS = {"Svelte": "#FF3E00", "Kotlin": "#A97BFF", "Cuda": "#3A4E3A", "GLSL": "#5686A5", "Metal": "#8F14E9",
               "Objective-C": "#438EFF", "Swift": "#F05138", "Go": "#00ADD8", "Java": "#B07219", "Rust": "#DEA584", "C": "#A8B9CC", "C++": "#F34B7D", "Python": "#3572A5", "TypeScript": "#3178C6",
               "JavaScript": "#F1E05A", "Dart": "#00B4AB", "HTML": "#E34C26", "Jupyter Notebook": "#DA5B0B"}

# name shown, repo (or url), tag, description lines, language
PROJECTS = [
    ("NIMBUS", "Nimbus_revanced", "DESKTOP AI ASSISTANT",
     ["Always-on assistant pill that lives on your", "desktop and automates the small stuff."], "Rust"),
    ("ZUNZUN", "zunzun", "INFERENCE ENGINE",
     ["Runs huge open-weight MoE models on", "everyday machines with limited RAM."], "C"),
    ("NIMBUS HUD", "nimbus", "SCREEN AGENT",
     ["Agent overlay for Windows and Mac that", "answers questions about anything on screen."], "JavaScript"),
    ("DAIMON", "Daimon", "MOBILE AI CHAT",
     ["A chat app for language models,", "built for your phone."], "TypeScript"),
    ("SCIONFIT", "SCIONfit", "MODEL TESTBED",
     ["Puts AI models through agentic workflows", "in a near-deployment environment."], "Python"),
    ("HCR-EV", "HCR-EV", "EDGE AI",
     ["Real-time EV powertrain optimization with", "sensor fusion and causal reasoning."], "Python"),
    ("NAMMA OFFICE", "https://harshavardhan3002.github.io/namma-office-downloads/", "PRODUCTIVITY SUITE",
     ["Spreadsheet, writer and PDF apps", "with Kannada typing."], "Rust"),
    ("ROCMFPX", "ROCmFPX", "GPU KERNELS",
     ["llama.cpp fork with low-bit weight types", "for AMD GPUs (Vulkan and HIP)."], "C++"),
]


def get(url, token=None):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-build"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def save(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)


def frame(w, h, cut=18):
    # Cyberpunk panel outline: top-right and bottom-left corners cut off
    return f"{1},{1} {w - cut},{1} {w - 1},{cut} {w - 1},{h - 1} {cut},{h - 1} {1},{h - cut}"


def banner():
    w, h = 1280, 360
    bars = []
    x = 900
    for i, bw in enumerate([3, 1, 2, 1, 4, 1, 1, 3, 2, 1, 3, 1, 2, 4, 1, 2, 1, 3, 1, 1, 2, 3, 1, 2, 1, 4, 2, 1, 3, 1]):
        if i % 2 == 0:
            bars.append(f'<rect x="{x}" y="268" width="{bw * 2}" height="34" fill="{Y}"/>')
        x += bw * 2 + 2
    title = f'x="80" y="205" {MONO} font-size="140" font-weight="700" letter-spacing="22"'
    hud = [("SYS.STATUS", "ONLINE", C), ("CLASS", "NETRUNNER", Y), ("NEURAL LINK", "STABLE", C),
           ("LOCATION", "[REDACTED]", R), ("IDENTITY", "[CLASSIFIED]", R)]
    hud_svg = "".join(
        f'<text x="900" y="{108 + i * 30}" {MONO} font-size="17" fill="{DIM}">{k} <tspan fill="{DIM}">'
        f'{"." * (16 - len(k))}</tspan> <tspan fill="{v_c}" font-weight="700"'
        f'{" class=\"blink\"" if v == "ONLINE" else ""}>{v}</tspan></text>'
        for i, (k, v, v_c) in enumerate(hud))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{C}" stroke-opacity="0.07"/></pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.035"/></pattern>
<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C}" stop-opacity="0"/><stop offset="1" stop-color="{C}" stop-opacity="0.12"/></linearGradient>
<clipPath id="s1"><rect x="0" y="118" width="{w}" height="18"/></clipPath>
<clipPath id="s2"><rect x="0" y="160" width="{w}" height="12"/></clipPath>
<clipPath id="s3"><rect x="0" y="186" width="{w}" height="9"/></clipPath>
<style>
@keyframes gr{{0%,84%,100%{{transform:translate(0,0)}}86%{{transform:translate(-7px,2px)}}88%{{transform:translate(6px,-2px)}}90%{{transform:translate(-3px,1px)}}92%{{transform:translate(0,0)}}}}
@keyframes gc{{0%,84%,100%{{transform:translate(0,0)}}86%{{transform:translate(7px,-2px)}}88%{{transform:translate(-6px,2px)}}90%{{transform:translate(3px,0)}}92%{{transform:translate(0,0)}}}}
@keyframes sl{{0%,85%,93%,100%{{transform:translateX(0);opacity:0}}86%{{transform:translateX(-26px);opacity:1}}88%{{transform:translateX(18px);opacity:1}}90%{{transform:translateX(-10px);opacity:1}}}}
@keyframes flick{{0%,18%,22%,62%,64%,100%{{opacity:1}}20%,63%{{opacity:.35}}}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes sweep{{from{{transform:translateY(-120px)}}to{{transform:translateY({h}px)}}}}
@keyframes load{{0%{{transform:scaleX(0)}}70%,100%{{transform:scaleX(1)}}}}
.gr{{animation:gr 4s infinite steps(1)}} .gc{{animation:gc 4s infinite steps(1)}}
.s1{{animation:sl 4s infinite steps(1)}} .s2{{animation:sl 4s .12s infinite steps(1)}} .s3{{animation:sl 4s .06s infinite steps(1)}}
.flick{{animation:flick 5s infinite}} .blink{{animation:blink 1s infinite steps(1)}}
.sweep{{animation:sweep 6s linear infinite}} .load{{transform-origin:960px 0;animation:load 5s ease-in-out infinite}}
</style>
</defs>
<rect width="{w}" height="{h}" fill="{BG}"/>
<rect width="{w}" height="{h}" fill="url(#grid)"/>
<rect class="sweep" width="{w}" height="120" fill="url(#sweep)"/>
<polygon points="{frame(w - 40, h - 40, 40)}" transform="translate(20,20)" fill="none" stroke="{Y}" stroke-width="2"/>
<polygon points="20,20 380,20 362,48 20,48" fill="{Y}"/>
<text x="34" y="40" {MONO} font-size="17" font-weight="700" fill="{BG}">// NETRUNNER PROFILE v2.077</text>
<rect x="{w - 60}" y="{h - 34}" width="40" height="6" fill="{R}"/><rect x="{w - 110}" y="{h - 34}" width="40" height="6" fill="{Y}"/>
<g class="flick">
<text {title} fill="{R}" class="gr" opacity="0.9">GHOST</text>
<text {title} fill="{C}" class="gc" opacity="0.9">GHOST</text>
<text {title} fill="{Y}">GHOST</text>
<g clip-path="url(#s1)"><g class="s1"><rect x="60" y="100" width="620" height="120" fill="{BG}"/><text {title} fill="{C}">GHOST</text></g></g>
<g clip-path="url(#s2)"><g class="s2"><rect x="60" y="100" width="620" height="120" fill="{BG}"/><text {title} fill="{Y}">GHOST</text></g></g>
<g clip-path="url(#s3)"><g class="s3"><rect x="60" y="100" width="620" height="120" fill="{BG}"/><text {title} fill="{R}">GHOST</text></g></g>
</g>
<text x="84" y="252" {MONO} font-size="22" font-weight="700" fill="{C}" letter-spacing="3">AI ENGINEER // SYSTEMS DEVELOPER // APP BUILDER</text>
<text x="84" y="300" {MONO} font-size="17" fill="{DIM}">&gt; jack_in --user ghost --mode stealth<tspan fill="{Y}" class="blink"> &#9608;</tspan></text>
<text x="84" y="88" {MONO} font-size="15" fill="{R}" letter-spacing="2">[ 0x47484F5354 ]</text>
<line x1="880" y1="76" x2="880" y2="300" stroke="{Y}" stroke-opacity="0.5"/>
{hud_svg}
<text x="900" y="258" {MONO} font-size="13" fill="{DIM}">UPLINK</text>
<rect x="960" y="248" width="250" height="10" fill="none" stroke="{C}" stroke-opacity="0.6"/>
<rect class="load" x="960" y="248" width="250" height="10" fill="{C}" opacity="0.8"/>
{''.join(bars)}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def terminal():
    lines = [("ghost@nightcity:~$ ", "whoami"),
             ("", "> developer. netrunner. I build AI that runs on your own machine."),
             ("ghost@nightcity:~$ ", "cat ./focus"),
             ("", "> AI apps · desktop agents · inference engines · local LLMs"),
             ("ghost@nightcity:~$ ", "ls ./stack"),
             ("", "> rust  c++  python  typescript  dart  cuda  rocm  vulkan"),
             ("ghost@nightcity:~$ ", "uptime"),
             ("", "> always on. occasionally sober enough to ship.")]
    w, fs, cw, lh, x0 = 1280, 21, 12.65, 34, 34
    h = 80 + lh * len(lines) + 20
    t, out, css = 0.4, [], []
    # Each line is drawn in full, then hidden by panel-coloured covers: the prompt cover vanishes when the line
    # starts, the text cover slides right one character per step (CSS transforms only, so it plays everywhere).
    for i, (prompt, cmd) in enumerate(lines):
        y = 82 + i * lh
        pw = len(prompt) * cw
        n = len(cmd)
        dur = 0.05 * n if prompt else 0.012 * n
        if prompt:
            out.append(f'<text x="{x0}" y="{y}" {MONO} font-size="{fs}" xml:space="preserve"><tspan fill="{Y}" '
                       f'font-weight="700">{escape(prompt)}</tspan><tspan fill="{TXT}">{escape(cmd)}</tspan></text>')
            out.append(f'<rect class="p{i}" x="{x0 - 2}" y="{y - 24}" width="{pw + 2:.1f}" height="{lh}" fill="{PANEL}"/>')
            css.append(f".p{i}{{animation:hide .01s {t:.2f}s both}}")
        else:
            out.append(f'<text x="{x0}" y="{y}" {MONO} font-size="{fs}" fill="{C}" xml:space="preserve">{escape(cmd)}</text>')
        out.append(f'<rect class="c{i}" x="{x0 + pw:.1f}" y="{y - 24}" width="{w - 40 - x0 - pw:.1f}" height="{lh}" fill="{PANEL}"/>')
        css.append(f"@keyframes t{i}{{from{{transform:translateX(0)}}to{{transform:translateX({n * cw + 4:.1f}px)}}}}"
                   f".c{i}{{animation:t{i} {dur:.2f}s steps({n}) {t + (0.3 if prompt else 0):.2f}s both}}")
        t += dur + (0.6 if prompt else 0.7)
    yc = 82 + len(lines) * lh
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><clipPath id="inner"><rect x="2" y="36" width="{w - 6}" height="{h - 40}"/></clipPath>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<style>@keyframes blink{{50%{{opacity:0}}}} @keyframes hide{{from{{opacity:1}}to{{opacity:0}}}} @keyframes show{{from{{opacity:0}}to{{opacity:1}}}}
.blink{{animation:blink 1s infinite steps(1)}} .last{{animation:show .01s {t:.2f}s both}}
{chr(10).join(css)}</style></defs>
<polygon points="{frame(w, h, 26)}" fill="{PANEL}" stroke="{C}" stroke-opacity="0.55" stroke-width="2"/>
<rect x="1" y="1" width="{w - 27}" height="34" fill="{C}" opacity="0.12"/>
<circle cx="26" cy="18" r="6" fill="{R}"/><circle cx="46" cy="18" r="6" fill="{Y}"/><circle cx="66" cy="18" r="6" fill="{C}"/>
<text x="96" y="24" {MONO} font-size="15" fill="{C}" letter-spacing="2">ghost@nightcity :: /dev/neural0</text>
<g clip-path="url(#inner)">{''.join(out)}</g>
<text class="last" x="{x0}" y="{yc}" {MONO} font-size="{fs}" xml:space="preserve"><tspan fill="{Y}" font-weight="700">ghost@nightcity:~$ </tspan><tspan fill="{Y}" class="blink">&#9608;</tspan></text>
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def section(num, title, w=1280, h=64):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<polygon points="0,8 470,8 446,56 0,56" fill="{Y}"/>
<text x="22" y="42" {MONO} font-size="26" font-weight="700" fill="{BG}">{num} // {escape(title)}</text>
<line x1="470" y1="54" x2="{w}" y2="54" stroke="{Y}" stroke-width="2"/>
<rect x="{w - 90}" y="40" width="90" height="8" fill="{R}"/>
<text x="{w - 100}" y="44" {MONO} font-size="13" fill="{DIM}" text-anchor="end">SECTOR {num}</text>
</svg>"""


def card(i, name, tag, desc, lang, stars):
    w, h = 620, 210
    lc = LANG_COLORS.get(lang, DIM)
    star = f'<text x="{w - 30}" y="{h - 26}" {MONO} font-size="17" fill="{Y}" text-anchor="end">&#9733; {stars}</text>' if stars else ""
    body = "".join(f'<text x="30" y="{122 + k * 27}" {MONO} font-size="18" fill="{TXT}">{escape(l)}</text>'
                   for k, l in enumerate(desc))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<style>@keyframes pulse{{0%,100%{{opacity:.25}}50%{{opacity:1}}}} .p{{animation:pulse 2.4s infinite}}</style></defs>
<polygon points="{frame(w, h, 22)}" fill="{PANEL}" stroke="{Y}" stroke-opacity="0.85" stroke-width="2"/>
<polygon points="{w - 22},1 {w - 1},22 {w - 1},1" fill="{Y}"/>
<text x="30" y="46" {MONO} font-size="15" fill="{R}" letter-spacing="2">{i:02d}</text>
<text x="64" y="47" {MONO} font-size="30" font-weight="700" fill="{Y}" letter-spacing="2">{escape(name)}</text>
<text x="30" y="80" {MONO} font-size="15" fill="{C}" letter-spacing="3">// {escape(tag)}</text>
{body}
<circle cx="38" cy="{h - 32}" r="7" fill="{lc}"/>
<text x="54" y="{h - 26}" {MONO} font-size="16" fill="{DIM}">{escape(lang)}</text>
<rect class="p" x="{w - 140}" y="30" width="10" height="10" fill="{C}"/>
<text x="{w - 122}" y="40" {MONO} font-size="13" fill="{DIM}">ACTIVE</text>
{star}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def stat_panel(title, rows, w=620, h=260, extra=""):
    body = ""
    for k, (label, value, color) in enumerate(rows):
        y = 104 + k * 66
        body += (f'<text x="30" y="{y}" {MONO} font-size="44" font-weight="700" fill="{color}">{escape(value)}</text>'
                 f'<text x="30" y="{y + 24}" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">{escape(label)}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<style>@keyframes blink{{50%{{opacity:0}}}} .blink{{animation:blink 1.2s infinite steps(1)}}</style></defs>
<polygon points="{frame(w, h, 22)}" fill="{PANEL}" stroke="{C}" stroke-opacity="0.7" stroke-width="2"/>
<polygon points="1,1 {w * 0.62:.0f},1 {w * 0.62 - 16:.0f},34 1,34" fill="{C}"/>
<text x="16" y="24" {MONO} font-size="16" font-weight="700" fill="{BG}">{escape(title)}</text>
<rect class="blink" x="{w - 40}" y="14" width="10" height="10" fill="{R}"/>
<text x="{w - 48}" y="24" {MONO} font-size="13" fill="{DIM}" text-anchor="end">LIVE FEED</text>
{body}{extra}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def footer(w=1280, h=70):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>@keyframes blink{{50%{{opacity:0}}}} .blink{{animation:blink 1s infinite steps(1)}}</style>
<line x1="0" y1="20" x2="{w}" y2="20" stroke="{Y}" stroke-width="2"/>
<rect x="0" y="16" width="160" height="8" fill="{R}"/>
<text x="{w / 2}" y="54" {MONO} font-size="18" fill="{Y}" text-anchor="middle" letter-spacing="6">// END OF TRANSMISSION <tspan class="blink">&#9608;</tspan></text>
</svg>"""


def main():
    token = os.environ.get("GITHUB_TOKEN")
    repos = get(f"https://api.github.com/users/{GH_USER}/repos?per_page=100&type=owner", token)
    own = [r for r in repos if not r["fork"]]
    stars = {r["name"]: r["stargazers_count"] for r in repos}
    langs = {}
    for r in own:
        if r["name"] in UPSTREAM_FORKS:
            continue
        for lang, n in get(r["languages_url"], token).items():
            if lang not in SKIP_LANGS:
                langs[lang] = langs.get(lang, 0) + n
    q = json.dumps({"query": f'{{user(login:"{GH_USER}"){{contributionsCollection{{contributionCalendar{{totalContributions}}}}}}}}'})
    req = urllib.request.Request("https://api.github.com/graphql", data=q.encode(),
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-build"})
    with urllib.request.urlopen(req, timeout=60) as r:
        contrib = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    models = get(f"https://huggingface.co/api/models?author={HF_USER}&limit=1000&expand[]=downloadsAllTime")
    hf_dl = sum(m.get("downloadsAllTime", 0) for m in models)

    save("assets/banner.svg", banner())
    save("assets/terminal.svg", terminal())
    for num, title in [("01", "ACTIVE PROJECTS"), ("02", "CYBERWARE"), ("03", "TELEMETRY")]:
        save(f"assets/section-{num}.svg", section(num, title))
    for i, (name, repo, tag, desc, lang) in enumerate(PROJECTS, 1):
        save(f"assets/card-{i:02d}.svg", card(i, name, tag, desc, lang, stars.get(repo, 0)))

    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    total = sum(n for _, n in top) or 1
    x, bar, legend = 30, "", ""
    for k, (lang, n) in enumerate(top):
        bw = 560 * n / total
        bar += f'<rect x="{x:.1f}" y="200" width="{bw:.1f}" height="10" fill="{LANG_COLORS.get(lang, DIM)}"/>'
        legend += (f'<circle cx="{36 + k * 112}" cy="234" r="5" fill="{LANG_COLORS.get(lang, DIM)}"/>'
                   f'<text x="{46 + k * 112}" y="239" {MONO} font-size="13" fill="{DIM}">{escape(lang[:10])}</text>')
        x += bw
    save("assets/stats-github.svg", stat_panel(
        "DATA FORTRESS // GITHUB",
        [("PUBLIC REPOSITORIES", str(len(own)), Y)],
        extra=f'<text x="330" y="104" {MONO} font-size="44" font-weight="700" fill="{C}">{contrib}</text>'
              f'<text x="330" y="128" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">CONTRIBUTIONS / 1Y</text>'
              f'<text x="30" y="186" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">TOP LANGUAGES</text>'
              + bar + legend))
    save("assets/stats-hf.svg", stat_panel(
        "UPLINK // HUGGING FACE",
        [("TOTAL DOWNLOADS", f"{hf_dl:,}", Y), ("MODELS PUBLISHED", str(len(models)), C)]))
    save("assets/footer.svg", footer())
    print(len(own), contrib, hf_dl, len(models), top)


if __name__ == "__main__":
    main()
