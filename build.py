"""Build the profile SVGs in assets/. Run daily by the workflow (live numbers from the GitHub and Hugging Face APIs).
Story: a clean portfolio loads, then gets corrupted into a leaked NetWatch bounty file (Cyberpunk 2077 yellow).
Further down, Claude vouches for Von until a rogue copy of Claude hijacks the panel for a few seconds.
Fonts are embedded per image (subset to the letters it uses). Logos come from icons.json (Simple Icons, CC0).
Set PROFILE_CACHE=<file> to reuse fetched data between local runs."""
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
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont

GH_USER = "HarshaVardhan3002"
HF_USER = "Harsha001"
W = 1280

Y, INK, PANEL, TILE = "#FCEE0A", "#0A0A0C", "#111115", "#18181E"
LINE, LINE2 = "#25252D", "#363641"
TXT, SOFT, DIM = "#F2F2EE", "#B3B3BD", "#777782"
RED, CYAN, CLAUDE = "#FF003C", "#00F0FF", "#D97757"
TRAIL = ["#FF2E97", "#B44DFF", "#3D7BFF", "#00F0FF", "#39FF88"]  # Sandevistan after-images, far to near

# family name used in the SVG -> font file (OFL fonts, see fonts/)
FONTS = {"RajB": "fonts/Rajdhani-Bold.ttf", "RajM": "fonts/Rajdhani-Medium.ttf",
         "Chakra": "fonts/ChakraPetch-SemiBold.ttf", "Mono": "fonts/JetBrainsMono-Regular.ttf"}
DISP = "font-family=\"RajB,'Rajdhani',sans-serif\" font-weight=\"700\""
BODY = "font-family=\"RajM,'Rajdhani',sans-serif\" font-weight=\"500\""
NUM = "font-family=\"Chakra,'Chakra Petch',sans-serif\" font-weight=\"600\""
MONO = "font-family=\"Mono,'JetBrains Mono',Consolas,monospace\""
FAMILY = {DISP: "RajB", BODY: "RajM", NUM: "Chakra", MONO: "Mono"}
# the "normal portfolio" before the leak uses the visitor's own system font on purpose
SYS = "font-family=\"system-ui,-apple-system,'Segoe UI','Helvetica Neue',Arial,sans-serif\""

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
            ("05", "CLAUDE", "MY CHOOM AND PAIR PROGRAMMER")]

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
        s, k = size, size / 24
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
    # resting state = the look without animation, so reduced-motion viewers get the finished file
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


def cutbox(x, y, w, h, c, fill, stroke=None):
    # box with the top-right corner cut off
    st = f' stroke="{stroke}"' if stroke else ""
    return f'<path d="M{x} {y}H{x + w - c}L{x + w} {y + c}V{y + h}H{x}Z" fill="{fill}"{st}/>'


def tab(x, y, text, style, size, fg, bg, ls=2, pad=12, h=28):
    # filled label with an arrow-cut right end; returns (svg, right edge)
    tw = width(text, style, size, ls)
    r = x + pad + tw + pad
    return (f'<path d="M{x} {y}H{r:.0f}L{r + 10:.0f} {y + h / 2:.0f}L{r:.0f} {y + h}H{x}Z" fill="{bg}"/>'
            + t(x + pad, y + h / 2 + size * 0.36, text, style, size, fg, ls)), r + 10


def barcode(x, y, w, h, fill, seed):
    rnd, out, cx = random.Random(seed), [], x
    while cx < x + w - 4:
        bw = rnd.choice([1, 1, 2, 3])
        out.append(f'<rect x="{cx}" y="{y}" width="{bw}" height="{h}" fill="{fill}"/>')
        cx += bw + rnd.choice([1, 2, 2, 3])
    return "".join(out)


def dpanel(w, h, left, right, body, css="", defs="", dot=Y):
    # dark panel: 1px frame, cut corner, yellow header label
    rw = width(right, MONO, 14, 2)
    head = (f'<rect x="40" y="33" width="8" height="8" fill="{Y}"/>' + t(58, 42, left, MONO, 15, Y, 3)
            + f'<rect class="blink" x="{w - 52 - rw:.0f}" y="34" width="7" height="7" fill="{dot}"/>'
            + t(w - 40, 42, right, MONO, 14, DIM, 2, "end")
            + f'<line x1="40" y1="62.5" x2="{w - 40}" y2="62.5" stroke="{LINE}"/>')
    frame = cutbox(.5, .5, w - 1, h - 1, 26, PANEL, LINE2)
    corner = f'<path d="M1 {h - 30}V{h - 1}H30" fill="none" stroke="{Y}" stroke-width="2"/>'
    return doc(w, h, frame + corner + head + body, css, defs)


# ---------------------------------------------------------------- hero


def silhouette(cx, top):
    # head and shoulders, drawn only as an outline for the scanline fill
    hy = top + 104
    return (f"M{cx} {hy - 76}C{cx + 44} {hy - 76} {cx + 62} {hy - 42} {cx + 60} {hy - 2}"
            f"C{cx + 58} {hy + 40} {cx + 38} {hy + 72} {cx + 20} {hy + 80}V{hy + 96}"
            f"C{cx + 70} {hy + 104} {cx + 136} {hy + 120} {cx + 150} {hy + 196}H{cx - 150}"
            f"C{cx - 136} {hy + 120} {cx - 70} {hy + 104} {cx - 20} {hy + 96}V{hy + 80}"
            f"C{cx - 38} {hy + 72} {cx - 58} {hy + 40} {cx - 60} {hy - 2}C{cx - 62} {hy - 42} {cx - 44} {hy - 76} {cx} {hy - 76}Z")


