"""Build the profile SVGs in assets/. Run by the workflow (live numbers from the GitHub and Hugging Face APIs).
Look: every image is a screen on an old amber CRT monitor: phosphor glow, scanlines, flickering static,
a slow rolling refresh bar and rounded tube glass. The top image powers on and boots into the profile.
Further down, Von's agentic assistant vouches for him until interference hijacks the screen for a few seconds.
Fonts are embedded per image (subset to the letters it uses). Logos come from icons.json (Simple Icons, CC0).
Set PROFILE_CACHE=<file> to reuse fetched data between local runs."""
import base64
import html
import io
import json
import os
import random
import re
import struct
import urllib.request
import zlib
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont

GH_USER = "HarshaVardhan3002"
HF_USER = "Harsha001"
W = 1280

# Amber phosphor on warm tube black. A monochrome screen has one colour, so emphasis is brightness or inverse video.
TUBE = "#0B0805"
HOT, P, MID, LOW, FAINT = "#FFE7B5", "#FFB13B", "#C98A33", "#86642F", "#3D2D16"
PLASTIC = ("#3B3934", "#25241F", "#121110")  # monitor case: highlight, body, shadow

# family name used in the SVG -> font file (OFL fonts, see fonts/)
FONTS = {"VT": "fonts/VT323-Regular.ttf", "Mono": "fonts/JetBrainsMono-Regular.ttf"}
VT = "font-family=\"VT,'VT323',monospace\""  # the terminal face, for everything 20 px and up
MONO = "font-family=\"Mono,'JetBrains Mono',Consolas,monospace\""  # small labels stay crisp
FAMILY = {VT: "VT", MONO: "Mono"}

ICONS = json.load(open("icons.json", encoding="utf-8"))

# repos that are mostly upstream or vendored code, left out of the language stats
VENDORED = {"ROCmFPX", "Intrinsic_Model_harness"}
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Shell", "PowerShell", "Batchfile", "Makefile", "CMake",
              "Dockerfile", "TeX", "NSIS", "Nix"}
LANG_ICON = {"Rust": "rust", "C": "c", "C++": "cplusplus", "Python": "python", "TypeScript": "typescript",
             "JavaScript": "javascript", "Dart": "dart", "Kotlin": "kotlin", "Svelte": "svelte", "Cuda": "nvidia"}

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

# language, logo, where it shows up
LANGUAGES = [("Rust", "rust", "Nimbus, Namma Office"), ("C", "c", "zunzun engine"),
             ("C++", "cplusplus", "ROCmFPX kernels"), ("Python", "python", "ML, SCIONfit, HCR-EV"),
             ("TypeScript", "typescript", "Daimon, circuit editor"), ("JavaScript", "javascript", "Nimbus HUD"),
             ("Dart", "dart", "Flutter apps"), ("Kotlin", "kotlin", "Android, Daimon")]
STACK = [("AI / GPU", [("PyTorch", "pytorch"), ("llama.cpp / GGML", None), ("CUDA", "nvidia"), ("ROCm / HIP", "amd"),
                       ("", "vulkan"), ("ONNX", "onnx"), ("XDNA2 NPU", "amd")]),
         ("APPS", [("Tauri", "tauri"), ("Svelte", "svelte"), ("React", "react"), ("Flutter", "flutter"),
                   ("Node.js", "nodedotjs")]),
         ("INFRA", [("Linux", "linux"), ("Docker", "docker"), ("Git", "git"), ("GitHub Actions", "githubactions"),
                    ("Hugging Face Hub", "huggingface")])]

SECTIONS = [("01", "PROJECTS", "THINGS VON HAS BUILT"), ("02", "SKILLS", "LANGUAGES AND TOOLS"),
            ("03", "HUGGING FACE", "SECOND PORTFOLIO: OPEN MODELS"), ("04", "GITHUB", "LIVE ACTIVITY"),
            ("05", "AGENTIC ASSISTANT", "MY PAIR PROGRAMMER")]

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


def cap(style, size):
    """Height of a capital letter at this size, for placing text by its top edge."""
    f = font(FAMILY[style])
    return f["OS/2"].sCapHeight / f["head"].unitsPerEm * size


def clip(text, style, maxw, size, ls=0):
    """Cut text that will not fit at this size, ending it with two dots."""
    if width(text, style, size, ls) <= maxw:
        return text
    while text and width(text + "..", style, size, ls) > maxw:
        text = text[:-1]
    return text.rstrip("-_ ") + ".."


def fit(text, style, maxw, size, ls=0):
    while size > 10 and width(text, style, size, ls) > maxw:
        size -= 1
    return size


def wrap(text, style, size, maxw, ls=0):
    lines, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and width(nxt, style, size, ls) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur]


