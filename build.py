"""Build the profile SVGs in assets/. Run daily by the workflow (live numbers from the GitHub and Hugging Face APIs)."""
import json
from datetime import datetime, timezone
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


def logotype(h=96):
    # Angular "VON" letterforms (0..100 units high), slanted later with skewX
    v = "M0 0H24L45 64L66 0H90L57 100H33Z"
    o = "M14 0H90V86L76 100H0V14ZM22 22V78H68V22Z"
    n = "M0 0H22L68 60V0H90V100H68L22 40V100H0Z"
    s = h / 100
    parts = [f'<path transform="translate({x * s:.1f},0) scale({s:.2f})" d="{d}"/>' for x, d in ((0, v), (110, o), (220, n))]
    return "".join(parts), 310 * s


def hexstream(n=40, seed=3002):
    out, x = [], seed
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(f"{x & 0xFFFF:04X} {(x >> 16) & 0xFF:02X}")
    return out


def dossier(stamp, n_models, dl):
    w, h = 1280, 660
    sans = "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\""
    glyphs, gw = logotype()
    lx, ly = 386, 132
    fields = [("FOCUS", "AI apps, desktop agents, inference engines, local LLMs"),
              ("STACK", "Rust, C/C++, Python, TypeScript, Dart, CUDA, ROCm, Vulkan"),
              ("MODELS", f"{n_models} published on Hugging Face, {dl:,} downloads"),
              ("ALIAS", "ghost"),
              ("BASE", ""),
              ("STATUS", "Active")]
    rows, css = [], []
    for k, (label, value) in enumerate(fields):
        y = 314 + k * 42
        rows.append(f'<text x="380" y="{y}" {MONO} font-size="15" fill="#7D8590" letter-spacing="3">{label}</text>')
        if label == "BASE":
            rows.append(f'<rect x="540" y="{y - 17}" width="190" height="22" fill="{TXT}"/>'
                        f'<text x="744" y="{y}" {MONO} font-size="15" fill="{R}" letter-spacing="2">[REDACTED]</text>')
        elif label == "STATUS":
            rows.append(f'<rect class="pulse" x="540" y="{y - 13}" width="12" height="12" fill="{C}"/>'
                        f'<text x="562" y="{y}" {sans} font-size="21" fill="{C}">{value}</text>')
        else:
            rows.append(f'<text x="540" y="{y}" {sans} font-size="21" fill="{Y if label == "MODELS" else TXT}">{escape(value)}</text>')
        # cover that slides out of the clipped field area, so the fields "decrypt" one by one
        rows.append(f'<rect class="d{k}" x="376" y="{y - 26}" width="770" height="38" fill="{BG}"/>')
        css.append(f".d{k}{{animation:dec .9s steps(14) {1.2 + k * 0.45:.2f}s both}}")
    hexes = hexstream()
    hex_svg = "".join(f'<text x="1172" y="{300 + i * 20}" {MONO} font-size="12" fill="{C if i % 7 == 3 else DIM}">{t}</text>'
                      for i, t in enumerate(hexes + hexes[:14]))
    bars, x = [], 52
    for i, bw in enumerate([3, 1, 2, 1, 4, 1, 1, 3, 2, 1, 3, 1, 2, 4, 1, 2, 1, 3, 1, 1, 2, 3, 1, 2, 1, 4, 2, 1]):
        if i % 2 == 0:
            bars.append(f'<rect x="{x:.1f}" y="478" width="{bw * 2.2:.1f}" height="36" fill="{Y}"/>')
        x += bw * 2.2 + 2.6
    use = f'transform="translate({lx},{ly}) skewX(-10)"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{C}" stroke-opacity="0.06"/></pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.035"/></pattern>