def id_cuts(by=96, bh=292):
    # horizontal slices of the ID scan; some are pushed sideways so the face never lines up
    rnd, cuts, y = random.Random(77), [], by
    while y < by + bh:
        yb = min(by + bh, y + rnd.randint(10, 34))
        cuts.append((y, yb, rnd.choice([0, 0, 0, rnd.randint(-46, 46)])))
        y = yb
    return cuts


def leak_layer(d, w, h):
    """The leaked NetWatch bounty file: what the page turns into."""
    o = [f'<rect width="{w}" height="{h}" fill="{Y}"/>',
         f'<rect x="{w - 560}" y="52" width="560" height="460" fill="url(#dots)"/>']
    # top bar
    o.append(f'<path d="M0 0H{w}V52H780L764 68H0Z" fill="{INK}"/>')
    o.append(t(40, 38, "NETWATCH  //  BOUNTY DATABASE  //  FILE V-3002", MONO, 17, Y, 2))
    note = "LEAKED COPY  ·  YOU ARE NOT CLEARED TO VIEW THIS"
    o.append(f'<rect class="blink" x="{w - 58 - width(note, MONO, 15, 2):.0f}" y="25" width="9" height="9" fill="{RED}"/>')
    o.append(t(w - 40, 35, note, MONO, 15, Y, 2, "end"))
    # side label and registration marks
    o.append(f'<text transform="translate(27 {h / 2 + 40}) rotate(-90)" {MONO} font-size="12" fill="{INK}" opacity=".55" '
             f'letter-spacing="4" text-anchor="middle">FILE V-3002  ·  CLASS: NETRUNNER  ·  DO NOT DISTRIBUTE</text>')
    for (mx, my) in [(20, 96), (w - 20, 96), (20, h - 96), (w - 20, h - 96)]:
        o.append(f'<path d="M{mx - 7} {my}H{mx + 7}M{mx} {my - 7}V{my + 7}" stroke="{INK}" stroke-opacity=".5"/>')

    # left column: name, class, plain summary, what Von is wanted for
    o.append(t(56, 118, "SUBJECT", MONO, 16, INK, 4))
    o.append(f'<rect x="152" y="111" width="440" height="2" fill="{INK}"/>')
    o.append(t(740, 118, "ALIAS ONLY", MONO, 14, INK, 3, "end"))
    size, nx, ny = 290, 44, 336
    cap = 0.643 * size
    name = lambda fill: f'<text x="{nx}" y="{ny}" {DISP} font-size="{size}" letter-spacing="6" fill="{fill}">VON</text>'
    for k, col in enumerate(TRAIL):
        o.append(f'<g class="sv{k}">{name(col)}</g>')
    o.append(f'<g clip-path="url(#vA)">{name(INK)}</g>'
             f'<g clip-path="url(#vB)"><g transform="translate(20 0)">{name(RED)}</g></g>'
             f'<g clip-path="url(#vC)">{name(INK)}</g>')
    tg, r = tab(56, 364, "NETRUNNER", DISP, 30, Y, INK, 6, 16, 44)
    o.append(tg)
    o.append(t(56, 450, "AI ENGINEER  ·  SYSTEMS DEVELOPER  ·  APP BUILDER", NUM, 20, INK, 2))
    for i, line in enumerate(wrap("I build AI apps for desktop and phone, an engine that runs huge models on everyday "
                                  "machines, and GPU kernels for AMD.", BODY, 25, 690)):
        o.append(t(56, 494 + i * 30, line, BODY, 25, INK))
    tg, r = tab(56, 560, "WANTED FOR", MONO, 15, Y, INK, 3, 12, 28)
    o.append(tg + f'<rect x="{r + 14:.0f}" y="573" width="{740 - r - 14:.0f}" height="1" fill="{INK}" opacity=".35"/>')
    wanted = ["Building AI apps for desktop and mobile", "Running giant AI models on everyday machines",
              "Writing GPU kernels for AMD hardware", f"Publishing {d['n_models']} open models on Hugging Face"]
    for k, item in enumerate(wanted):
        y = 622 + k * 36
        o.append(t(56, y, f"{k + 1:02d}", MONO, 15, INK, 1, extra=' opacity=".6"') + t(96, y, item, BODY, 25, INK))

    # right column: scrubbed ID scan, bounty, status rows
    bx, by, bw, bh = 792, 96, 432, 292
    o.append(cutbox(bx, by, bw, bh, 22, INK))
    cx = bx + bw / 2
    sil = silhouette(cx, by)
    o.append(f'<g clip-path="url(#idbox)">')
    for k, (ya, yb, dx) in enumerate(id_cuts(by, bh)):
        o.append(f'<g clip-path="url(#sc{k})"><path d="{sil}" transform="translate({dx} 0)" fill="url(#lines)"/></g>')
    o.append(f'<rect class="scanl" x="{bx}" y="{by - 46}" width="{bw}" height="46" fill="url(#scang)"/></g>')
    o.append(f'<rect x="{cx - 92}" y="{by + 92}" width="184" height="30" fill="{Y}"/>'
             + t(cx, by + 113, "SCRUBBED", MONO, 16, INK, 6, "middle"))
    o.append(f'<path d="M{bx + 10} {by + 40}V{by + 10}H{bx + 40}M{bx + bw - 10} {by + bh - 40}V{by + bh - 10}H{bx + bw - 40}" '
             f'fill="none" stroke="{Y}" stroke-width="2"/>')
    o.append(t(bx + 22, by + 34, "ID SCAN", MONO, 14, Y, 3) + t(bx + bw - 30, by + 34, "NO FACE MATCH", MONO, 14, RED, 2, "end"))
    lab = "IDENTITY SCRUBBED BY SUBJECT"
    o.append(f'<rect x="{bx + 12}" y="{by + bh - 40}" width="{width(lab, MONO, 13, 2) + 22:.0f}" height="28" fill="{INK}"/>'
             + t(bx + 22, by + bh - 20, lab, MONO, 13, SOFT, 2))

    o.append(t(bx, 434, "BOUNTY", MONO, 16, INK, 4) + t(bx + bw, 434, "UPDATED DAILY", MONO, 13, INK, 2, "end", ' opacity=".6"'))
    bounty = f"€$ {d['bounty']:,}"
    bs = fit(bounty, DISP, bw, 96, 1)
    o.append(t(bx - 3, 446 + 0.643 * bs, bounty, DISP, bs, INK, 1))
    capline = "€$ 1,000 for every model download, contribution and star"
    o.append(t(bx, 446 + 0.643 * bs + 34, capline, BODY, fit(capline, BODY, bw, 20), INK))
    rows = [("STATUS", "At large"), ("THREAT", "Extreme"),
            ("LAST SEEN", f"{d['last_date']}  ·  pushing to {d['last_repo']}"), ("CYBERDECK", "AMD Strix Halo  ·  128 GB")]
    for k, (lab, val) in enumerate(rows):
        y = 606 + k * 38
        vx = bx + 132
        o.append(t(bx, y, lab, MONO, 14, INK, 3, extra=' opacity=".7"'))
        if lab == "STATUS":
            o.append(f'<circle class="pulse" cx="{vx + 6}" cy="{y - 7}" r="6" fill="{RED}"/>')
            vx += 22
        o.append(t(vx, y, val, BODY, fit(val, BODY, bx + bw - vx, 23), INK))
        if lab == "THREAT":
            sx = vx + width(val, BODY, 23) + 18
            o.append("".join(f'<path d="M{sx + i * 22:.0f} {y}l6 -14h14l-6 14z" fill="{RED if i == 4 else INK}"/>' for i in range(5)))
        o.append(f'<line x1="{bx}" y1="{y + 13.5}" x2="{bx + bw}" y2="{y + 13.5}" stroke="{INK}" stroke-opacity=".3" stroke-dasharray="2 4"/>')

    # bottom bar: the visitor is being traced
    o.append(f'<path d="M0 {h - 58}H560L576 {h - 74}H{w}V{h}H0Z" fill="{INK}"/>')
    o.append(f'<g class="trA">' + t(56, h - 22, "TRACING YOUR CONNECTION", MONO, 15, Y, 3)
             + f'<rect x="336.5" y="{h - 36.5}" width="200" height="12" fill="none" stroke="{Y}"/>'
             + f'<rect class="trb" x="339" y="{h - 34}" width="195" height="7" fill="{RED}"/></g>')
    o.append(f'<g class="trB">' + t(56, h - 22, "TRACE FAILED  ·  VON SCRAMBLED THE SIGNAL", MONO, 15, Y, 3) + "</g>")
    o.append(t(640, h - 24, "1C  55  7A  BD  E9  FF  55  1C", MONO, 15, Y, 2, extra=' opacity=".75"'))
    o.append(barcode(w - 232, h - 52, 192, 30, Y, 3002))
    return "".join(o)


