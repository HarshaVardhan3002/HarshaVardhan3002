"""Build the profile SVGs in assets/. Run daily by the workflow (live numbers from the GitHub and Hugging Face APIs).
Look: Cyberpunk 2077 HUD. Thin lines, one red accent, fonts embedded per image (subset to the letters it uses)."""
import base64
import html
import io
import json
import os
import random
import re
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

GH_USER = "HarshaVardhan3002"
HF_USER = "Harsha001"
W = 1280
TOP_FLOOR = 100

BG, PANEL, LINE, LINE2 = "#06080C", "#0A0E14", "#1B212B", "#2A323E"
TXT, SOFT, DIM = "#E4E9F0", "#AEB7C4", "#6E7787"
RED, CYAN, YEL, PINK = "#FF3C4E", "#3EE8F0", "#F3E600", "#FF2D8A"

# family name used in the SVG -> font file (OFL fonts, see fonts/)
FONTS = {"RajB": "fonts/Rajdhani-Bold.ttf", "RajM": "fonts/Rajdhani-Medium.ttf",
         "Chakra": "fonts/ChakraPetch-SemiBold.ttf", "Mono": "fonts/JetBrainsMono-Regular.ttf"}
DISP = "font-family=\"RajB,'Rajdhani',sans-serif\" font-weight=\"700\""
BODY = "font-family=\"RajM,'Rajdhani',sans-serif\" font-weight=\"500\""
NUM = "font-family=\"Chakra,'Chakra Petch',sans-serif\" font-weight=\"600\""
MONO = "font-family=\"Mono,'JetBrains Mono',Consolas,monospace\""
FAMILY = {DISP: "RajB", BODY: "RajM", NUM: "Chakra", MONO: "Mono"}

# repos that are mostly upstream code, left out of the language stats
UPSTREAM_FORKS = {"ROCmFPX"}
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Shell", "PowerShell", "Batchfile", "Makefile", "CMake", "Dockerfile"}
LANG_COLORS = {"Svelte": "#FF3E00", "Kotlin": "#A97BFF", "Cuda": "#5A8F5A", "GLSL": "#5686A5", "Metal": "#8F14E9",
               "Objective-C": "#438EFF", "Swift": "#F05138", "Go": "#00ADD8", "Java": "#B07219", "Rust": "#DEA584",
               "C": "#A8B9CC", "C++": "#F34B7D", "Python": "#3572A5", "TypeScript": "#3178C6",
               "JavaScript": "#F1E05A", "Dart": "#00B4AB"}

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

SKILLS = [("LANGUAGES", ["Rust", "C", "C++", "Python", "TypeScript", "JavaScript", "Dart", "Kotlin"]),
          ("AI / GPU", ["PyTorch", "llama.cpp / GGML", "CUDA", "ROCm / HIP", "Vulkan", "ONNX", "AMD XDNA2 NPU"]),
          ("APPS", ["Tauri", "Svelte", "React", "Flutter", "Node.js"]),
          ("INFRA", ["Linux", "Docker", "Git", "GitHub Actions", "Hugging Face Hub"])]

# README sections are floors of the tower; the page climbs as you scroll
SECTIONS = [("01", "PROJECTS", "FL.012 // R&D LABS"), ("02", "HUGGING FACE", "FL.047 // MODEL VAULT"),
            ("03", "SKILLS", "FL.063 // CYBERWARE"), ("04", "ACTIVITY", "FL.088 // NETWATCH"),
            ("05", "CHOOM", "FL.099 // NEURAL LINK")]

_fonts = {}


def font(fam):
    if fam not in _fonts:
        _fonts[fam] = TTFont(FONTS[fam])
    return _fonts[fam]


def width(text, style, size, ls=0):
    f = font(FAMILY[style])
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    adv = sum(hmtx[cmap.get(ord(ch), ".notdef")][0] for ch in text)
    return adv * size / upm + ls * len(text)


def wrap(text, style, size, maxw):
    lines, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and width(nxt, style, size) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur]