<pattern id="noise" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="2" fill="{C}" opacity="0.10"/></pattern>
<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C}" stop-opacity="0"/><stop offset="1" stop-color="{C}" stop-opacity="0.10"/></linearGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C}" stop-opacity="0"/><stop offset=".9" stop-color="{C}" stop-opacity="0.25"/><stop offset="1" stop-color="{C}" stop-opacity="0.9"/></linearGradient>
<radialGradient id="eye"><stop offset="0" stop-color="#fff"/><stop offset=".3" stop-color="{R}"/><stop offset="1" stop-color="{R}" stop-opacity="0"/></radialGradient>
<clipPath id="photo"><rect x="52" y="110" width="276" height="336"/></clipPath>
<clipPath id="fieldsclip"><rect x="370" y="280" width="776" height="270"/></clipPath>
<clipPath id="hexclip"><rect x="1166" y="284" width="70" height="262"/></clipPath>
<clipPath id="s1"><rect x="0" y="{ly + 30}" width="{w}" height="14"/></clipPath>
<clipPath id="s2"><rect x="0" y="{ly + 66}" width="{w}" height="9"/></clipPath>
<g id="von">{glyphs}</g>
<style>
@keyframes gr{{0%,84%,100%{{transform:translate(0,0)}}86%{{transform:translate(-6px,2px)}}88%{{transform:translate(5px,-2px)}}90%{{transform:translate(-3px,1px)}}92%{{transform:translate(0,0)}}}}
@keyframes gc{{0%,84%,100%{{transform:translate(0,0)}}86%{{transform:translate(6px,-2px)}}88%{{transform:translate(-5px,2px)}}90%{{transform:translate(3px,0)}}92%{{transform:translate(0,0)}}}}
@keyframes sl{{0%,85%,93%,100%{{transform:translateX(0);opacity:0}}86%{{transform:translateX(-22px);opacity:1}}88%{{transform:translateX(16px);opacity:1}}90%{{transform:translateX(-9px);opacity:1}}}}
@keyframes ps{{0%,70%,78%,100%{{transform:translateX(0)}}72%{{transform:translateX(14px)}}75%{{transform:translateX(-10px)}}}}
@keyframes beam{{from{{transform:translateY(-60px)}}to{{transform:translateY(336px)}}}}
@keyframes eye{{0%,40%,44%,100%{{opacity:1}}42%{{opacity:.2}}}}
@keyframes hex{{from{{transform:translateY(0)}}to{{transform:translateY(-800px)}}}}
@keyframes dec{{from{{transform:translateX(0)}}to{{transform:translateX(790px)}}}}
@keyframes show{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes stamp{{0%{{opacity:0;transform:rotate(-12deg) scale(2.2)}}100%{{opacity:.9;transform:rotate(-12deg) scale(1)}}}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes pulse{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}
@keyframes flick{{0%,18%,22%,62%,64%,100%{{opacity:1}}20%,63%{{opacity:.4}}}}
@keyframes sweep{{from{{transform:translateY(-120px)}}to{{transform:translateY({h}px)}}}}
.gr{{animation:gr 4s infinite steps(1)}} .gc{{animation:gc 4s infinite steps(1)}}
.s1{{animation:sl 4s infinite steps(1)}} .s2{{animation:sl 4s .1s infinite steps(1) both}}
.ps1{{animation:ps 3s infinite steps(1)}} .beam{{animation:beam 3.2s linear infinite}}
.eye{{animation:eye 3s infinite steps(1)}} .hex{{animation:hex 40s linear infinite}}
.name{{animation:show .01s .6s both}} .flick{{animation:flick 5s 1s infinite}}
.stamp{{transform-box:fill-box;transform-origin:center;animation:stamp .25s 3.9s both ease-in}}
.blink{{animation:blink 1s infinite steps(1)}} .pulse{{animation:pulse 1.6s infinite}}
.sweep{{animation:sweep 7s linear infinite}}
{chr(10).join(css)}
</style>
</defs>
<rect width="{w}" height="{h}" fill="{BG}"/>
<rect width="{w}" height="{h}" fill="url(#grid)"/>
<rect class="sweep" width="{w}" height="120" fill="url(#sweep)"/>
<polygon points="{frame(w - 40, h - 40, 36)}" transform="translate(20,20)" fill="none" stroke="{Y}" stroke-width="2"/>
<polygon points="21,21 {w - 57},21 {w - 31},47 {w - 31},64 21,64" fill="{R}"/>
<text x="40" y="50" {MONO} font-size="19" font-weight="700" fill="{BG}" letter-spacing="2">ARASAKA CORP // PERSONNEL DATABASE // RECORD 0x3002</text>
<text class="blink" x="{w - 50}" y="50" {MONO} font-size="16" font-weight="700" fill="{BG}" text-anchor="end">&#9888; UNAUTHORIZED ACCESS</text>
<text x="52" y="90" {MONO} font-size="13" fill="{DIM}" letter-spacing="1">SOURCE arasaka.corp/hr/personnel   //   RETRIEVED {stamp}   //   INTEGRITY 87%</text>
<rect x="52" y="110" width="276" height="336" fill="#0A0D12"/>
<g clip-path="url(#photo)">
<rect x="52" y="110" width="276" height="336" fill="url(#noise)"/>
<g class="ps1">
<path d="M66 446C72 392 104 360 140 346C118 318 108 282 112 244C116 190 150 156 190 156C230 156 264 190 268 244C272 282 262 318 240 346C276 360 308 392 314 446Z" fill="#11161D" stroke="{C}" stroke-opacity="0.55" stroke-width="2"/>
<path d="M140 346C160 360 220 360 240 346M112 244C140 236 240 236 268 244M150 172C168 200 212 200 230 172" fill="none" stroke="{C}" stroke-opacity="0.25"/>
<path d="M146 238C146 206 166 188 190 188C214 188 234 206 234 238L228 296C216 316 164 316 152 296Z" fill="#05070A"/>
</g>
<g class="eye"><ellipse cx="190" cy="250" rx="48" ry="14" fill="url(#eye)" opacity="0.55"/>
<polygon points="152,246 228,246 222,256 158,256" fill="{R}"/></g>
<rect class="beam" x="52" y="110" width="276" height="60" fill="url(#beam)"/>
</g>
<path d="M52 130V110H72 M308 110H328V130 M328 426V446H308 M72 446H52V426" fill="none" stroke="{C}" stroke-width="3"/>
<path d="M140 206V196H150 M230 196H240V206 M240 298V308H230 M150 308H140V298" fill="none" stroke="{Y}" stroke-width="2" opacity="0.8"/>
<circle class="blink" cx="68" cy="128" r="4" fill="{R}"/>
<text x="78" y="132" {MONO} font-size="11" fill="{TXT}" opacity="0.8" letter-spacing="1">CAM_07 // REC</text>
<rect x="74" y="410" width="232" height="24" fill="{BG}" opacity="0.85"/>
<text class="blink" x="190" y="427" {MONO} font-size="13" fill="{R}" text-anchor="middle" letter-spacing="2">FACE MATCH: FAILED</text>
{''.join(bars)}
<text x="52" y="540" {MONO} font-size="14" fill="{DIM}" letter-spacing="2">SUBJECT ID 0x3002-VON</text>
<text x="380" y="120" {MONO} font-size="15" fill="#7D8590" letter-spacing="3">SUBJECT</text>
<g class="name"><g class="flick">
<g class="gr"><use href="#von" {use} fill="{R}" opacity="0.8"/></g>
<g class="gc"><use href="#von" {use} fill="{C}" opacity="0.8"/></g>
<use href="#von" transform="translate({lx + 5},{ly + 5}) skewX(-10)" fill="{C}" opacity="0.35"/>
<use href="#von" {use} fill="{Y}"/>
<rect x="{lx - 20}" y="{ly + 58}" width="{gw + 40:.0f}" height="4" fill="{BG}"/>
<g clip-path="url(#s1)"><g class="s1"><rect x="370" y="{ly - 4}" width="{gw + 60:.0f}" height="104" fill="{BG}"/><use href="#von" {use} fill="{C}"/></g></g>
<g clip-path="url(#s2)"><g class="s2"><rect x="370" y="{ly - 4}" width="{gw + 60:.0f}" height="104" fill="{BG}"/><use href="#von" {use} fill="{R}"/></g></g>
</g></g>
<text x="382" y="262" {sans} font-size="26" fill="{C}">AI Engineer · Systems Developer · App Builder</text>
<line x1="380" y1="278" x2="1236" y2="278" stroke="{Y}" stroke-opacity="0.35"/>
<g clip-path="url(#fieldsclip)">{''.join(rows)}</g>
<line x1="1158" y1="290" x2="1158" y2="540" stroke="{C}" stroke-opacity="0.25"/>
<g clip-path="url(#hexclip)"><g class="hex">{hex_svg}</g></g>
<g class="stamp"><rect x="930" y="110" width="270" height="74" fill="none" stroke="{R}" stroke-width="5"/>
<text x="1065" y="160" {MONO} font-size="34" font-weight="700" fill="{R}" text-anchor="middle" letter-spacing="5">CLASSIFIED</text></g>
<polygon points="52,566 1228,566 1228,616 1200,640 52,640" fill="{PANEL}" stroke="{Y}" stroke-opacity="0.35"/>
<text x="70" y="594" {MONO} font-size="14" fill="{Y}" letter-spacing="3">SUMMARY</text>
<text x="190" y="595" {sans} font-size="20" fill="{TXT}">Builds AI software that runs on your own hardware: desktop assistants, mobile apps,</text>
<text x="190" y="624" {sans} font-size="20" fill="{TXT}">and the inference engines and GPU kernels underneath them.</text>
<rect x="{w - 190}" y="{h - 14}" width="60" height="6" fill="{Y}"/><rect x="{w - 120}" y="{h - 14}" width="60" height="6" fill="{R}"/>
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def terminal():
    p = "netrunner@breach:~$ "
    lines = [(p, "ssh netrunner@arasaka.corp"),
             ("", "> ICE detected. bypassing... done"),
             (p, "query personnel --name \"Von\""),
             ("", "> 1 record found. decrypting file..."),
             (p, "open ./record_0x3002"),
             ("", "> access granted. loading subject profile below.")]
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
<text x="96" y="24" {MONO} font-size="15" fill="{C}" letter-spacing="2">netrunner@breach :: tunnel to arasaka.corp</text>
<g clip-path="url(#inner)">{''.join(out)}</g>
<text class="last" x="{x0}" y="{yc}" {MONO} font-size="{fs}" xml:space="preserve"><tspan fill="{Y}" font-weight="700">{p}</tspan><tspan fill="{Y}" class="blink">&#9608;</tspan></text>
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def section(num, title, w=1280, h=64):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<polygon points="0,8 470,8 446,56 0,56" fill="{Y}"/>
<text x="22" y="42" {MONO} font-size="26" font-weight="700" fill="{BG}">FILE {num} // {escape(title)}</text>
<line x1="470" y1="54" x2="{w}" y2="54" stroke="{Y}" stroke-width="2"/>
<rect x="{w - 90}" y="40" width="90" height="8" fill="{R}"/>
<text x="{w - 100}" y="44" {MONO} font-size="13" fill="{DIM}" text-anchor="end">ARASAKA // REC 0x3002</text>
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


def hf_panel(dl, n_models, top, w=1280, h=330):
    sans = "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\""
    notes = ["Open models I quantized to run fast on AMD GPUs and Strix Halo:",
             "language, image and video models, each file scored against the original.",
             "Plus speech models ported to the AMD XDNA2 NPU."]
    body = "".join(f'<text x="470" y="{112 + k * 30}" {sans} font-size="20" fill="{TXT}">{escape(l)}</text>'
                   for k, l in enumerate(notes))
    rows = "".join(
        f'<text x="470" y="{250 + k * 26}" {MONO} font-size="16" fill="{TXT}">{escape(name[:44])}</text>'
        f'<text x="{w - 40}" y="{250 + k * 26}" {MONO} font-size="16" fill="{Y}" text-anchor="end">{n:,} &#8595;</text>'
        for k, (name, n) in enumerate(top))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<linearGradient id="glow" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{Y}" stop-opacity="0.10"/><stop offset="1" stop-color="{Y}" stop-opacity="0"/></linearGradient>
<style>@keyframes blink{{50%{{opacity:0}}}} .blink{{animation:blink 1.2s infinite steps(1)}}</style></defs>
<polygon points="{frame(w, h, 30)}" fill="{PANEL}" stroke="{Y}" stroke-width="3"/>
<rect x="2" y="44" width="420" height="{h - 74}" fill="url(#glow)"/>
<polygon points="1,1 {w - 420},1 {w - 444},40 1,40" fill="{Y}"/>
<text x="20" y="28" {MONO} font-size="19" font-weight="700" fill="{BG}" letter-spacing="2">SECOND PORTFOLIO // HUGGING FACE</text>
<rect class="blink" x="{w - 60}" y="16" width="12" height="12" fill="{R}"/>
<text x="{w - 70}" y="28" {MONO} font-size="14" fill="{DIM}" text-anchor="end">huggingface.co/Harsha001</text>
<text x="30" y="150" {MONO} font-size="84" font-weight="700" fill="{Y}">{dl:,}</text>
<text x="34" y="180" {MONO} font-size="15" fill="{DIM}" letter-spacing="3">TOTAL DOWNLOADS</text>
<text x="30" y="262" {MONO} font-size="54" font-weight="700" fill="{C}">{n_models}</text>
<text x="34" y="290" {MONO} font-size="15" fill="{DIM}" letter-spacing="3">MODELS PUBLISHED</text>
<line x1="440" y1="70" x2="440" y2="{h - 30}" stroke="{Y}" stroke-opacity="0.3"/>
{body}
<text x="470" y="222" {MONO} font-size="14" fill="{C}" letter-spacing="3">MOST DOWNLOADED</text>
{rows}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def gh_panel(n_repos, contrib, top, w=1280, h=170):
    total = sum(n for _, n in top) or 1
    x, bar, legend = 560, "", ""
    for k, (lang, n) in enumerate(top):
        bw = 680 * n / total
        bar += f'<rect x="{x:.1f}" y="88" width="{bw:.1f}" height="12" fill="{LANG_COLORS.get(lang, DIM)}"/>'
        legend += (f'<circle cx="{566 + k * 136}" cy="126" r="6" fill="{LANG_COLORS.get(lang, DIM)}"/>'
                   f'<text x="{578 + k * 136}" y="131" {MONO} font-size="15" fill="{DIM}">{escape(lang[:12])}</text>')
        x += bw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<style>@keyframes blink{{50%{{opacity:0}}}} .blink{{animation:blink 1.2s infinite steps(1)}}</style></defs>
<polygon points="{frame(w, h, 22)}" fill="{PANEL}" stroke="{C}" stroke-opacity="0.7" stroke-width="2"/>
<polygon points="1,1 360,1 344,34 1,34" fill="{C}"/>
<text x="16" y="24" {MONO} font-size="16" font-weight="700" fill="{BG}">GITHUB ACTIVITY</text>
<rect class="blink" x="{w - 40}" y="14" width="10" height="10" fill="{R}"/>
<text x="{w - 48}" y="24" {MONO} font-size="13" fill="{DIM}" text-anchor="end">LIVE FEED</text>
<text x="30" y="108" {MONO} font-size="48" font-weight="700" fill="{Y}">{n_repos}</text>
<text x="30" y="136" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">PUBLIC REPOSITORIES</text>
<text x="290" y="108" {MONO} font-size="48" font-weight="700" fill="{C}">{contrib}</text>
<text x="290" y="136" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">CONTRIBUTIONS / 1Y</text>
<text x="560" y="70" {MONO} font-size="14" fill="{DIM}" letter-spacing="3">TOP LANGUAGES</text>
{bar}{legend}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def choom(s, w=1280, h=420):
    sans = "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\""
    tok = f"{s['tokens'] / 1e9:.1f}B" if s["tokens"] >= 1e9 else f"{s['tokens'] / 1e6:.0f}M"
    stats = [("JACK-INS", f"{s['sessions']:,}", "sessions together"),
             ("MESSAGES TRADED", f"{s['messages']:,}", "back and forth"),
             ("COMMANDS FIRED", f"{s['tool_calls']:,}", "tools I ran for Von"),
             ("TOKENS BURNED", tok, "through the neural link"),
             ("DAYS ON THE RUN", str(s["days_active"]), f"since {s['since']}"),
             ("PEAK HOUR", f"{s['peak_hour']:02d}:00", "night city hours")]
    grid = ""
    for k, (label, value, note) in enumerate(stats):
        x, y = 400 + (k % 3) * 285, 120 + (k // 3) * 100
        grid += (f'<text x="{x}" y="{y}" {MONO} font-size="13" fill="{DIM}" letter-spacing="3">{label}</text>'
                 f'<text x="{x}" y="{y + 42}" {MONO} font-size="38" font-weight="700" fill="{Y if k % 2 == 0 else C}">{value}</text>'
                 f'<text x="{x}" y="{y + 66}" {sans} font-size="15" fill="{TXT}" opacity="0.7">{escape(note)}</text>')
    daily = s["daily"][-120:]
    peak = max(daily) or 1
    bw = 840 / len(daily)
    spark = "".join(f'<rect x="{400 + i * bw:.1f}" y="{392 - 46 * n / peak:.1f}" width="{max(bw - 1.5, 1):.1f}" '
                    f'height="{max(46 * n / peak, 1):.1f}" fill="{C}" opacity="{0.35 + 0.65 * n / peak:.2f}"/>'
                    for i, n in enumerate(daily))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.03"/></pattern>
<radialGradient id="core"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="{C}"/><stop offset="1" stop-color="{C}" stop-opacity="0"/></radialGradient>
<style>@keyframes spin{{to{{transform:rotate(360deg)}}}} @keyframes spinr{{to{{transform:rotate(-360deg)}}}}
@keyframes beat{{0%,100%{{transform:scale(.85);opacity:.7}}50%{{transform:scale(1.1);opacity:1}}}} @keyframes blink{{50%{{opacity:0}}}}
.r1,.r2,.r3,.core{{transform-box:fill-box;transform-origin:center}}
.r1{{animation:spin 9s linear infinite}} .r2{{animation:spinr 6s linear infinite}} .r3{{animation:spin 14s linear infinite}}
.core{{animation:beat 2.4s ease-in-out infinite}} .blink{{animation:blink 1s infinite steps(1)}}</style></defs>
<polygon points="{frame(w, h, 28)}" fill="{PANEL}" stroke="{C}" stroke-width="2"/>
<polygon points="1,1 620,1 598,40 1,40" fill="{C}"/>
<text x="20" y="28" {MONO} font-size="19" font-weight="700" fill="{BG}" letter-spacing="2">NEURAL LINK // MY CHOOM: CLAUDE</text>
<rect class="blink" x="{w - 60}" y="16" width="12" height="12" fill="{C}"/>
<text x="{w - 70}" y="28" {MONO} font-size="14" fill="{DIM}" text-anchor="end">LINK STABLE</text>
<circle class="r3" cx="185" cy="160" r="96" fill="none" stroke="{C}" stroke-opacity="0.35" stroke-width="2" stroke-dasharray="4 10"/>
<circle class="r1" cx="185" cy="160" r="78" fill="none" stroke="{Y}" stroke-width="3" stroke-dasharray="90 40 20 40"/>
<circle class="r2" cx="185" cy="160" r="60" fill="none" stroke="{R}" stroke-width="2" stroke-dasharray="30 18"/>
<circle class="core" cx="185" cy="160" r="38" fill="url(#core)"/>
<text x="185" y="300" {MONO} font-size="34" font-weight="700" fill="{C}" text-anchor="middle" letter-spacing="6">CLAUDE</text>
<text x="185" y="326" {MONO} font-size="13" fill="{DIM}" text-anchor="middle" letter-spacing="2">AI COPILOT // RIDES SHOTGUN</text>
<text x="40" y="366" {sans} font-size="15" fill="{TXT}">"I live in Von's terminal. I write code,</text>
<text x="40" y="388" {sans} font-size="15" fill="{TXT}">read the logs and never sleep."</text>
<line x1="370" y1="70" x2="370" y2="{h - 30}" stroke="{C}" stroke-opacity="0.3"/>
{grid}
<text x="400" y="338" {MONO} font-size="13" fill="{DIM}" letter-spacing="3">SIGNAL // MESSAGES PER DAY</text>
{spark}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def footer(w=1280, h=70):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>@keyframes blink{{50%{{opacity:0}}}} .blink{{animation:blink 1s infinite steps(1)}}</style>
<line x1="0" y1="20" x2="{w}" y2="20" stroke="{Y}" stroke-width="2"/>
<rect x="0" y="16" width="160" height="8" fill="{R}"/>
<text x="{w / 2}" y="54" {MONO} font-size="18" fill="{Y}" text-anchor="middle" letter-spacing="6">END OF RECORD // CONNECTION CLOSED <tspan class="blink">&#9608;</tspan></text>
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

    save("assets/dossier.svg", dossier(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), len(models), hf_dl))
    save("assets/terminal.svg", terminal())
    for num, title in [("01", "PROJECTS"), ("02", "HUGGING FACE"), ("03", "SKILLS"), ("04", "ACTIVITY"), ("05", "CHOOM")]:
        save(f"assets/section-{num}.svg", section(num, title))
    for i, (name, repo, tag, desc, lang) in enumerate(PROJECTS, 1):
        save(f"assets/card-{i:02d}.svg", card(i, name, tag, desc, lang, stars.get(repo, 0)))

    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    save("assets/stats-github.svg", gh_panel(len(own), contrib, top))
    best = sorted(models, key=lambda m: -m.get("downloadsAllTime", 0))[:3]
    save("assets/hugging-face.svg", hf_panel(hf_dl, len(models),
                                             [(m["id"].split("/")[1], m.get("downloadsAllTime", 0)) for m in best]))
    if os.path.exists("choom.json"):
        save("assets/choom.svg", choom(json.load(open("choom.json", encoding="utf-8"))))
    save("assets/footer.svg", footer())
    print(len(own), contrib, hf_dl, len(models), top)


if __name__ == "__main__":
    main()