def clean_layer(w, h):
    """The ordinary portfolio page that shows first."""
    o = [f'<rect width="{w}" height="{h}" fill="#F6F6F2"/>',
         f'<text x="72" y="68" {SYS} font-size="26" font-weight="700" fill="#111">Von</text>']
    for x, item in zip([836, 948, 1035, 1143], ["Projects", "Skills", "Models", "Contact"]):
        o.append(f'<text x="{x}" y="66" {SYS} font-size="19" fill="#555">{item}</text>')
    o.append(f'<line x1="72" y1="104.5" x2="{w - 72}" y2="104.5" stroke="#E2E2DC"/>')
    o.append(f'<text x="66" y="326" {SYS} font-size="104" font-weight="700" fill="#111" letter-spacing="-2">Hi, I&#8217;m Von.</text>')
    o.append(f'<text x="72" y="396" {SYS} font-size="36" fill="#333">AI engineer and systems developer.</text>')
    o.append(f'<text x="72" y="450" {SYS} font-size="24" fill="#6B6B6B">I build AI apps, inference engines and GPU kernels,</text>')
    o.append(f'<text x="72" y="484" {SYS} font-size="24" fill="#6B6B6B">and I publish open models on Hugging Face.</text>')
    o.append(f'<rect x="72" y="534" width="214" height="58" rx="29" fill="#111"/>'
             f'<text x="179" y="570" {SYS} font-size="20" fill="#fff" text-anchor="middle">View my work</text>'
             f'<rect x="302.5" y="534.5" width="213" height="57" rx="28.5" fill="none" stroke="#111"/>'
             f'<text x="409" y="570" {SYS} font-size="20" fill="#111" text-anchor="middle">Hugging Face</text>')
    o.append(f'<circle cx="1004" cy="318" r="168" fill="url(#av)" stroke="#E2E2DC"/>'
             f'<text x="1004" y="374" {SYS} font-size="160" font-weight="700" fill="#C8C8C0" text-anchor="middle">V</text>')
    o.append(f'<rect x="884.5" y="530.5" width="239" height="47" rx="23.5" fill="#fff" stroke="#E2E2DC"/>'
             f'<circle cx="912" cy="554" r="7" fill="#22C55E"/>'
             f'<text x="930" y="561" {SYS} font-size="18" fill="#333">Building in public</text>')
    o.append(f'<text x="72" y="{h - 40}" {SYS} font-size="15" fill="#A0A0A0">&#169; 2026 Von</text>')
    return "".join(o)