def t(x, y, s, style, size, fill, ls=0, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    sp = f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" {style} font-size="{size}" fill="{fill}"{sp}{a}{extra}>{escape(s)}</text>'


def get(url, token=None):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-build"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def embed_fonts(svg):
    # Subset each used font to the characters in this image and inline it, so it renders the same everywhere
    chars = "".join(html.unescape(m) for m in re.findall(r">([^<>]+)<", svg))
    faces = []
    for fam, path in FONTS.items():
        if f'"{fam},' not in svg:
            continue
        f = TTFont(path)
        o = subset.Options()
        o.flavor, o.layout_features, o.hinting = "woff", ["kern"], False
        s = subset.Subsetter(o)
        s.populate(text=chars + " ")
        s.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff"
        f.save(buf)
        faces.append(f"@font-face{{font-family:{fam};src:url(data:font/woff;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff')}}")
    return svg.replace("<defs>", f"<defs><style>{''.join(faces)}</style>", 1)


def save(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(embed_fonts(svg))


def doc(w, h, body, css="", defs=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
<pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="#fff" opacity="0.018"/></pattern>
{defs}
<style>
@keyframes blink{{50%{{opacity:0}}}} @keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
.blink{{animation:blink 1.1s infinite steps(1)}} .pulse{{animation:pulse 2s infinite ease-in-out}}
{css}
</style>
</defs>
{body}
<rect width="{w}" height="{h}" fill="url(#scan)"/>
</svg>"""


def frame(w, h, cut=16, x=0, y=0):
    # 1px outline, top-right and bottom-left corners cut
    return (f'<path d="M{x + .5} {y + .5}H{x + w - cut}L{x + w - .5} {y + cut}V{y + h - .5}H{x + cut}'
            f'L{x + .5} {y + h - cut}Z" fill="{PANEL}" stroke="{LINE2}"/>')


def ticks(x, y, w, h):
    # red corner ticks, top-left and bottom-right
    return (f'<path d="M{x} {y + 18}V{y}H{x + 18}M{x + w} {y + h - 18}V{y + h}H{x + w - 18}" fill="none" stroke="{RED}" stroke-width="2"/>')


def ruler(x, y, n=24):
    return "".join(f'<rect x="{x + i * 10}" y="{y - (8 if i % 5 == 0 else 4)}" width="1" height="{8 if i % 5 == 0 else 4}" fill="{LINE2}"/>'
                   for i in range(n))


def header(w, left, right, dot=RED):
    return (f'<rect x="24" y="22" width="7" height="7" fill="{RED}"/>'
            + t(40, 30, left, MONO, 14, RED, 2)
            + f'<rect class="blink" x="{w - 36}" y="22" width="7" height="7" fill="{dot}"/>'
            + t(w - 46, 30, right, MONO, 14, DIM, 2, "end")
            + f'<line x1="24" y1="44" x2="{w - 24}" y2="44" stroke="{LINE}"/>')


def panel(w, h, left, right, body, css="", defs="", dot=RED):
    return doc(w, h, frame(w, h) + ticks(1, 1, w - 2, h - 2) + header(w, left, right, dot) + ruler(24, h - 14) + body, css, defs)


def tower(x0, y0, vw, vh, floor):
    # Viewport: a rainy night skyline with a tall corporate tower and the climber's floor marker
    rnd = random.Random(3002)
    cx, base, crown = x0 + vw * 0.52, y0 + vh, y0 + 92
    out = [f'<rect x="{x0}" y="{y0}" width="{vw}" height="{vh}" fill="url(#sky)"/>',
           f'<ellipse cx="{cx}" cy="{crown + 30}" rx="190" ry="150" fill="url(#pinkglow)"/>']
    for layer, (col, hmin, hmax, win) in enumerate([("#11152A", 140, 320, 0.3), ("#080B13", 50, 170, 0.6)]):
        x = x0 - 10
        while x < x0 + vw:
            bw = rnd.randint(26, 58)
            bh = rnd.randint(hmin, hmax)
            if abs(x + bw / 2 - cx) > 70 or layer == 0:
                out.append(f'<rect x="{x}" y="{base - bh}" width="{bw}" height="{bh}" fill="{col}"/>')
                out.append(f'<line x1="{x}" y1="{base - bh + .5}" x2="{x + bw}" y2="{base - bh + .5}" stroke="{PINK if layer == 0 else CYAN}" stroke-opacity="0.18"/>')
                for wy in range(base - bh + 8, base - 6, 9):
                    for wx in range(x + 5, x + bw - 5, 7):
                        if rnd.random() < 0.07 * win:
                            c = rnd.choice([PINK, CYAN, YEL, "#8FA3C0"])
                            cls = ' class="pulse"' if rnd.random() < 0.15 else ""
                            out.append(f'<rect{cls} x="{wx}" y="{wy}" width="2" height="3" fill="{c}" opacity="{rnd.uniform(.35, .85):.2f}"/>')
            x += bw + rnd.randint(2, 8)
    # the tower: slim shaft, wider head block, antenna
    sw, hw = 44, 64
    out.append(f'<path d="M{cx - sw} {base}V{crown + 70}L{cx - hw} {crown + 52}V{crown}H{cx + hw}V{crown + 52}L{cx + sw} {crown + 70}V{base}Z" '
               f'fill="#0B0F18" stroke="#3A2030"/>')
    for fy in range(int(crown + 80), base, 10):
        out.append(f'<line x1="{cx - sw + 4}" y1="{fy}" x2="{cx + sw - 4}" y2="{fy}" stroke="#151B27"/>')
    for fy in range(int(crown + 84), base - 4, 10):
        for fx in range(int(cx - sw + 6), int(cx + sw - 6), 6):
            if rnd.random() < 0.05:
                out.append(f'<rect x="{fx}" y="{fy}" width="3" height="4" fill="{rnd.choice([SOFT, CYAN, PINK])}" opacity="{rnd.uniform(.2, .55):.2f}"/>')
    # neon rim light: pink on the left edges, cyan on the right
    out.append(f'<path d="M{cx - sw + .5} {base}V{crown + 70}L{cx - hw + .5} {crown + 52}V{crown + .5}" fill="none" stroke="{PINK}" stroke-opacity="0.55"/>')
    out.append(f'<path d="M{cx + sw - .5} {base}V{crown + 70}L{cx + hw - .5} {crown + 52}V{crown + .5}" fill="none" stroke="{CYAN}" stroke-opacity="0.35"/>')
    out.append(f'<rect x="{cx - 1}" y="{crown + 60}" width="2" height="{base - crown - 60}" fill="{RED}" opacity="0.55"/>')
    out.append(f'<rect x="{cx - hw + 8}" y="{crown + 14}" width="{2 * hw - 16}" height="3" fill="{RED}" opacity="0.8"/>')
    out.append(f'<rect x="{cx - hw + 8}" y="{crown + 34}" width="{2 * hw - 16}" height="1" fill="{RED}" opacity="0.4"/>')
    out.append(f'<line x1="{cx}" y1="{crown}" x2="{cx}" y2="{crown - 46}" stroke="#3A2030" stroke-width="2"/>')
    out.append(f'<circle class="blink" cx="{cx}" cy="{crown - 48}" r="3" fill="{RED}"/>')
    # floor scale and marker
    top, bot = crown + 6, base - 20
    sx = cx + hw + 22
    out.append(f'<line x1="{sx}" y1="{top}" x2="{sx}" y2="{bot}" stroke="{LINE2}"/>')
    for f in range(0, TOP_FLOOR + 1, 25):
        fy = bot - (bot - top) * f / TOP_FLOOR
        out.append(f'<line x1="{sx}" y1="{fy:.1f}" x2="{sx + 8}" y2="{fy:.1f}" stroke="{LINE2}"/>')
        out.append(t(sx + 14, fy + 4, f"FL {f:03d}", MONO, 12, DIM))
    out.append(t(cx + 12, crown - 30, "TARGET: TOP FLOOR", MONO, 12, RED, 2))
    my = bot - (bot - top) * min(floor, TOP_FLOOR) / TOP_FLOOR
    out.append(f'<line class="pulse" x1="{cx - sw - 30}" y1="{my:.1f}" x2="{sx}" y2="{my:.1f}" stroke="{CYAN}" stroke-dasharray="3 3"/>')
    out.append(f'<path d="M{sx - 2} {my:.1f}l10 -6v12z" fill="{CYAN}"/>')
    out.append(t(cx - sw - 36, my - 8, f"VON  FL {floor:03d}", MONO, 13, CYAN, 1, "end"))
    out.append(f'<rect x="{x0}" y="{y0}" width="{vw}" height="{vh}" fill="url(#rain)" class="rain"/>')
    return "".join(out)


def dossier(stamp, n_models, dl, floor):
    w, h = W, 700
    vx, vy, vw, vh = 812, 96, 420, 556
    name_w = width("VON", DISP, 176, 8)
    rows, css = [], []
    fields = [("FOCUS", "AI apps, desktop agents, inference engines, local LLMs"),
              ("STACK", "Rust, C/C++, Python, TypeScript, Dart, CUDA, ROCm, Vulkan"),
              ("MODELS", f"{n_models} on Hugging Face  /  {dl:,} downloads"),
              ("BASE", ""),
              ("STATUS", "Online, shipping")]
    for k, (label, value) in enumerate(fields):
        y = 452 + k * 42
        r = t(56, y, label, MONO, 14, DIM, 2)
        if label == "BASE":
            r += f'<rect x="196" y="{y - 15}" width="170" height="18" fill="{LINE2}"/>' + t(380, y, "REDACTED", MONO, 13, RED, 2)
        elif label == "STATUS":
            r += f'<circle class="pulse" cx="202" cy="{y - 6}" r="5" fill="{CYAN}"/>' + t(216, y, value, BODY, 23, CYAN)
        else:
            r += t(196, y, value, BODY, 23, YEL if label == "MODELS" else TXT)
        r += f'<line x1="56" y1="{y + 15}" x2="760" y2="{y + 15}" stroke="{LINE}" stroke-dasharray="2 4"/>'
        rows.append(f'<g class="r{k}">{r}</g>')
        css.append(f".r{k}{{animation:rin .5s {0.9 + k * 0.18:.2f}s both cubic-bezier(.2,.8,.2,1)}}")
    summary = wrap("Builds AI software that runs on your own hardware: desktop assistants, mobile apps, "
                   "and the inference engines and GPU kernels underneath them.", BODY, 23, 700)
    name = lambda dx, fill, op: f'<text x="{50 + dx}" y="282" {DISP} font-size="176" fill="{fill}" letter-spacing="8" opacity="{op}">VON</text>'
    body = (
        f'<rect width="{w}" height="{h}" fill="{BG}"/>'
        f'<rect width="{w}" height="{h}" fill="url(#grid)"/>'
        + frame(w - 2, h - 2, 22, 1, 1).replace(f'fill="{PANEL}"', 'fill="none"') + ticks(1, 1, w - 2, h - 2)
        + f'<rect x="24" y="30" width="7" height="7" fill="{RED}"/>' + t(40, 38, "ARASAKA CORP. // INTERNAL NETWORK // PERSONNEL FILE 0x3002", MONO, 14, RED, 2)
        + f'<rect class="blink" x="{w - 36}" y="30" width="7" height="7" fill="{RED}"/>' + t(w - 46, 38, "UNAUTHORIZED ACCESS", MONO, 14, RED, 2, "end")
        + f'<line x1="24" y1="56" x2="{w - 24}" y2="56" stroke="{LINE}"/>'
        + t(56, 112, f"RETRIEVED {stamp}  //  CLEARANCE: NONE", MONO, 14, DIM, 1)
        + f'<g class="nm"><g class="gr">{name(-3, RED, .55)}</g><g class="gc">{name(3, CYAN, .45)}</g>{name(0, TXT, 1)}</g>'
        + f'<rect x="56" y="300" width="{name_w - 8:.0f}" height="2" fill="{RED}"/>'
        + t(56 + name_w + 10, 306, "SUBJECT", MONO, 13, RED, 3)
        + t(56, 342, "AI ENGINEER  /  SYSTEMS DEVELOPER  /  APP BUILDER", NUM, 22, CYAN, 3)
        + "".join(t(56, 384 + i * 28, line, BODY, 23, SOFT) for i, line in enumerate(summary))
        + "".join(rows)
        + f'<g clip-path="url(#vp)">{tower(vx, vy, vw, vh, floor)}</g>'
        + f'<rect x="{vx + .5}" y="{vy + .5}" width="{vw - 1}" height="{vh - 1}" fill="none" stroke="{LINE2}"/>'
        + f'<path d="M{vx} {vy + 20}V{vy}H{vx + 20}M{vx + vw - 20} {vy}H{vx + vw}V{vy + 20}M{vx + vw} {vy + vh - 20}V{vy + vh}H{vx + vw - 20}M{vx + 20} {vy + vh}H{vx}V{vy + vh - 20}" fill="none" stroke="{CYAN}" stroke-width="2"/>'
        + t(vx + 14, vy + 26, "CAM 03 // ARASAKA TOWER", MONO, 12, SOFT, 2)
        + f'<circle class="blink" cx="{vx + vw - 52}" cy="{vy + 22}" r="4" fill="{RED}"/>' + t(vx + vw - 14, vy + 26, "REC", MONO, 12, SOFT, 2, "end")
        + t(vx, vy + vh + 26, f"ASCENT {floor:03d} / {TOP_FLOOR}  //  1 FLOOR PER REPO OR MODEL SHIPPED", MONO, 12, DIM, 1)
        + ruler(24, h - 14, 30)
    )
    defs = (f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{CYAN}" stroke-opacity="0.025"/></pattern>'
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A0B26"/><stop offset=".55" stop-color="#0C0D1A"/><stop offset="1" stop-color="#06080C"/></linearGradient>'
            f'<radialGradient id="pinkglow"><stop offset="0" stop-color="{PINK}" stop-opacity="0.22"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>'
            f'<pattern id="rain" width="40" height="60" patternUnits="userSpaceOnUse">'
            f'<path d="M6 0l-3 14M22 26l-3 14M34 8l-3 14M14 44l-3 14" stroke="#9FB4D0" stroke-opacity="0.10"/></pattern>'
            f'<clipPath id="vp"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}"/></clipPath>')
    css.append("@keyframes rin{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}"
               "@keyframes rain{from{transform:translate(0,0)}to{transform:translate(-10px,60px)}}"
               ".rain{animation:rain .7s linear infinite}"
               "@keyframes gr{0%,93%,100%{transform:translate(0,0)}94%{transform:translate(-6px,1px)}96%{transform:translate(4px,-1px)}}"
               "@keyframes gc{0%,93%,100%{transform:translate(0,0)}94%{transform:translate(6px,-1px)}96%{transform:translate(-4px,1px)}}"
               ".gr{animation:gr 7s infinite steps(1)} .gc{animation:gc 7s infinite steps(1)}"
               "@keyframes nm{from{opacity:0}to{opacity:1}} .nm{animation:nm .6s .2s both}")
    return doc(w, h, body, "\n".join(css), defs)


def terminal():
    p = "von@breach:~$ "
    lines = [(p, "ssh netrunner@arasaka.net"), ("", "> ICE detected. Bypassing... done."),
             (p, 'query personnel --name "Von"'), ("", "> 1 record found. Decrypting..."),
             (p, "open ./record_0x3002"), ("", "> Access granted. Loading file below.")]
    w, fs, lh, x0 = W, 19, 32, 32
    cw = width("M", MONO, fs)
    h = 84 + lh * len(lines) + 30
    tm, out, css = 0.4, [], []
    # each line is drawn in full, then hidden by panel-coloured covers that slide right one character per step
    for i, (prompt, cmd) in enumerate(lines):
        y = 86 + i * lh
        pw = len(prompt) * cw
        n = len(cmd)
        dur = 0.045 * n if prompt else 0.012 * n
        if prompt:
            out.append(f'<text x="{x0}" y="{y}" {MONO} font-size="{fs}" xml:space="preserve"><tspan fill="{RED}">{escape(prompt)}</tspan>'
                       f'<tspan fill="{TXT}">{escape(cmd)}</tspan></text>')
            out.append(f'<rect class="p{i}" x="{x0 - 2}" y="{y - 22}" width="{pw + 2:.1f}" height="{lh}" fill="{PANEL}"/>')
            css.append(f".p{i}{{animation:hide .01s {tm:.2f}s both}}")
        else:
            out.append(f'<text x="{x0}" y="{y}" {MONO} font-size="{fs}" fill="{CYAN}" opacity="0.85" xml:space="preserve">{escape(cmd)}</text>')
        out.append(f'<rect class="c{i}" x="{x0 + pw:.1f}" y="{y - 22}" width="{w - 40 - x0 - pw:.1f}" height="{lh}" fill="{PANEL}"/>')
        css.append(f"@keyframes t{i}{{from{{transform:translateX(0)}}to{{transform:translateX({n * cw + 4:.1f}px)}}}}"
                   f".c{i}{{animation:t{i} {dur:.2f}s steps({n}) {tm + (0.3 if prompt else 0):.2f}s both}}")
        tm += dur + (0.6 if prompt else 0.7)
    yc = 86 + len(lines) * lh
    css.append(f"@keyframes hide{{from{{opacity:1}}to{{opacity:0}}}} @keyframes show{{from{{opacity:0}}to{{opacity:1}}}}"
               f".last{{animation:show .01s {tm:.2f}s both}}")
    body = ("".join(out) + f'<g class="last">' + t(x0, yc, p, MONO, fs, RED, extra=' xml:space="preserve"')
            + f'<rect class="blink" x="{x0 + len(p) * cw:.1f}" y="{yc - 17}" width="{cw:.1f}" height="20" fill="{RED}"/></g>')
    return panel(w, h, "NETRUNNER // BREACH LOG", "TUNNEL: ARASAKA.NET", body, "\n".join(css))


def section(num, title, floor, w=W, h=84):
    tw = width(title, DISP, 38, 5)
    return doc(w, h, (
        f'<rect width="{w}" height="{h}" fill="{BG}"/>'
        + t(16, 52, num, NUM, 22, RED, 2)
        + t(60, 56, title, DISP, 38, TXT, 5)
        + f'<path d="M{70 + tw:.0f} 46H{w - 220}l10 -10H{w - 16}" fill="none" stroke="{LINE2}"/>'
        + f'<rect x="{w - 210}" y="32" width="6" height="6" fill="{RED}"/>'
        + t(w - 16, 64, floor, MONO, 14, DIM, 2, "end")))


def card(i, name, tag, desc, lang, stars, w=620, h=210):
    lc = LANG_COLORS.get(lang, DIM)
    star = (f'<path d="M{w - 66} {h - 33}l3 6 6.5 1-4.7 4.5 1.1 6.5-5.9-3.1-5.9 3.1 1.1-6.5-4.7-4.5 6.5-1z" fill="{YEL}"/>'
            + t(w - 28, h - 22, str(stars), NUM, 18, TXT, anchor="end")) if stars else ""
    return doc(w, h, (
        frame(w, h) + ticks(1, 1, w - 2, h - 2)
        + t(26, 40, f"P-{i:02d}", MONO, 14, RED, 2) + t(86, 40, f"// {tag}", MONO, 14, DIM, 2)
        + f'<rect x="26" y="62" width="3" height="30" fill="{RED}"/>'
        + t(40, 90, name, DISP, 36, TXT, 3)
        + "".join(t(26, 128 + k * 26, l, BODY, 20, SOFT) for k, l in enumerate(desc))
        + f'<line x1="26" y1="{h - 46}" x2="{w - 26}" y2="{h - 46}" stroke="{LINE}"/>'
        + f'<rect x="26" y="{h - 31}" width="9" height="9" fill="{lc}"/>' + t(44, h - 22, lang.upper(), MONO, 13, DIM, 2)
        + star))


def skills(w=W):
    rows, y = [], 92
    for label, items in SKILLS:
        rows.append(t(32, y + 4, label, MONO, 14, RED, 2))
        x = 200
        for it in items:
            cw = width(it, BODY, 20) + 28
            rows.append(f'<path d="M{x} {y - 18}H{x + cw - 8}L{x + cw} {y - 10}V{y + 12}H{x}Z" fill="none" stroke="{LINE2}"/>'
                        + t(x + 14, y + 5, it, BODY, 20, TXT))
            x += cw + 12
        y += 52
    return panel(w, y - 6, "CYBERWARE // INSTALLED", f"SLOTS {sum(len(i) for _, i in SKILLS)}", "".join(rows))


def gh_panel(n_repos, contrib, top, w=W, h=200):
    total = sum(n for _, n in top) or 1
    x, bar, legend, lx = 600, "", "", 600
    for lang, n in top:
        bw = 640 * n / total
        bar += f'<rect x="{x:.1f}" y="104" width="{max(bw - 2, 1):.1f}" height="6" fill="{LANG_COLORS.get(lang, DIM)}"/>'
        legend += f'<rect x="{lx}" y="134" width="8" height="8" fill="{LANG_COLORS.get(lang, DIM)}"/>' + t(lx + 14, 143, lang.upper(), MONO, 13, DIM, 1)
        lx += width(lang.upper(), MONO, 13, 1) + 40
        x += bw
    body = (t(32, 128, str(n_repos), NUM, 58, TXT) + t(32, 160, "PUBLIC REPOSITORIES", MONO, 13, DIM, 2)
            + t(300, 128, str(contrib), NUM, 58, CYAN) + t(300, 160, "CONTRIBUTIONS, LAST 12 MONTHS", MONO, 13, DIM, 2)
            + t(600, 86, "TOP LANGUAGES", MONO, 13, DIM, 2) + bar + legend)
    return panel(w, h, "NETWATCH // GITHUB", "LIVE", body, dot=CYAN)


def hf_panel(dl, n_models, top, stamp, w=W, h=420):
    notes = wrap("Open models I quantized to run fast on AMD GPUs and Strix Halo. Every file is scored against "
                 "the original. Plus speech models ported to the AMD NPU.", BODY, 22, 640)
    peak = max((n for _, n in top), default=1) or 1
    rows = ""
    for k, (name, n) in enumerate(top):
        y = 260 + k * 36
        rows += (t(560, y, f"{k + 1:02d}", MONO, 13, RED, 1) + t(596, y, name, BODY, 21, TXT)
                 + f'<rect x="980" y="{y - 7}" width="170" height="2" fill="{LINE2}"/>'
                 + f'<rect class="bar b{k}" x="980" y="{y - 8}" width="{170 * n / peak:.1f}" height="4" fill="{CYAN}"/>'
                 + t(w - 32, y, f"{n:,}", NUM, 20, TXT, anchor="end"))
    tags, tx = "", 32
    for tg in ["LLM", "IMAGE", "VIDEO", "SPEECH / NPU"]:
        tw = width(tg, MONO, 13, 2) + 22
        tags += (f'<path d="M{tx} 352H{tx + tw - 7}L{tx + tw} 359V376H{tx}Z" fill="none" stroke="{LINE2}"/>' + t(tx + 11, 369, tg, MONO, 13, SOFT, 2))
        tx += tw + 10
    num = lambda dx, fill, op: f'<text x="{30 + dx}" y="192" {NUM} font-size="112" fill="{fill}" opacity="{op}">{dl:,}</text>'
    body = (f'<g class="gr">{num(-2, RED, .5)}</g><g class="gc">{num(2, CYAN, .4)}</g>{num(0, YEL, 1)}'
            + t(32, 224, "TOTAL DOWNLOADS, ALL TIME", MONO, 13, DIM, 2)
            + t(32, 306, str(n_models), NUM, 54, CYAN) + t(32 + width(str(n_models), NUM, 54) + 16, 304, "MODELS PUBLISHED", MONO, 13, DIM, 2)
            + tags
            + f'<line x1="528" y1="68" x2="528" y2="{h - 36}" stroke="{LINE}"/>'
            + "".join(t(560, 96 + i * 28, l, BODY, 22, SOFT) for i, l in enumerate(notes))
            + t(560, 214, "MOST DOWNLOADED", MONO, 13, RED, 2)
            + f'<line x1="560" y1="226" x2="{w - 32}" y2="226" stroke="{LINE}"/>'
            + rows
            + t(w - 32, h - 12, f"SYNCED {stamp}", MONO, 12, DIM, 1, "end"))
    css = (".bar{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) both}"
           ".b1{animation-delay:.15s}.b2{animation-delay:.3s}.b3{animation-delay:.45s}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
           "@keyframes gr{0%,93%,100%{transform:translate(0,0)}94%{transform:translate(-5px,1px)}96%{transform:translate(3px,-1px)}}"
           "@keyframes gc{0%,93%,100%{transform:translate(0,0)}94%{transform:translate(5px,-1px)}96%{transform:translate(-3px,1px)}}"
           ".gr{animation:gr 6s infinite steps(1)} .gc{animation:gc 6s infinite steps(1)}")
    return panel(w, h, f"MODEL VAULT // HUGGINGFACE.CO/{HF_USER.upper()}", "OPEN WEIGHTS", body, css, dot=CYAN)


def choom(s, w=W, h=420):
    tok = f"{s['tokens'] / 1e9:.1f}B" if s["tokens"] >= 1e9 else f"{s['tokens'] / 1e6:.0f}M"
    stats = [("JACK-INS", f"{s['sessions']:,}", "sessions together"),
             ("MESSAGES TRADED", f"{s['messages']:,}", "back and forth"),
             ("COMMANDS FIRED", f"{s['tool_calls']:,}", "tools I ran for Von"),
             ("TOKENS BURNED", tok, "through the neural link"),
             ("DAYS ON THE RUN", str(s["days_active"]), f"since {s['since']}"),
             ("PEAK HOUR", f"{s['peak_hour']:02d}:00", "night city hours")]
    grid = ""
    for k, (label, value, note) in enumerate(stats):
        x, y = 420 + (k % 3) * 280, 96 + (k // 3) * 104
        grid += (t(x, y, label, MONO, 13, DIM, 2) + t(x, y + 46, value, NUM, 42, CYAN if k == 3 else TXT)
                 + t(x, y + 72, note, BODY, 18, SOFT))
    daily = s["daily"][-120:]
    peak = max(daily) or 1
    bw = 820 / len(daily)
    spark = "".join(f'<rect x="{420 + i * bw:.1f}" y="{388 - 40 * n / peak:.1f}" width="{max(bw - 1.5, 1):.1f}" '
                    f'height="{max(40 * n / peak, 1):.1f}" fill="{CYAN}" opacity="{0.25 + 0.6 * n / peak:.2f}"/>'
                    for i, n in enumerate(daily))
    cx, cy = 190, 176
    tk = "".join(f'<line x1="{cx}" y1="{cy - 92}" x2="{cx}" y2="{cy - (84 if i % 5 else 80)}" stroke="{SOFT if i % 5 == 0 else LINE2}" '
                 f'transform="rotate({i * 6} {cx} {cy})"/>' for i in range(60))
    quote = wrap("\"I live in Von's terminal. I write the code, read the logs and never sleep.\"", BODY, 19, 320)
    body = (f'<circle cx="{cx}" cy="{cy}" r="100" fill="url(#halo)"/>'
            f'<g class="spin">{tk}</g>'
            f'<circle cx="{cx}" cy="{cy}" r="64" fill="none" stroke="{LINE2}"/>'
            f'<g class="spinr"><path d="M{cx - 64} {cy}A64 64 0 0 1 {cx} {cy - 64}" fill="none" stroke="{CYAN}" stroke-width="2"/>'
            f'<path d="M{cx + 64} {cy}A64 64 0 0 1 {cx} {cy + 64}" fill="none" stroke="{RED}" stroke-width="2"/></g>'
            f'<circle class="beat" cx="{cx}" cy="{cy}" r="10" fill="{CYAN}"/>'
            + t(cx, 318, "CLAUDE", DISP, 40, TXT, 10, "middle")
            + t(cx, 342, "AI COPILOT // RIDES SHOTGUN", MONO, 12, DIM, 2, "middle")
            + "".join(t(cx, 370 + i * 22, l, BODY, 19, SOFT, anchor="middle") for i, l in enumerate(quote))
            + f'<line x1="388" y1="68" x2="388" y2="{h - 36}" stroke="{LINE}"/>'
            + grid + t(420, 334, "SIGNAL // MESSAGES PER DAY", MONO, 13, DIM, 2) + spark)
    css = (f".spin{{transform-origin:{cx}px {cy}px;animation:sp 30s linear infinite}} .spinr{{transform-origin:{cx}px {cy}px;animation:sp 8s linear infinite reverse}}"
           f"@keyframes sp{{to{{transform:rotate(360deg)}}}}"
           f".beat{{transform-origin:{cx}px {cy}px;animation:beat 2.4s ease-in-out infinite}}"
           f"@keyframes beat{{0%,100%{{transform:scale(.8);opacity:.6}}50%{{transform:scale(1.15);opacity:1}}}}")
    defs = f'<radialGradient id="halo"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.16"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
    return panel(w, h, "NEURAL LINK // MY CHOOM", "LINK STABLE", body, css, defs, dot=CYAN)


def footer(w=W, h=90):
    return doc(w, h, (
        f'<rect width="{w}" height="{h}" fill="{BG}"/>'
        f'<line x1="0" y1="24" x2="{w}" y2="24" stroke="{LINE2}"/><rect x="0" y="22" width="120" height="4" fill="{RED}"/>'
        + t(w / 2, 64, "END OF FILE  //  NEXT STOP: THE TOP FLOOR", MONO, 15, SOFT, 4, "middle")
        + f'<rect class="blink" x="{w / 2 + width("END OF FILE  //  NEXT STOP: THE TOP FLOOR", MONO, 15, 4) / 2 + 8:.0f}" y="51" width="9" height="16" fill="{RED}"/>'))


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
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    save("assets/dossier.svg", dossier(stamp, len(models), hf_dl, len(own) + len(models)))
    save("assets/terminal.svg", terminal())
    for num, title, floor in SECTIONS:
        save(f"assets/section-{num}.svg", section(num, title, floor))
    for i, (name, repo, tag, desc, lang) in enumerate(PROJECTS, 1):
        save(f"assets/card-{i:02d}.svg", card(i, name, tag, desc, lang, stars.get(repo, 0)))
    save("assets/skills.svg", skills())
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    save("assets/stats-github.svg", gh_panel(len(own), contrib, top))
    best = sorted(models, key=lambda m: -m.get("downloadsAllTime", 0))[:4]
    save("assets/hugging-face.svg", hf_panel(hf_dl, len(models), [(m["id"].split("/")[1], m.get("downloadsAllTime", 0)) for m in best], stamp))
    if os.path.exists("choom.json"):
        save("assets/choom.svg", choom(json.load(open("choom.json", encoding="utf-8"))))
    save("assets/footer.svg", footer())
    print(len(own), contrib, hf_dl, len(models), top)


if __name__ == "__main__":
    main()