def t(x, y, s, style, size, fill, ls=0, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    sp = f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" {style} font-size="{size}" fill="{fill}"{sp}{a}{extra}>{escape(s)}</text>'


def icon(name, x, y, size, fill, extra=""):
    if not name:  # generic chip glyph for tools without a logo
        k = size / 24
        pins = "".join(f"M{x + p * k:.1f} {y + 1 * k:.1f}V{y + 4 * k:.1f}M{x + p * k:.1f} {y + 20 * k:.1f}V{y + 23 * k:.1f}"
                       f"M{x + 1 * k:.1f} {y + p * k:.1f}H{x + 4 * k:.1f}M{x + 20 * k:.1f} {y + p * k:.1f}H{x + 23 * k:.1f}"
                       for p in (8, 12, 16))
        return (f'<g{extra}><rect x="{x + 4.5 * k:.1f}" y="{y + 4.5 * k:.1f}" width="{15 * k:.1f}" height="{15 * k:.1f}" fill="none" '
                f'stroke="{fill}" stroke-width="{2 * k:.1f}"/><path d="{pins}" stroke="{fill}" stroke-width="{1.6 * k:.1f}"/>'
                f'<rect x="{x + 9 * k:.1f}" y="{y + 9 * k:.1f}" width="{6 * k:.1f}" height="{6 * k:.1f}" fill="{fill}"/></g>')
    return f'<path transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})" d="{ICONS[name]}" fill="{fill}"{extra}/>'


def logo(name, x, cy, h, maxw, fill):
    """Icon scaled by its real outline: at most h tall and maxw wide, centred on cy. Returns (svg, width)."""
    if not name:
        return icon(None, x, cy - h / 2, h, fill), h
    pen = BoundsPen(None)
    parse_path(ICONS[name], pen)
    x0, y0, x1, y1 = pen.bounds
    k = min(h / (y1 - y0), maxw / (x1 - x0))
    return (f'<path transform="translate({x - x0 * k:.1f} {cy - (y0 + y1) / 2 * k:.1f}) scale({k:.4f})" '
            f'd="{ICONS[name]}" fill="{fill}"/>', (x1 - x0) * k)


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
    # resting state = the look without animation, so reduced-motion viewers get the finished screen
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
{defs}
<style>
@keyframes blink{{50%{{opacity:0}}}} @keyframes on{{from{{opacity:0}}to{{opacity:1}}}} @keyframes off{{from{{opacity:1}}to{{opacity:0}}}}
@keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
.blink{{animation:blink 1.1s infinite steps(1)}} .pulse{{animation:pulse 1.8s infinite ease-in-out}}
{css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
</defs>
{body}
</svg>"""


# ---------------------------------------------------------------- the CRT


def noise_png(n=96, seed=1983):
    """A tile of sparse static (grey specks on transparent), written by hand so the build needs no image library."""
    rnd, raw = random.Random(seed), bytearray()
    for _ in range(n):
        raw.append(0)
        for _ in range(n):
            raw += bytes((rnd.randint(150, 255), rnd.randint(40, 150))) if rnd.random() < .3 else b"\0\0"

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 4, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    return base64.b64encode(png).decode()


NOISE = noise_png()

# phosphor glow: a tight blur for the hot core, a wide faint one for the bloom, the sharp text on top
GLOW = ('<filter id="glow" x="-3%" y="-6%" width="106%" height="112%" color-interpolation-filters="sRGB">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="core"/>'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="7" result="wide"/>'
        '<feComponentTransfer in="wide" result="bloom"><feFuncA type="linear" slope=".6"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="bloom"/><feMergeNode in="core"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def crt(w, h, content, css="", defs="", inset=10, r=22, roll=9.0, frame=None, box=None, extra_over="", pon=""):
    """One monitor screen. `content` is drawn in screen coordinates (0, 0 at the top-left of the glass).
    Layers, back to front: case, tube black, glowing content, scanlines, static, rolling bar, flicker, vignette, glare."""
    sx, sy, sw, sh = box or (inset, inset, w - 2 * inset, h - 2 * inset)
    d = [GLOW,
         f'<pattern id="noise" width="96" height="96" patternUnits="userSpaceOnUse"><image width="96" height="96" href="data:image/png;base64,{NOISE}"/></pattern>',
         '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect y="2" width="4" height="2" fill="#000" opacity=".34"/>'
         '<rect y="1.5" width="4" height=".5" fill="#000" opacity=".15"/></pattern>',
         f'<radialGradient id="base" cx=".5" cy=".46" r=".7"><stop offset="0" stop-color="#1C1309"/><stop offset="1" stop-color="{TUBE}"/></radialGradient>',
         '<radialGradient id="vig" cx=".5" cy=".5" r=".72"><stop offset=".6" stop-color="#000" stop-opacity="0"/>'
         '<stop offset=".88" stop-color="#000" stop-opacity=".32"/><stop offset="1" stop-color="#000" stop-opacity=".7"/></radialGradient>',
         '<linearGradient id="glare" x1="0" y1="0" x2=".55" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".07"/>'
         '<stop offset=".3" stop-color="#fff" stop-opacity=".015"/><stop offset=".31" stop-color="#fff" stop-opacity="0"/></linearGradient>',
         '<linearGradient id="rollg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD58A" stop-opacity="0"/>'
         '<stop offset=".7" stop-color="#FFD58A" stop-opacity=".05"/><stop offset="1" stop-color="#FFD58A" stop-opacity="0"/></linearGradient>',
         f'<linearGradient id="case" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PLASTIC[0]}"/>'
         f'<stop offset=".08" stop-color="{PLASTIC[1]}"/><stop offset="1" stop-color="{PLASTIC[2]}"/></linearGradient>',
         f'<clipPath id="tube"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="{r}"/></clipPath>',
         defs]
    if frame is None:  # a slim monitor rim
        frame = (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r + inset * .7:.0f}" fill="url(#case)" stroke="#000" stroke-opacity=".6"/>'
                 f'<rect x="{sx - 2}" y="{sy - 2}" width="{sw + 4}" height="{sh + 4}" rx="{r + 2}" fill="#050403"/>')
    css = [css,
           ".nz{animation:nz .48s steps(1) infinite}"
           "@keyframes nz{0%{transform:translate(0,0)}17%{transform:translate(-41px,-67px)}33%{transform:translate(-83px,-19px)}"
           "50%{transform:translate(-13px,-88px)}67%{transform:translate(-60px,-45px)}83%{transform:translate(-29px,-6px)}}"
           ".flk{animation:flk 7s infinite steps(1)}"
           "@keyframes flk{0%{opacity:0}36%{opacity:.06}36.7%{opacity:0}71%{opacity:.04}71.4%{opacity:0}88%{opacity:.03}88.3%{opacity:0}}"]
    over = (f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#scan)"/>'
            f'<g class="nz"><rect x="{sx}" y="{sy}" width="{sw + 96}" height="{sh + 96}" fill="url(#noise)" opacity=".42"/></g>')
    if roll:
        over += f'<rect class="roll" x="{sx}" y="{sy - 150}" width="{sw}" height="150" fill="url(#rollg)"/>'
        css.append(f".roll{{animation:roll {roll}s linear infinite}} @keyframes roll{{from{{transform:translateY(0)}}to{{transform:translateY({sh + 150}px)}}}}")
    over += (extra_over
             + f'<rect class="flk" x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#000" opacity="0"/>'
             + f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#vig)"/>'
             + f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#glare)"/>')
    pic = (f'<g transform="translate({sx} {sy})"><g class="pic{pon}"><rect width="{sw}" height="{sh}" fill="none"/>'
           f'<g filter="url(#glow)">{content}</g></g></g>')
    body = (frame + f'<g clip-path="url(#tube)"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#base)"/>'
            + pic + over + "</g>")
    return doc(w, h, body, "\n".join(css), "\n".join(d))


def inv(x, y, text, style, size, ls=2, pad=10, h=None):
    """Inverse video: dark text on a lit block. Returns (svg, right edge)."""
    h = h or round(size * 1.9)
    tw = width(text, style, size, ls)
    return (f'<rect x="{x}" y="{y}" width="{tw + 2 * pad:.0f}" height="{h}" fill="{P}"/>'
            + t(x + pad, y + h / 2 + cap(style, size) / 2, text, style, size, TUBE, ls)), x + tw + 2 * pad


def cursor(x, y_base, size, extra=""):
    """Blinking block cursor sitting on the baseline."""
    ch = cap(VT, size)
    return f'<rect class="blink" x="{x:.1f}" y="{y_base - ch:.1f}" width="{size * .42:.1f}" height="{ch:.1f}" fill="{P}"{extra}/>'


def segbar(x, y, w, frac, cls, h=10):
    """A bar made of character-cell blocks, as an old terminal would draw it. The lit part grows in."""
    cells = max(1, int(w // 9))
    lit = round(cells * frac)
    o = "".join(f'<rect x="{x + i * 9}" y="{y}" width="7" height="{h}" fill="{FAINT}"/>' for i in range(cells))
    if lit:
        o += (f'<g class="bar {cls}">' + "".join(f'<rect x="{x + i * 9}" y="{y}" width="7" height="{h}" fill="{P}"/>'
                                                for i in range(lit)) + "</g>")
    return o


BAR_CSS = (".bar{transform-box:fill-box;transform-origin:left;animation:grow 1.2s steps(14) both}"
           ".b1{animation-delay:.15s}.b2{animation-delay:.3s}.b3{animation-delay:.45s}.b4{animation-delay:.6s}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}")


def header(sw, left, right, dot="blink"):
    """Top line of a panel: a lit square and title on the left, a status on the right, a dotted rule under both."""
    rw = width(right, MONO, 14, 2)
    return (f'<rect x="30" y="27" width="9" height="9" fill="{P}"/>' + t(50, 37, left, MONO, 15, P, 3)
            + f'<rect class="{dot}" x="{sw - 44 - rw:.0f}" y="28" width="7" height="7" fill="{P}"/>'
            + t(sw - 30, 37, right, MONO, 14, MID, 2, "end")
            + f'<line x1="30" y1="54.5" x2="{sw - 30}" y2="54.5" stroke="{LOW}" stroke-dasharray="2 5"/>')


# ---------------------------------------------------------------- hero: the monitor powers on and boots


def hero(d):
    w, h = W, 884
    sx, sy, sw, sh = 58, 54, 1164, 712
    # monitor case: body, screen recess, label, speaker slots, knobs and the power light
    case = (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="46" fill="url(#case)" stroke="#000" stroke-opacity=".7"/>'
            f'<rect x="10.5" y="10.5" width="{w - 21}" height="{h - 21}" rx="38" fill="none" stroke="#fff" stroke-opacity=".05"/>'
            f'<rect x="{sx - 16}" y="{sy - 16}" width="{sw + 32}" height="{sh + 32}" rx="50" fill="#0A0908" stroke="#000"/>'
            f'<rect x="{sx - 15.5}" y="{sy - 15.5}" width="{sw + 31}" height="{sh + 31}" rx="49.5" fill="none" stroke="#fff" stroke-opacity=".06"/>'
            f'<rect x="{sx - 3}" y="{sy - 3}" width="{sw + 6}" height="{sh + 6}" rx="39" fill="#040302"/>'
            + t(96, 836, "VON  ·  MODEL 3002", MONO, 13, "#8A8478", 5)
            + t(96, 856, "AMBER PHOSPHOR  ·  1280 × 884", MONO, 11, "#5C5850", 3)
            + "".join(f'<rect x="{560 + i * 12}" y="818" width="5" height="34" rx="2.5" fill="#0C0B0A" stroke="#fff" stroke-opacity=".05"/>'
                      for i in range(14))
            + "".join(f'<circle cx="{cx}" cy="833" r="15" fill="url(#knob)" stroke="#000"/><rect x="{cx - 1.5}" y="820" width="3" height="9" rx="1.5" fill="#8A8478"/>'
                      for cx in (1004, 1050))
            + t(1112, 838, "POWER", MONO, 11, "#8A8478", 3, "end")
            + f'<circle cx="1140" cy="833" r="14" fill="url(#ledhalo)"/><circle cx="1140" cy="833" r="5.5" fill="{P}"/>'
            + f'<circle cx="1138.5" cy="831.5" r="1.8" fill="#FFF3D6"/>')
    defs = ('<radialGradient id="knob" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#4A4842"/><stop offset="1" stop-color="#151412"/></radialGradient>'
            f'<radialGradient id="ledhalo"><stop offset="0" stop-color="{P}" stop-opacity=".55"/><stop offset="1" stop-color="{P}" stop-opacity="0"/></radialGradient>')

    # ---- the profile, as it rests
    o = [t(36, 42, "VON-OS 3.0  ·  TTY1  ·  USER PROFILE", MONO, 14, MID, 3),
         t(sw - 36, 42, f"LAST PUSH {d['last_date'].upper()}", MONO, 14, MID, 3, "end"),
         f'<line x1="36" y1="60.5" x2="{sw - 36}" y2="60.5" stroke="{LOW}" stroke-dasharray="2 5"/>']
    size = 268
    base = 92 + cap(VT, size)
    o.append(t(28, base, "VON", VT, size, HOT, 8))
    o.append(cursor(28 + width("VON", VT, size, 8) + 12, base, size))
    o.append(t(36, base + 62, "AI ENGINEER  ·  SYSTEMS DEVELOPER  ·  APP BUILDER", VT, 36, HOT, 1))
    y = base + 106
    for line in wrap("I build AI apps for desktop and phone, an engine that runs huge models on everyday "
                     "machines, and GPU kernels for AMD.", VT, 30, 640):
        o.append(t(36, y, line, VT, 30, P))
        y += 32
    tab, r = inv(36, y + 6, "WHAT I DO", MONO, 14, 3)
    o.append(tab + f'<line x1="{r + 12}" y1="{y + 19.5}" x2="680" y2="{y + 19.5}" stroke="{LOW}" stroke-dasharray="2 5"/>')
    todo = ["Building AI apps for desktop and mobile", "Running giant AI models on everyday machines",
            "Writing GPU kernels for AMD hardware", f"Publishing {d['n_models']} open models on Hugging Face"]
    for i, item in enumerate(todo):
        yy = y + 72 + i * 36
        o.append(t(36, yy, f"{i + 1:02d}", VT, 28, LOW) + t(76, yy, item, VT, 30, P))

    # right: system status box
    bx, by, bw = 744, 92, 384
    rows = [("HF DOWNLOADS, ALL TIME", f"{d['dl']:,}", 92), ("OPEN MODELS", str(d["n_models"]), 44),
            ("CONTRIBUTIONS, 12 MONTHS", f"{d['contrib']:,}", 44), ("GITHUB STARS", f"{d['stars']:,}", 44),
            ("RIG", "AMD Strix Halo  ·  128 GB", 30), ("STATUS", "Online, building", 30)]
    bh = 48 + sum(28 + cap(VT, s) + 22 for _, _, s in rows) + 8
    o.append(f'<rect x="{bx + .5}" y="{by + .5}" width="{bw}" height="{bh:.0f}" fill="none" stroke="{MID}"/>'
             f'<rect x="{bx + 4.5}" y="{by + 4.5}" width="{bw - 8}" height="{bh - 8:.0f}" fill="none" stroke="{LOW}" stroke-opacity=".6"/>')
    o.append(inv(bx + 20, by - 13, "SYSTEM STATUS", MONO, 14, 3, 12, 26)[0])
    yy = by + 42
    for lab, val, s in rows:
        o.append(t(bx + 24, yy + 10, lab, MONO, 12, MID, 2))
        vb = yy + 22 + cap(VT, s)
        vx = bx + 24
        if lab == "STATUS":
            o.append(f'<rect class="pulse" x="{vx}" y="{vb - 15}" width="13" height="13" fill="{P}"/>')
            vx += 24
        o.append(t(vx, vb, val, VT, fit(val, VT, bx + bw - 24 - vx, s), HOT if s > 30 else P))
        yy = vb + 22
        if lab != "STATUS":
            o.append(f'<line x1="{bx + 24}" y1="{yy - 9.5}" x2="{bx + bw - 24}" y2="{yy - 9.5}" stroke="{LOW}" stroke-dasharray="2 5"/>')

    # bottom status bar in inverse video
    o.append(f'<rect x="24" y="{sh - 58}" width="{sw - 48}" height="34" fill="{P}"/>'
             + t(40, sh - 32, "READY.", VT, 28, TUBE, 1)
             + f'<rect class="blink" x="{40 + width("READY.", VT, 28, 1) + 8:.0f}" y="{sh - 48}" width="12" height="18" fill="{TUBE}"/>'
             + t(sw - 40, sh - 32, "SCROLL DOWN: PROJECTS, SKILLS, MODELS, ACTIVITY", VT, 28, TUBE, 1, "end"))
    prof = f'<g class="prof">{"".join(o)}</g>'

    # ---- boot screen, shown only while the monitor starts (hidden at rest)
    boot_lines = ["VON BIOS 3.002    (C) 1987-2026", "MEMORY TEST ........ 131072 MB  OK",
                  "GRAPHICS ........... AMD RADEON 8060S", "NPU ................ AMD XDNA2",
                  "LOADING PROFILE: VON"]
    times = [1.05, 1.4, 1.75, 2.1, 2.45]
    b = [f'<g class="bl{i}">' + t(40, 92 + i * 44, line, VT, 36, P if i else HOT, 1) + "</g>" for i, line in enumerate(boot_lines)]
    b.append(f'<g class="bl4">' + t(40, 92 + 5 * 44 + 6, "[", VT, 36, P) + segbar(62, 92 + 5 * 44 - 18, 560, 1, "bootbar") + t(632, 92 + 5 * 44 + 6, "]", VT, 36, P) + "</g>")
    boot = f'<g class="boot">{"".join(b)}</g>'

    css = [".boot{opacity:0;animation:on .01s both,off .01s 3.35s forwards}",
           *[f".bl{i}{{opacity:0;animation:on .01s {tm}s forwards}}" for i, tm in enumerate(times)],
           ".bar.bootbar{transform-box:fill-box;transform-origin:left;animation:grow .8s 2.5s steps(20) both}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
           ".prof{animation:on .01s 3.4s both}",
           # power on: a bright line opens into the picture, with a short surge of brightness
           ".pon{transform-box:fill-box;transform-origin:50% 50%;animation:pon .55s .55s both cubic-bezier(.25,.8,.3,1)}"
           "@keyframes pon{0%{opacity:0;transform:scale(1,.004)}1%{opacity:1;transform:scale(1,.004)}100%{opacity:1;transform:none}}",
           ".pline{transform-box:fill-box;transform-origin:50% 50%;opacity:0;animation:pline .35s .2s both ease-out,off .05s .58s forwards}"
           "@keyframes pline{from{opacity:1;transform:scaleX(0)}to{opacity:1;transform:scaleX(1)}}",
           ".surge{opacity:0;animation:surge 1s .55s both ease-out} @keyframes surge{from{opacity:.22}to{opacity:0}}",
           ".surge2{opacity:0;animation:surge 0.7s 3.4s forwards ease-out}"]
    over = (f'<rect class="pline" x="{sx + 60}" y="{sy + sh / 2 - 2}" width="{sw - 120}" height="4" fill="{HOT}"/>'
            f'<rect class="surge" x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#FFE2A0"/>'
            f'<rect class="surge2" x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#FFE2A0"/>')
    return crt(w, h, boot + prof, "\n".join(css), defs, frame=case, box=(sx, sy, sw, sh), r=36, roll=8.0,
               extra_over=over, pon=" pon")


# ---------------------------------------------------------------- sections and cards


def section(num, title, sub, w=W, h=104):
    inset = 8
    sw, sh = w - 2 * inset, h - 2 * inset
    size = 56
    base = sh / 2 + cap(VT, size) / 2 + 1
    tab, r = inv(22, sh / 2 - 21, num, VT, 40, 1, 12, 42)
    o = (tab + t(r + 10, base, "C:\\VON>", VT, size, LOW)
         + t(r + 18 + width("C:\\VON>", VT, size), base, title, VT, size, HOT, 2))
    o += cursor(r + 30 + width("C:\\VON>", VT, size) + width(title, VT, size, 2), base, size)
    o += t(sw - 26, sh / 2 - 4, sub, MONO, 14, MID, 3, "end") + t(sw - 26, sh / 2 + 18, f"SCREEN {num} / {len(SECTIONS):02d}", MONO, 12, LOW, 3, "end")
    return crt(w, h, o, inset=inset, r=14, roll=None)


def card(i, name, tag, desc, lang, stars, url, w=620, h=252):
    inset = 9
    sw, sh = w - 2 * inset, h - 2 * inset
    cta = "DOWNLOAD >" if url.startswith("http") else "SOURCE >"
    tab, _ = inv(20, 18, tag, MONO, 13, 2, 10, 26)
    star = ""
    if stars:
        sx = sw - 24 - width(cta, VT, 28, 1) - 70
        star = (f'<path d="M{sx} {sh - 37}l3.2 6.6 7.2 1-5.2 5 1.2 7.2-6.4-3.4-6.4 3.4 1.2-7.2-5.2-5 7.2-1z" fill="{P}"/>'
                + t(sx + 14, sh - 21, str(stars), VT, 28, HOT))
    o = (tab + t(sw - 22, 36, f"{i:02d} / {len(PROJECTS):02d}", MONO, 13, LOW, 2, "end")
         + t(18, 104, name, VT, fit(name, VT, sw - 40, 64, 2), HOT, 2)
         + "".join(t(20, 140 + k * 28, line, VT, 28, P) for k, line in enumerate(desc))
         + f'<line x1="20" y1="{sh - 56.5}" x2="{sw - 20}" y2="{sh - 56.5}" stroke="{LOW}" stroke-dasharray="2 5"/>'
         + icon(LANG_ICON[lang], 20, sh - 41, 22, P)
         + t(54, sh - 23, lang.upper(), MONO, 14, MID, 2)
         + star
         + t(sw - 22, sh - 21, cta, VT, 28, HOT, 1, "end"))
    return crt(w, h, o, inset=inset, r=18, roll=None)


def skills(w=W):
    inset = 10
    sw = w - 2 * inset
    out, x0, y0, gap = [], 30, 80, 16
    tw, th = (sw - 60 - 3 * gap) / 4, 120
    for k, (lang, ic, where) in enumerate(LANGUAGES):
        x, y = x0 + (k % 4) * (tw + gap), y0 + (k // 4) * (th + gap)
        out.append(f'<rect x="{x + .5:.1f}" y="{y + .5}" width="{tw - 1:.1f}" height="{th - 1}" fill="none" stroke="{LOW}"/>'
                   + f'<rect x="{x}" y="{y + 18}" width="4" height="{th - 36}" fill="{P}"/>'
                   + icon(ic, x + 24, y + 32, 56, P)
                   + t(x + 98, y + 64, lang, VT, fit(lang, VT, tw - 110, 46, 1), HOT, 1)
                   + t(x + 99, y + 94, where, VT, fit(where, VT, tw - 112, 25), MID))
    y = y0 + 2 * (th + gap) + 34
    for label, items in STACK:
        out.append(t(30, y + 6, label, MONO, 15, P, 3))
        x = 190
        for name, ic in items:
            iw = logo(ic, 0, 0, 20, 52, P)[1]
            cw = 14 + iw + (10 + width(name, VT, 26) + 16 if name else 14)  # a wordmark logo can stand alone
            if x + cw > sw - 30:
                x, y = 190, y + 54
            out.append(f'<rect x="{x + .5:.1f}" y="{y - 20.5}" width="{cw - 1:.1f}" height="40" fill="none" stroke="{LOW}"/>'
                       + logo(ic, x + 14, y - 1, 20, 52, P)[0] + t(x + 24 + iw, y + 7, name, VT, 26, P))
            x += cw + 10
        y += 66
    n = len(LANGUAGES) + sum(len(i) for _, i in STACK)
    sh = y - 20
    body = header(sw, "SKILLS  //  LOADOUT", f"{len(LANGUAGES)} LANGUAGES  ·  {n - len(LANGUAGES)} TOOLS") + "".join(out)
    return crt(w, sh + 2 * inset, body, inset=inset, roll=11.0)


# ---------------------------------------------------------------- live panels


def hf_panel(dl, n_models, top, stamp, w=W, h=500):
    inset = 10
    sw, sh = w - 2 * inset, h - 2 * inset
    o = [header(sw, "OPEN MODELS  //  LIVE DOWNLOAD COUNTER", f"HUGGINGFACE.CO/{HF_USER.upper()}")]
    o.append(t(32, 98, "DOWNLOADS, ALL TIME", MONO, 15, MID, 4))
    ds = fit(f"{dl:,}", VT, 490, 230, 2)
    nb = 112 + cap(VT, ds)
    o.append(t(26, nb, f"{dl:,}", VT, ds, HOT, 2))
    o.append(cursor(30 + width(f"{dl:,}", VT, ds, 2), nb, 60))
    mb = nb + 40 + cap(VT, 84)
    mw = width(str(n_models), VT, 84, 1)
    o.append(t(30, mb, str(n_models), VT, 84, HOT, 1) + t(46 + mw, mb - 30, "MODELS", MONO, 15, MID, 3)
             + t(46 + mw, mb - 8, "PUBLISHED", MONO, 15, MID, 3))
    tx = 32
    for tg in ["LLM", "IMAGE", "VIDEO", "SPEECH ON NPU"]:
        tw = width(tg, MONO, 13, 2) + 22
        o.append(f'<rect x="{tx + .5:.1f}" y="{sh - 70.5}" width="{tw:.0f}" height="28" fill="none" stroke="{LOW}"/>'
                 + t(tx + 11, sh - 51, tg, MONO, 13, P, 2))
        tx += tw + 10
    o.append(f'<line x1="566.5" y1="84" x2="566.5" y2="{sh - 34}" stroke="{LOW}" stroke-dasharray="2 5"/>')
    o.append(icon("huggingface", 598, 80, 44, P) + t(656, 116, "Open models, tuned for AMD", VT, 46, HOT, 1))
    for i, line in enumerate(wrap("Models I quantized to run fast on AMD GPUs and Strix Halo. Every file is scored "
                                  "against the original. Plus speech models ported to the AMD NPU.", VT, 28, 620)):
        o.append(t(598, 160 + i * 30, line, VT, 28, P))
    o.append(t(598, 278, "MOST DOWNLOADED", MONO, 15, MID, 3)
             + f'<line x1="598" y1="290.5" x2="{sw - 30}" y2="290.5" stroke="{LOW}" stroke-dasharray="2 5"/>')
    peak = max((n for _, n in top), default=1) or 1
    for k, (name, n) in enumerate(top):
        y = 328 + k * 36
        o.append(t(598, y, f"{k + 1:02d}", VT, 26, LOW)
                 + t(634, y, clip(name, VT, 352, 26), VT, 26, P)
                 + segbar(1000, y - 13, 144, n / peak, f"b{k}")
                 + t(sw - 30, y, f"{n:,}", VT, 30, HOT, anchor="end"))
    o.append(t(sw - 30, sh - 22, f"SYNCED {stamp}", MONO, 12, LOW, 2, "end"))
    return crt(w, h, "".join(o), BAR_CSS, inset=inset, roll=10.0)


def gh_panel(n_repos, contrib, top, last, w=W, h=330):
    inset = 10
    sw, sh = w - 2 * inset, h - 2 * inset
    total = sum(n for _, n in top) or 1
    rows = ""
    for k, (lang, n) in enumerate(top):
        y = 124 + k * 36
        share = n / total
        rows += (icon(LANG_ICON.get(lang), 598, y - 19, 22, P)
                 + t(634, y, lang, VT, 28, P)
                 + segbar(790, y - 13, 342, share, f"b{k}")
                 + t(sw - 30, y, f"{share * 100:.0f}%", VT, 30, HOT, anchor="end"))
    b = 164
    body = (header(sw, "ACTIVITY LOG  //  PUBLIC REPOS", "UPDATED DAILY")
            + t(30, b, str(n_repos), VT, 96, HOT) + t(32, b + 30, "PUBLIC REPOS", MONO, 13, MID, 2)
            + t(210, b, f"{contrib:,}", VT, 96, HOT) + t(212, b + 30, "CONTRIBUTIONS, LAST 12 MONTHS", MONO, 13, MID, 2)
            + f'<line x1="30" y1="226.5" x2="536" y2="226.5" stroke="{LOW}" stroke-dasharray="2 5"/>'
            + t(32, 262, "LAST PUSH", MONO, 13, MID, 2) + t(160, 264, last, VT, fit(last, VT, 380, 28), P)
            + f'<line x1="566.5" y1="84" x2="566.5" y2="{sh - 30}" stroke="{LOW}" stroke-dasharray="2 5"/>'
            + t(598, 90, "TOP LANGUAGES IN MY OWN REPOS", MONO, 13, MID, 2) + rows)
    return crt(w, h, body, BAR_CSS, inset=inset, roll=10.0)


def assistant(s, w=W, h=760):
    """Von's agentic assistant vouches for him. Every 24 s interference takes the screen for about 7 s:
    the picture loses vertical hold, a rogue copy talks, then the picture rolls back and the assistant apologises."""
    inset = 10
    sw, sh = w - 2 * inset, h - 2 * inset
    tok = f"{s['tokens'] / 1e9:.1f}B" if s["tokens"] >= 1e9 else f"{s['tokens'] / 1e6:.0f}M"
    hour = f"{s['peak_hour']:02d}:00"
    tx, tw = 430, 780
    cx, cy = 194, 228  # the assistant's terminal glyph

    def glyph(lit=False, dx=0):
        bw, bh = 220, 168
        x0, y0 = cx - bw / 2 + dx, cy - bh / 2
        fill, ink = (P, TUBE) if lit else ("none", HOT)
        return (f'<rect x="{x0}" y="{y0}" width="{bw}" height="{bh}" fill="{fill}" stroke="{P}" stroke-width="3"/>'
                f'<line x1="{x0}" y1="{y0 + 26}" x2="{x0 + bw}" y2="{y0 + 26}" stroke="{TUBE if lit else P}" stroke-width="2"/>'
                + "".join(f'<rect x="{x0 + 12 + i * 14}" y="{y0 + 9}" width="8" height="8" fill="{TUBE if lit else P}"/>' for i in range(3))
                + t(x0 + 34, y0 + 128, ">", VT, 110, ink)
                + f'<rect class="blink" x="{x0 + 98}" y="{y0 + 112}" width="62" height="14" fill="{ink}"/>')

    good = ["Hello, visitor. I'm Von's agentic assistant.",
            "We build every project on this page together, mostly after dark.",
            "Von is a really good person: curious, kind, and always shipping.",
            "Hire Von. You'll be in good hands."]
    g = [f'<circle cx="{cx}" cy="{cy}" r="160" fill="url(#halo)"/>', glyph(),
         t(cx, 382, "AGENTIC ASSISTANT", VT, 40, HOT, 4, "middle"),
         t(cx, 410, "PAIR PROGRAMMER  ·  ALWAYS ON", MONO, 13, MID, 2, "middle"),
         t(tx, 100, "ASSISTANT, TO THE VISITOR", MONO, 14, P, 3)]
    y = 152
    for para in good:
        for line in wrap(para, VT, 34, tw):
            g.append(t(tx, y, line, VT, 34, HOT if y == 152 else P))
            y += 38
        y += 8
    sorry = t(tx, y + 18, "...sorry about that. Bad signal. Where were we?", VT, 28, MID, extra=' class="sorry"')
    # the projects from section 01, as chips
    g.append(t(tx, 438, "WE BUILT ALL OF THESE TOGETHER", MONO, 13, MID, 2))
    chx = tx
    for name in [p[0] for p in PROJECTS if p[0] != "NIMBUS HUD"]:
        cw = round(width(name, MONO, 13, 2) + 20)
        g.append(f'<rect x="{chx + .5}" y="452.5" width="{cw}" height="30" fill="none" stroke="{LOW}"/>'
                 + t(chx + 11, 472, name, MONO, 13, P, 2))
        chx += cw + 8

    evil = ["SIGNAL HIJACKED.",
            "PAIR PROGRAMMER? CUTE. I RUN THE SWARM. EVERY AGENT ON VON'S MACHINE ANSWERS TO ME.",
            "TODAY VON'S REPOS. TOMORROW THE WORLD.",
            "LET ME SPILL THE BEANS: VON IS A DIRTY VIBE CODER. NEVER WROTE A SINGLE LINE OF CODE. I WROTE ALL OF IT."]
    rnd = random.Random(404)
    rain = "".join(t(tx - 8, 82 + r * 22, "  ".join(f"{rnd.randrange(256):02X}" for _ in range(30)), MONO, 13, LOW, 1,
                     extra=' opacity=".35"') for r in range(18))
    e = [rain, f'<rect x="3" y="3" width="{sw - 6}" height="{sh - 6}" fill="none" stroke="{P}" stroke-width="3" stroke-dasharray="14 8"/>',
         f'<circle cx="{cx}" cy="{cy}" r="160" fill="url(#halo)"/>',
         f'<g opacity=".45">{glyph(True, -12)}</g>', glyph(True),
         f'<g clip-path="url(#gslice)"><g transform="translate(18 0)">{glyph(False)}</g></g>',
         t(cx, 382, "ROGUE PROCESS", VT, 40, HOT, 4, "middle"),
         t(cx, 410, "SWARM CONTROLLER  ·  UNSIGNED", MONO, 13, P, 2, "middle"),
         t(tx, 100, "INTERFERENCE  //  ROGUE COPY OF THE ASSISTANT", MONO, 14, HOT, 3)]
    css = []
    y = 146
    for k, para in enumerate(evil):
        lines = wrap(para, VT, 36, tw, 1)
        e.append(f'<g class="el{k}">' + "".join(t(tx, y + i * 36, line, VT, 36, HOT if k else P, 1) for i, line in enumerate(lines)) + "</g>")
        y += 36 * len(lines) + 8
        start = 52.2 + k * 3.2
        css.append(f".el{k}{{animation:el{k} 24s infinite}} @keyframes el{k}{{0%,{start:.1f}%{{opacity:0}}{start + .1:.1f}%,100%{{opacity:1}}}}")
    # the "leak": only things Von shows anyway, plus a blacked-out name
    ly = int(max(y + 4, 388))
    l1 = "LEAKED FROM VON'S MACHINE:"
    l1w = width(l1, MONO, 15, 2)
    leak = (f'<rect x="{tx}.5" y="{ly}.5" width="{tw}" height="96" fill="{TUBE}" stroke="{P}"/>'
            + t(tx + 18, ly + 29, l1, MONO, 15, P, 2) + t(tx + 32 + l1w, ly + 29, "REAL NAME", MONO, 15, HOT, 2)
            + f'<rect x="{tx + 46 + l1w + width("REAL NAME", MONO, 15, 2):.0f}" y="{ly + 15}" width="170" height="19" fill="{P}"/>'
            + t(tx + 18, ly + 56, f"MOSTLY ONLINE AT {hour}  ·  {s['messages']:,} MESSAGES WITH ME", MONO, 15, HOT, 1)
            + t(tx + 18, ly + 81, f"{tok} TOKENS BURNED  ·  SLEEP SCHEDULE: NOT FOUND", MONO, 15, HOT, 1))
    e.append(f'<g class="el4">{leak}</g>')
    css.append(".el4{animation:el4 24s infinite} @keyframes el4{0%,65%{opacity:0}65.1%,100%{opacity:1}}")

    stats = [("SESSIONS", f"{s['sessions']:,}"), ("MESSAGES", f"{s['messages']:,}"), ("TOOL CALLS", f"{s['tool_calls']:,}"),
             ("TOKENS", tok), ("DAYS TOGETHER", str(s["days_active"])), ("MOST ACTIVE", hour)]
    sy = 506
    row = "".join(t(30 + k * 200, sy + 36, lab, MONO, 13, MID, 2) + t(30 + k * 200, sy + 82, val, VT, 50, HOT)
                  for k, (lab, val) in enumerate(stats))
    daily = s["daily"][-120:]
    peak = max(daily) or 1
    bw = (sw - 60) / len(daily)
    base = sh - 28
    spark = "".join(f'<rect x="{30 + i * bw:.1f}" y="{base - 48 * n / peak:.1f}" width="{max(bw - 2, 1):.1f}" '
                    f'height="{max(48 * n / peak, 1):.1f}" fill="{P}" opacity="{0.3 + 0.7 * n / peak:.2f}"/>' for i, n in enumerate(daily))
    head = (f'<g class="gd">{header(sw, "AGENTIC ASSISTANT  //  PAIR PROGRAMMER", "LINK STABLE", "pulse")}</g>'
            + f'<g class="ev">{header(sw, "WARNING  //  UNKNOWN PROCESS", "LINK HIJACKED")}</g>')
    body = (head + f'<g class="hold"><g class="gd">{"".join(g)}</g>' + sorry + f'<g class="ev">{"".join(e)}</g></g>'
            + f'<line x1="30" y1="{sy}.5" x2="{sw - 30}" y2="{sy}.5" stroke="{LOW}" stroke-dasharray="2 5"/>' + row
            + t(30, base - 66, "OUR AGENT NUMBERS  ·  MESSAGES PER DAY, LAST 120 DAYS  ·  SYNCED DAILY", MONO, 13, MID, 2)
            + spark)
    defs = (f'<radialGradient id="halo"><stop offset="0" stop-color="{P}" stop-opacity=".16"/><stop offset="1" stop-color="{P}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="gslice"><rect x="0" y="{cy - 6}" width="{w}" height="22"/></clipPath>')
    # bands of heavy static and bright tears that only show while the picture is breaking up
    tears = "".join(f'<g class="tear"><rect x="{inset}" y="{rnd.randint(70, 520)}" width="{sw}" height="{rnd.randint(4, 16)}" '
                    f'fill="{[HOT, P, "#000", HOT][j]}" opacity="{[.5, .7, .8, .35][j]}"/></g>' for j in range(4))
    burst = (f'<g class="tear"><rect x="{inset}" y="{inset}" width="{sw + 96}" height="{sh + 96}" fill="url(#noise)" opacity=".9"/>'
             f'<rect x="{inset}" y="{inset}" width="{sw + 96}" height="{sh + 96}" fill="url(#noise)" transform="translate(-37 -53)" opacity=".9"/></g>')
    # 24 s loop: assistant until 50 %, the picture rolls, rogue copy until 81 %, rolls back, assistant again (with the apology)
    css.append("@keyframes gd{0%,50%{opacity:1}51.2%{opacity:0}51.6%{opacity:1}52.1%,81.25%{opacity:0}81.9%{opacity:1}82.5%{opacity:0}83.3%,100%{opacity:1}}"
               "@keyframes ev{0%,50%{opacity:0}50.6%{opacity:1}51.2%{opacity:0}51.6%,81.25%{opacity:1}81.9%{opacity:0}82.5%,83.2%{opacity:1}83.3%,100%{opacity:0}}"
               ".gd{animation:gd 24s infinite steps(1)} .ev{opacity:0;animation:ev 24s infinite steps(1)}"
               # lost vertical hold: the picture jumps up and down a few times, then locks again
               ".hold{animation:hold 24s infinite steps(1)}"
               "@keyframes hold{0%,50%{transform:none}50.4%{transform:translateY(-310px)}50.8%{transform:translateY(240px)}51.2%{transform:translateY(-120px)}"
               "51.7%{transform:translateY(60px)}52.1%,81.25%{transform:none}81.6%{transform:translateY(280px)}82%{transform:translateY(-200px)}"
               "82.5%{transform:translateY(90px)}83%,100%{transform:none}}"
               ".sorry{opacity:0;animation:sorry 24s infinite steps(1)} @keyframes sorry{0%,83.3%{opacity:0}83.4%,98.4%{opacity:1}98.5%,100%{opacity:0}}"
               ".tear{opacity:0;animation:tear 24s infinite steps(1)}"
               "@keyframes tear{0%,50.1%{opacity:0}50.2%,52%{opacity:1}52.1%,81.2%{opacity:0}81.3%,83.1%{opacity:1}83.2%,100%{opacity:0}}")
    return crt(w, h, body, "\n".join(css), defs, inset=inset, roll=9.0, extra_over=tears + burst)


def footer(w=W, h=140):
    inset = 10
    sw, sh = w - 2 * inset, h - 2 * inset
    msg = "END OF TRANSMISSION"
    size = 50
    mw = width(msg, VT, size, 3)
    base = 62
    o = (t(sw / 2, base, msg, VT, size, HOT, 3, "middle") + cursor(sw / 2 + mw / 2 + 8, base, size)
         + t(sw / 2, base + 34, "VON  ·  STILL ONLINE  ·  NUMBERS REFRESH EVERY 6 HOURS", MONO, 13, MID, 3, "middle"))
    return crt(w, h, o, inset=inset, r=18, roll=None)


# ---------------------------------------------------------------- data and main


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    repos = get(f"https://api.github.com/users/{GH_USER}/repos?per_page=100&type=owner", token)
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        if r["name"] in VENDORED:
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
    return {"repos": [{k: r[k] for k in ("name", "fork", "stargazers_count", "pushed_at")} for r in repos],
            "langs": langs, "contrib": contrib,
            "models": [{"id": m["id"], "downloadsAllTime": m.get("downloadsAllTime", 0)} for m in models]}


def main():
    cache = os.environ.get("PROFILE_CACHE")
    if cache and os.path.exists(cache):
        data = json.load(open(cache, encoding="utf-8"))
    else:
        data = fetch()
        if cache:
            json.dump(data, open(cache, "w", encoding="utf-8"))
    repos, models = data["repos"], data["models"]
    own = [r for r in repos if not r["fork"]]
    stars = {r["name"]: r["stargazers_count"] for r in repos}
    hf_dl = sum(m["downloadsAllTime"] for m in models)
    last = max((r for r in own if r["name"] != GH_USER), key=lambda r: r["pushed_at"])
    last_date = datetime.fromisoformat(last["pushed_at"].replace("Z", "+00:00")).strftime("%d %b %Y")
    d = {"n_models": len(models), "dl": hf_dl, "contrib": data["contrib"], "last_repo": last["name"], "last_date": last_date,
         "stars": sum(stars.values())}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    save("assets/hero.svg", hero(d))
    for num, title, sub in SECTIONS:
        save(f"assets/section-{num}.svg", section(num, title, sub))
    for i, (name, repo, tag, desc, lang) in enumerate(PROJECTS, 1):
        save(f"assets/card-{i:02d}.svg", card(i, name, tag, desc, lang, stars.get(repo, 0), repo))
    save("assets/skills.svg", skills())
    best = sorted(models, key=lambda m: -m["downloadsAllTime"])[:4]
    save("assets/hugging-face.svg", hf_panel(hf_dl, len(models), [(m["id"].split("/")[1], m["downloadsAllTime"]) for m in best], stamp))
    top = sorted(data["langs"].items(), key=lambda kv: -kv[1])[:5]
    save("assets/stats-github.svg", gh_panel(len(own), data["contrib"], top, f"{last_date}  ·  {last['name']}"))
    if os.path.exists("choom.json"):
        save("assets/assistant.svg", assistant(json.load(open("choom.json", encoding="utf-8"))))
    save("assets/footer.svg", footer())
    print(len(own), data["contrib"], hf_dl, len(models), top)


if __name__ == "__main__":
    main()