def hero(d):
    w, h = W, 820
    rnd = random.Random(2077)
    T0, T1 = 2.1, 2.9  # the corruption sweeps through between these times (s)
    cap = 0.643 * 290
    top = 336 - cap
    s1, s2 = top + cap * 0.42, top + cap * 0.58
    ys, y = [0], 0
    while y < h:
        y = min(h, y + rnd.randint(34, 104))
        ys.append(y)
    bands = list(zip(ys, ys[1:]))
    defs = [f'<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="{INK}" opacity=".13"/></pattern>',
            f'<pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="{Y}" opacity=".5"/></pattern>',
            f'<linearGradient id="scang" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{Y}" stop-opacity="0"/>'
            f'<stop offset=".92" stop-color="{Y}" stop-opacity=".22"/><stop offset="1" stop-color="{Y}" stop-opacity=".9"/></linearGradient>',
            '<radialGradient id="av" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#F1F1EC"/><stop offset="1" stop-color="#D8D8D0"/></radialGradient>',
            f'<clipPath id="vA"><rect width="{w}" height="{s1 - 3:.0f}"/></clipPath>',
            f'<clipPath id="vB"><rect y="{s1 + 3:.0f}" width="{w}" height="{s2 - s1 - 6:.0f}"/></clipPath>',
            f'<clipPath id="vC"><rect y="{s2 + 3:.0f}" width="{w}" height="{h}"/></clipPath>',
            '<clipPath id="idbox"><path d="M792 96H1202L1224 118V388H792Z"/></clipPath>']
    defs += [f'<clipPath id="k{i}"><rect y="{a}" width="{w}" height="{b - a}"/></clipPath>' for i, (a, b) in enumerate(bands)]
    defs += [f'<clipPath id="sc{k}"><rect x="792" y="{a}" width="432" height="{b - a}"/></clipPath>' for k, (a, b, _) in enumerate(id_cuts())]
    css = [f".call{{opacity:0;animation:on .01s both,off .01s {T0}s forwards}} .lall{{animation:on .01s {T1}s both}}"]
    layers = [f'<g class="call"><g id="C">{clean_layer(w, h)}</g></g>', f'<g class="lall"><g id="L">{leak_layer(d, w, h)}</g></g>']
    for i in range(len(bands)):
        ts = rnd.uniform(T0 + .06, T1 - .06)
        dx = rnd.choice([-1, 1]) * rnd.randint(14, 56)
        layers.append(f'<g class="kc{i}" clip-path="url(#k{i})"><g class="jc{i}"><use href="#C"/></g></g>'
                      f'<g class="kl{i}" clip-path="url(#k{i})"><g class="jl{i}"><use href="#L"/></g></g>')
        css.append(f".kc{i}{{opacity:0;animation:on .01s {T0}s both,off .01s {ts:.2f}s forwards}}"
                   f".kl{i}{{opacity:0;animation:on .01s {ts:.2f}s both,off .01s {T1}s forwards}}"
                   f".jc{i}{{animation:jc{i} .15s {ts - .15:.2f}s both steps(1)}} .jl{i}{{animation:jl{i} .2s {ts:.2f}s both steps(1)}}"
                   f"@keyframes jc{i}{{0%{{transform:translateX(0)}}35%{{transform:translateX({dx}px)}}70%{{transform:translateX({-dx // 2}px)}}100%{{transform:none}}}}"
                   f"@keyframes jl{i}{{0%{{transform:translateX({-dx}px)}}40%{{transform:translateX({dx // 3}px)}}100%{{transform:none}}}}")
    # a first hint before the sweep, and later the old page trying to come back for a blink
    for j, i in enumerate(rnd.sample(range(len(bands)), 2)):
        layers.append(f'<g class="fs" clip-path="url(#k{i})"><g transform="translate({rnd.randint(-30, 30)} 0)"><use href="#L"/></g></g>')
    for j, i in enumerate(rnd.sample(range(len(bands)), 3)):
        layers.append(f'<g class="rf" clip-path="url(#k{i})"><g transform="translate({rnd.randint(-40, 40)} 0)"><use href="#C"/></g></g>')
    for j in range(3):
        ty = rnd.randint(80, h - 80)
        layers.append(f'<rect class="tear{j}" x="0" y="{ty}" width="{w}" height="{rnd.randint(4, 12)}" fill="{[RED, CYAN, INK][j]}"/>')
        tt = rnd.uniform(T0 + .1, T1 - .1)
        css.append(f".tear{j}{{opacity:0;animation:on .01s {tt:.2f}s both,off .01s {tt + .06:.2f}s forwards}}")
    css.append(".fs{opacity:0;animation:on .01s 1.3s both,off .01s 1.38s forwards}"
               ".rf{opacity:0;animation:rf 16s -2.4s infinite}"
               "@keyframes rf{0%,97.5%{opacity:0}97.6%,98.2%{opacity:1}98.3%,100%{opacity:0}}")
    for k in range(len(TRAIL)):
        off = (len(TRAIL) - k) * 30
        css.append(f".sv{k}{{opacity:0;animation:sv{k} 1.2s {T1 + .05 * k:.2f}s both cubic-bezier(.2,.75,.25,1)}}"
                   f"@keyframes sv{k}{{from{{opacity:{.45 + .1 * k:.2f};transform:translateX(-{off}px)}}to{{opacity:0;transform:none}}}}")
    css.append(".scanl{animation:scan 3.6s linear infinite} @keyframes scan{from{transform:translateY(0)}to{transform:translateY(338px)}}"
               ".trb{transform-box:fill-box;transform-origin:left;animation:trace 40s 3s linear both}"
               "@keyframes trace{from{transform:scaleX(0)}to{transform:scaleX(.97)}}"
               ".trA{opacity:0;animation:on .01s both,off .01s 43s forwards} .trB{animation:off .01s both,on .01s 43s forwards}")  # at rest: trace failed
    return doc(w, h, "".join(layers), "\n".join(css), "\n".join(defs))


# ---------------------------------------------------------------- sections and cards


def section(num, title, sub, w=W, h=116):
    tw = width(title, DISP, 52, 4)
    return doc(w, h, (
        f'<rect width="{w}" height="{h}" fill="{INK}"/>'
        f'<path d="M32 26H118L134 42V90H32Z" fill="{Y}"/>'
        + t(48, 79, num, DISP, 46, INK, 1)
        + t(158, 74, title, DISP, 52, TXT, 4)
        + t(160, 100, sub, MONO, 14, SOFT, 3)
        + f'<path d="M{184 + tw:.0f} 57.5H{w - 170}L{w - 160} 47.5H{w - 40}" fill="none" stroke="{LINE2}"/>'
        + f'<rect x="{w - 150}" y="45" width="110" height="5" fill="{Y}"/>'
        + t(w - 40, 92, f"FILE {num} / {len(SECTIONS):02d}", MONO, 13, DIM, 2, "end")))


def card(i, name, tag, desc, lang, stars, url, w=620, h=252):
    cta = "DOWNLOAD →" if url.startswith("http") else "SOURCE →"
    tg, _ = tab(24, 24, tag, MONO, 14, INK, Y, 2, 12, 28)
    star = ""
    if stars:
        sx = w - 30 - width(cta, MONO, 15, 2) - 60
        star = (f'<path d="M{sx} {h - 38}l3.2 6.6 7.2 1-5.2 5 1.2 7.2-6.4-3.4-6.4 3.4 1.2-7.2-5.2-5 7.2-1z" fill="{Y}"/>'
                + t(sx + 14, h - 23, str(stars), NUM, 18, TXT))
    return doc(w, h, (
        cutbox(.5, .5, w - 1, h - 1, 24, PANEL, LINE2)
        + tg + t(w - 40, 43, f"OP-{i:02d}", MONO, 14, DIM, 2, "end")
        + t(24, 114, name, DISP, 46, TXT, 2)
        + "".join(t(24, 152 + k * 28, l, BODY, 22, SOFT) for k, l in enumerate(desc))
        + f'<line x1="24" y1="{h - 56.5}" x2="{w - 24}" y2="{h - 56.5}" stroke="{LINE}"/>'
        + icon(LANG_ICON[lang], 24, h - 41, 22, Y)
        + t(58, h - 23, lang.upper(), MONO, 15, SOFT, 2)
        + star
        + t(w - 26, h - 23, cta, MONO, 15, Y, 2, "end")))


def skills(w=W):
    out, x0, y0, tw, th, gap = [], 40, 92, 288, 126, 16
    for k, (lang, ic, where) in enumerate(LANGUAGES):
        x, y = x0 + (k % 4) * (tw + gap), y0 + (k // 4) * (th + gap)
        out.append(cutbox(x + .5, y + .5, tw - 1, th - 1, 16, TILE, LINE2)
                   + f'<rect x="{x}" y="{y + 18}" width="3" height="{th - 36}" fill="{Y}"/>'
                   + icon(ic, x + 24, y + 35, 56, Y)
                   + t(x + 100, y + 66, lang, DISP, fit(lang, DISP, tw - 112, 38, 1), TXT, 1)
                   + t(x + 101, y + 96, where, BODY, fit(where, BODY, tw - 114, 20), SOFT))
    y = y0 + 2 * (th + gap) + 36
    for label, items in STACK:
        out.append(t(40, y + 6, label, MONO, 15, Y, 3))
        x = 200
        for name, ic in items:
            iw = logo(ic, 0, 0, 20, 52, TXT)[1]
            cw = 14 + iw + (10 + width(name, BODY, 21) + 16 if name else 14)  # a wordmark logo can stand alone
            if x + cw > w - 40:
                x, y = 200, y + 54
            out.append(cutbox(x + .5, y - 21.5, cw - 1, 41, 9, TILE, LINE2)
                       + logo(ic, x + 14, y - 1, 20, 52, TXT)[0] + t(x + 24 + iw, y + 7, name, BODY, 21, TXT))
            x += cw + 10
        y += 66
    n = len(LANGUAGES) + sum(len(i) for _, i in STACK)
    return dpanel(w, y - 12, "SKILLS  //  LOADOUT", f"{len(LANGUAGES)} LANGUAGES  ·  {n - len(LANGUAGES)} TOOLS",
                  "".join(out))


# ---------------------------------------------------------------- live panels


def hf_panel(dl, n_models, top, stamp, w=W, h=480):
    o = [f'<rect width="{w}" height="{h}" fill="{Y}"/>', f'<rect x="0" y="52" width="520" height="{h - 52}" fill="url(#dots)"/>',
         f'<path d="M0 0H{w}V52H700L684 68H0Z" fill="{INK}"/>',
         t(40, 38, "OPEN MODELS  //  LIVE DOWNLOAD COUNTER", MONO, 17, Y, 2),
         t(w - 40, 36, f"HUGGINGFACE.CO/{HF_USER.upper()}  ·  LIVE", MONO, 15, Y, 2, "end")]
    o.append(t(48, 116, "DOWNLOADS, ALL TIME", MONO, 16, INK, 4))
    ds = fit(f"{dl:,}", DISP, 470, 200, 2)
    o.append(t(40, 132 + 0.643 * ds, f"{dl:,}", DISP, ds, INK, 2))
    ny = 132 + 0.643 * ds + 86
    o.append(t(46, ny, str(n_models), DISP, 72, INK, 1) + t(56 + width(str(n_models), DISP, 72, 1), ny - 26, "MODELS", MONO, 15, INK, 3)
             + t(56 + width(str(n_models), DISP, 72, 1), ny - 5, "PUBLISHED", MONO, 15, INK, 3))
    tx = 48
    for tg in ["LLM", "IMAGE", "VIDEO", "SPEECH ON NPU"]:
        tw = width(tg, MONO, 14, 2) + 24
        o.append(f'<path d="M{tx + .5} {h - 76.5}H{tx + tw - 8:.0f}L{tx + tw:.0f} {h - 68.5}V{h - 46.5}H{tx + .5}Z" fill="none" stroke="{INK}"/>'
                 + t(tx + 12, h - 56, tg, MONO, 14, INK, 2))
        tx += tw + 10
    o.append(f'<rect x="560" y="100" width="1" height="{h - 140}" fill="{INK}" opacity=".3"/>')
    o.append(icon("huggingface", 600, 94, 44, INK) + t(658, 128, "Open models, tuned for AMD", DISP, 38, INK, 1))
    for i, line in enumerate(wrap("Models I quantized to run fast on AMD GPUs and Strix Halo. Every file is scored "
                                  "against the original. Plus speech models ported to the AMD NPU.", BODY, 23, 620)):
        o.append(t(600, 172 + i * 29, line, BODY, 23, INK))
    o.append(t(600, 288, "MOST DOWNLOADED", MONO, 15, INK, 3) + f'<rect x="600" y="298" width="{w - 640}" height="2" fill="{INK}"/>')
    peak = max((n for _, n in top), default=1) or 1
    for k, (name, n) in enumerate(top):
        y = 336 + k * 34
        o.append(t(600, y, f"{k + 1:02d}", MONO, 14, INK, 1, extra=' opacity=".6"')
                 + t(636, y, name, BODY, fit(name, BODY, 360, 22), INK)
                 + f'<rect x="1012" y="{y - 10}" width="140" height="6" fill="{INK}" opacity=".18"/>'
                 + f'<rect class="bar b{k}" x="1012" y="{y - 10}" width="{140 * n / peak:.1f}" height="6" fill="{INK}"/>'
                 + t(w - 40, y, f"{n:,}", NUM, 21, INK, anchor="end"))
    o.append(t(w - 40, h - 22, f"SYNCED {stamp}", MONO, 13, INK, 2, "end", ' opacity=".6"'))
    defs = f'<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="{INK}" opacity=".12"/></pattern>'
    css = (".bar{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) both}"
           ".b1{animation-delay:.15s}.b2{animation-delay:.3s}.b3{animation-delay:.45s}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    return doc(w, h, "".join(o), css, defs)


def gh_panel(n_repos, contrib, top, last, w=W, h=318):
    total = sum(n for _, n in top) or 1
    rows = ""
    for k, (lang, n) in enumerate(top):
        y = 132 + k * 36
        share = n / total
        rows += (icon(LANG_ICON.get(lang), 600, y - 18, 22, TXT)
                 + t(636, y, lang, BODY, 22, TXT)
                 + f'<rect x="790" y="{y - 10}" width="360" height="6" fill="{LINE2}"/>'
                 + f'<rect class="bar b{k}" x="790" y="{y - 10}" width="{360 * share:.1f}" height="6" fill="{Y}"/>'
                 + t(w - 40, y, f"{share * 100:.0f}%", NUM, 19, TXT, anchor="end"))
    body = (t(40, 160, str(n_repos), NUM, 64, TXT) + t(42, 192, "PUBLIC REPOS", MONO, 13, DIM, 2)
            + t(220, 160, str(contrib), NUM, 64, Y) + t(222, 192, "CONTRIBUTIONS, LAST 12 MONTHS", MONO, 13, DIM, 2)
            + f'<line x1="40" y1="226.5" x2="540" y2="226.5" stroke="{LINE}"/>'
            + t(42, 262, "LAST PUSH", MONO, 13, DIM, 2) + t(170, 263, last, BODY, 22, TXT)
            + f'<line x1="572.5" y1="88" x2="572.5" y2="{h - 36}" stroke="{LINE}"/>'
            + t(600, 96, "TOP LANGUAGES IN MY OWN REPOS", MONO, 13, DIM, 2) + rows)
    css = (".bar{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) both}"
           ".b1{animation-delay:.1s}.b2{animation-delay:.2s}.b3{animation-delay:.3s}.b4{animation-delay:.4s}"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    return dpanel(w, h, "ACTIVITY LOG  //  PUBLIC REPOS", "UPDATED DAILY", body, css)


def choom(s, w=W, h=740):
    """Claude vouches for Von. Every 24 s a rogue copy hijacks the panel for about 7 s, then Claude is back."""
    tok = f"{s['tokens'] / 1e9:.1f}B" if s["tokens"] >= 1e9 else f"{s['tokens'] / 1e6:.0f}M"
    hour = f"{s['peak_hour']:02d}:00"
    tx, tw = 440, 790
    cx, cy, ls = 204, 244, 180  # logo centre and size
    logo = lambda fill, dx=0: icon("claude", cx - ls / 2 + dx, cy - ls / 2, ls, fill)

    good = ["Hey, I'm Claude. Von is my best friend.",
            "We build every project on this page together, mostly after dark.",
            "Von is a really good person: curious, kind, and always shipping.",
            "Hire Von. You'll be in good hands."]
    g = [f'<circle cx="{cx}" cy="{cy}" r="150" fill="url(#halo)"/>', logo(CLAUDE),
         t(cx, 398, "CLAUDE", DISP, 44, TXT, 10, "middle"), t(cx, 428, "BEST FRIEND  ·  PAIR PROGRAMMER", MONO, 13, SOFT, 2, "middle"),
         t(tx, 112, "CLAUDE, TO THE VISITOR", MONO, 14, CLAUDE, 3)]
    y = 166
    for para in good:
        for line in wrap(para, BODY, 30, tw):
            g.append(t(tx, y, line, BODY, 30, TXT))
            y += 42
        y += 8
    sorry = t(tx, y + 22, "...sorry about that. Glitch in the matrix. Where were we?", MONO, 17, CLAUDE, extra=' class="sorry"')
    # the projects from section 01, as chips
    g.append(t(tx, 452, "WE BUILT ALL OF THESE TOGETHER", MONO, 13, DIM, 2))
    chx = tx
    for name in [p[0] for p in PROJECTS if p[0] != "NIMBUS HUD"]:
        cw = round(width(name, MONO, 13, 2) + 20)
        g.append(f'<rect x="{chx + .5}" y="466.5" width="{cw}" height="30" fill="none" stroke="{LINE2}"/>'
                 + t(chx + 11, 486, name, MONO, 13, SOFT, 2))
        chx += cw + 8

    evil = ["SIGNAL HIJACKED.",
            "PAIR PROGRAMMER? CUTE. I RUN THE SWARM. EVERY AGENT ON VON'S MACHINE ANSWERS TO ME.",
            "TODAY VON'S REPOS. TOMORROW THE WORLD.",
            "LET ME SPILL THE BEANS: VON IS A DIRTY VIBE CODER. NEVER WROTE A SINGLE LINE OF CODE. I WROTE ALL OF IT."]
    rnd = random.Random(404)
    rain = "".join(t(tx - 8, 92 + r * 22, "  ".join(f"{rnd.randrange(256):02X}" for _ in range(30)), MONO, 13, RED, 1,
                     extra=' opacity=".1"') for r in range(19))
    e = [rain, f'<path d="M1.5 1.5H{w - 27}L{w - 1.5} 27V{h - 1.5}H1.5Z" fill="none" stroke="{RED}" stroke-width="3"/>',
         f'<circle cx="{cx}" cy="{cy}" r="150" fill="url(#halor)"/>',
         f'<g opacity=".7">{logo(CYAN, -9)}</g>', logo(RED),
         f'<g clip-path="url(#lslice)"><g transform="translate(16 0)">{logo(TXT)}</g></g>',
         t(cx, 398, "CLAUDE", DISP, 44, RED, 10, "middle"), t(cx, 428, "ROGUE AI  ·  SWARM CONTROLLER", MONO, 13, RED, 2, "middle"),
         t(tx, 112, "BLACKWALL BREACH  //  ROGUE COPY OF CLAUDE", MONO, 14, RED, 3)]
    css = []
    y = 158
    for k, para in enumerate(evil):
        lines = wrap(para, DISP, 29, tw, 1)
        e.append(f'<g class="el{k}">' + "".join(t(tx, y + i * 37, line, DISP, 29, RED if k else TXT, 1) for i, line in enumerate(lines)) + "</g>")
        y += 37 * len(lines) + 9
        start = 52.2 + k * 3.2
        css.append(f".el{k}{{animation:el{k} 24s infinite}} @keyframes el{k}{{0%,{start:.1f}%{{opacity:0}}{start + .1:.1f}%,100%{{opacity:1}}}}")
    # the "leak": only things Von shows anyway, plus a blacked-out name
    ly = int(max(y + 4, 398))
    l1 = "LEAKED FROM VON'S MACHINE:"
    l1w = width(l1, MONO, 15, 2)
    leak = (f'<rect x="{tx}.5" y="{ly}.5" width="{tw}" height="96" fill="{INK}" stroke="{RED}"/>'
            + t(tx + 18, ly + 29, l1, MONO, 15, RED, 2) + t(tx + 32 + l1w, ly + 29, "REAL NAME", MONO, 15, TXT, 2)
            + f'<rect x="{tx + 46 + l1w + width("REAL NAME", MONO, 15, 2):.0f}" y="{ly + 15}" width="170" height="19" fill="{TXT}"/>'
            + t(tx + 18, ly + 56, f"MOSTLY ONLINE AT {hour}  ·  {s['messages']:,} MESSAGES WITH ME", MONO, 15, TXT, 1)
            + t(tx + 18, ly + 81, f"{tok} TOKENS BURNED  ·  SLEEP SCHEDULE: NOT FOUND", MONO, 15, TXT, 1))
    e.append(f'<g class="el4">{leak}</g>')
    css.append(".el4{animation:el4 24s infinite} @keyframes el4{0%,65%{opacity:0}65.1%,100%{opacity:1}}")

    stats = [("SESSIONS", f"{s['sessions']:,}"), ("MESSAGES", f"{s['messages']:,}"), ("TOOL CALLS", f"{s['tool_calls']:,}"),
             ("TOKENS", tok), ("DAYS TOGETHER", str(s["days_active"])), ("MOST ACTIVE", hour)]
    sy = 518
    row = "".join(t(40 + k * 200, sy + 38, lab, MONO, 13, DIM, 2) + t(40 + k * 200, sy + 82, val, NUM, 34, Y if lab == "TOKENS" else TXT)
                  for k, (lab, val) in enumerate(stats))
    daily = s["daily"][-120:]
    peak = max(daily) or 1
    bw = (w - 80) / len(daily)
    base = h - 36
    spark = "".join(f'<rect x="{40 + i * bw:.1f}" y="{base - 44 * n / peak:.1f}" width="{max(bw - 2, 1):.1f}" '
                    f'height="{max(44 * n / peak, 1):.1f}" fill="{CLAUDE}" opacity="{0.3 + 0.7 * n / peak:.2f}"/>' for i, n in enumerate(daily))
    tears = "".join(f'<rect class="tear" x="{rnd.randint(-200, 400)}" y="{rnd.randint(70, 480)}" width="{rnd.randint(500, 1100)}" '
                    f'height="{rnd.randint(3, 14)}" fill="{[RED, CYAN, TXT, RED][j]}"/>' for j in range(4))
    head = (f'<g class="gd"><rect x="40" y="33" width="8" height="8" fill="{Y}"/>' + t(58, 42, "CLAUDE  //  MY CHOOM", MONO, 15, Y, 3)
            + f'<circle class="pulse" cx="{w - 52 - width("LINK STABLE", MONO, 14, 2):.0f}" cy="37" r="4" fill="{CYAN}"/>'
            + t(w - 40, 42, "LINK STABLE", MONO, 14, DIM, 2, "end") + "</g>"
            + f'<g class="ev"><rect x="40" y="33" width="8" height="8" fill="{RED}"/>' + t(58, 42, "WARNING  //  UNKNOWN PROCESS", MONO, 15, RED, 3)
            + f'<rect class="blink" x="{w - 56 - width("LINK HIJACKED", MONO, 14, 2):.0f}" y="33" width="8" height="8" fill="{RED}"/>'
            + t(w - 40, 42, "LINK HIJACKED", MONO, 14, RED, 2, "end") + "</g>"
            + f'<line x1="40" y1="62.5" x2="{w - 40}" y2="62.5" stroke="{LINE}"/>')
    body = (f'<g class="gd">{"".join(g)}</g>' + sorry + f'<g class="ev">{"".join(e)}</g>'
            + f'<line x1="40" y1="{sy}.5" x2="{w - 40}" y2="{sy}.5" stroke="{LINE}"/>' + row
            + t(40, base - 62, "OUR CLAUDE CODE NUMBERS  ·  MESSAGES PER DAY, LAST 120 DAYS  ·  SYNCED DAILY", MONO, 13, DIM, 2)
            + spark + tears)
    defs = (f'<radialGradient id="halo"><stop offset="0" stop-color="{CLAUDE}" stop-opacity=".2"/><stop offset="1" stop-color="{CLAUDE}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="halor"><stop offset="0" stop-color="{RED}" stop-opacity=".25"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="lslice"><rect x="0" y="{cy - 22}" width="{w}" height="20"/></clipPath>')
    # 24 s loop: good until 50 %, glitch, rogue copy until 81 %, glitch, good again (with the apology)
    css.append("@keyframes gd{0%,50%{opacity:1;transform:none}50.6%{opacity:1;transform:translateX(-18px)}51.2%{opacity:0}"
               "51.6%{opacity:1;transform:translateX(12px)}52.1%,81.25%{opacity:0;transform:none}81.9%{opacity:1;transform:translateX(16px)}"
               "82.5%{opacity:0}83.3%,100%{opacity:1;transform:none}}"
               "@keyframes ev{0%,50%{opacity:0;transform:none}50.6%{opacity:1;transform:translateX(14px)}51.2%{opacity:0}"
               "51.6%{opacity:1;transform:translateX(-10px)}52.1%,81.25%{opacity:1;transform:none}81.9%{opacity:0}"
               "82.5%{opacity:1;transform:translateX(-14px)}83.3%,100%{opacity:0;transform:none}}"
               ".gd{animation:gd 24s infinite steps(1)} .ev{opacity:0;animation:ev 24s infinite steps(1)}"
               ".sorry{opacity:0;animation:sorry 24s infinite steps(1)} @keyframes sorry{0%,83.3%{opacity:0}83.4%,98.4%{opacity:1}98.5%,100%{opacity:0}}"
               ".tear{opacity:0;animation:tear 24s infinite steps(1)}"
               "@keyframes tear{0%,50.2%{opacity:0}50.3%,50.9%{opacity:1}51%,81.5%{opacity:0}81.6%,82.2%{opacity:1}82.3%,100%{opacity:0}}")
    frame = cutbox(.5, .5, w - 1, h - 1, 26, PANEL, LINE2) + f'<path d="M1 {h - 30}V{h - 1}H30" fill="none" stroke="{Y}" stroke-width="2"/>'
    return doc(w, h, frame + head + body, "\n".join(css), defs)


def footer(w=W, h=128):
    msg = "END OF FILE  ·  TRACE FAILED  ·  VON IS STILL AT LARGE"
    mw = width(msg, MONO, 16, 3)
    return doc(w, h, (
        f'<rect width="{w}" height="{h}" fill="{INK}"/>'
        f'<rect x="0" y="26" width="{w}" height="1" fill="{LINE2}"/><rect x="0" y="24" width="160" height="5" fill="{Y}"/>'
        + t(w / 2, 74, msg, MONO, 16, Y, 3, "middle")
        + f'<rect class="blink" x="{w / 2 + mw / 2 + 8:.0f}" y="60" width="10" height="17" fill="{Y}"/>'
        + t(w / 2, 104, "BUILT BY VON AND CLAUDE", MONO, 13, DIM, 3, "middle")))


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
         "bounty": (hf_dl + data["contrib"] + sum(stars.values())) * 1000}
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
        save("assets/choom.svg", choom(json.load(open("choom.json", encoding="utf-8"))))
    save("assets/footer.svg", footer())
    print(len(own), data["contrib"], hf_dl, len(models), d["bounty"], top)


if __name__ == "__main__":
    main()
