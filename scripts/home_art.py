"""Hand-authored inline drawings for the home sections: the agent's vocabulary of a coral cursor, dashed bounding
boxes and numbered steps. Each is aria-hidden and uses currentColor, var(--v) and coral, so dark mode needs no second set.
No data lives in the drawings.
"""
CORAL, CORAL_D, INK = "#FFA69E", "#7A3A36", "#212632"


def _cur(x, y, s=1.0):
    return (f'<path transform="translate({x} {y}) scale({s})" d="M0 0 16 7.6 9.2 9.4 6.2 16.6z" fill="{CORAL}" '
            f'stroke="{CORAL_D}" stroke-width="1.4" stroke-linejoin="round"/>')


def _win(x, y, w, h, bar=14, lights=True):
    lit = "".join(f'<circle cx="{x + 8 + i * 7}" cy="{y + bar / 2}" r="1.8" fill="currentColor"/>' for i in range(3)) if lights else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="var(--v)" stroke="currentColor" stroke-width="1.75"/>'
            f'<path d="M{x} {y + bar}H{x + w}" stroke="currentColor" stroke-width="1.5"/>{lit}')


def _line(x, y, w, h=5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="currentColor"/>'


def _bbox(x, y, w, h):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="none" stroke="{CORAL_D}" stroke-width="1.75" stroke-dasharray="4 3"/>'


def _svg(body, w=168, h=112, cls="vig"):
    return f'<svg class="{cls}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true" focusable="false">{body}</svg>'


def _dot(x, y, n):
    return (f'<circle cx="{x}" cy="{y}" r="8.5" fill="{CORAL}" stroke="{CORAL_D}" stroke-width="1.25"/>'
            f'<text x="{x}" y="{y + 3.4}" text-anchor="middle" fill="{INK}" style="font:600 10px var(--font-mono)">{n}</text>')


def vig_evaluate():
    """A browser task: the target button is boxed, and the outcome gets a check."""
    return _svg(_win(4, 4, 160, 104) + _line(16, 30, 84) + _line(16, 42, 60) +
                f'<rect x="20" y="62" width="58" height="20" rx="4" fill="currentColor"/>' + _bbox(13, 55, 72, 34) + _cur(68, 76) +
                f'<circle cx="128" cy="60" r="19" fill="{CORAL}" stroke="{CORAL_D}" stroke-width="1.5"/><path d="m119 60 7 7 12-14" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')


def vig_trajectory():
    """A demonstration: three screens in order, the cursor moving between them."""
    body = ""
    for i, x in enumerate((4, 60, 116)):
        body += _win(x, 8, 48, 56, bar=10, lights=False) + _line(x + 7, 20 + 0, 26, 4) + _line(x + 7, 28, 18, 4)
        body += _dot(x + 24, 92, i + 1)
    body += '<path d="M37 92H71M93 92H127" stroke="currentColor" stroke-width="1.75" stroke-dasharray="3 4"/>'
    body += _bbox(9, 38, 26, 18) + _bbox(76, 18 + 18, 26, 18) + _bbox(130, 38, 26, 18)
    body += _cur(30, 50, .7) + _cur(97, 48, .7) + _cur(150, 50, .7)
    return _svg(body)


def vig_ground():
    """Grounding: one element among many, boxed, with its coordinates."""
    cells = "".join(f'<rect x="{18 + c * 34}" y="{28 + r * 34}" width="24" height="24" rx="5" fill="currentColor"/>'
                    for r in range(2) for c in range(4) if not (r == 1 and c == 2))
    return _svg(_win(4, 4, 160, 104, lights=False) + cells +
                f'<rect x="86" y="62" width="24" height="24" rx="5" fill="var(--v)" stroke="currentColor" stroke-width="1.75"/>' +
                _bbox(80, 56, 36, 36) + '<path d="M98 56V18M116 74H164" stroke="' + CORAL_D + '" stroke-width="1.25" stroke-dasharray="2 3"/>' + _cur(102, 78))


def vig_loop():
    """An agent harness: a command window and the observe, act loop around it."""
    return _svg(_win(4, 4, 110, 104) +
                '<path d="m14 32 7 6-7 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' +
                _line(28, 35, 62) + _line(14, 54, 78) + _line(14, 68, 52) + _line(14, 82, 68) +
                f'<path d="M124 42a24 24 0 0 1 38 8M162 72a24 24 0 0 1-38-8" fill="none" stroke="{CORAL}" stroke-width="3" stroke-linecap="round"/>'
                f'<path d="m164 40-1 12-11-4zM122 74l1-12 11 4z" fill="{CORAL}"/>' + _cur(136, 48, .9))


def vig_sandbox():
    """A sandbox: the agent's window inside a boundary, locked."""
    corners = "M4 22V10a6 6 0 0 1 6-6h12M146 4h12a6 6 0 0 1 6 6v12M164 90v12a6 6 0 0 1-6 6h-12M22 108H10a6 6 0 0 1-6-6V90"
    return _svg(f'<path d="{corners}" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>'
                '<rect x="10" y="10" width="148" height="92" rx="4" fill="none" stroke="currentColor" stroke-width="1.25" stroke-dasharray="3 5"/>' +
                _win(26, 22, 88, 68, bar=12) + _line(36, 44, 54, 4) + _line(36, 54, 36, 4) + _cur(76, 62, .85) +
                f'<path d="M122 66v-9a11 11 0 0 1 22 0v9" fill="none" stroke="{CORAL_D}" stroke-width="3"/>'
                f'<rect x="114" y="65" width="38" height="29" rx="5" fill="{CORAL}" stroke="{CORAL_D}" stroke-width="1.5"/><circle cx="133" cy="79" r="3.5" fill="{INK}"/>')


def vig_shield():
    """Safety: a shield in front of the window the agent acts on."""
    return _svg(_win(4, 4, 120, 96) + _line(16, 32, 72) + _line(16, 46, 52) + _line(16, 60, 36) + _bbox(12, 70, 44, 18) +
                '<path d="M116 14 158 28v32c0 24-18 38-42 48-24-10-42-24-42-48V28z" fill="var(--v)" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/>'
                f'<path d="m98 58 13 13 24-26" fill="none" stroke="{CORAL_D}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')


VIGNETTES = {"benchmark": vig_evaluate, "dataset": vig_trajectory, "model": vig_ground, "framework": vig_loop,
             "infrastructure": vig_sandbox, "safety-security": vig_shield}


def device_web():
    return _svg('<rect x="3" y="3" width="90" height="66" rx="7" fill="var(--v)" stroke="currentColor" stroke-width="2"/><path d="M3 18H93" stroke="currentColor" stroke-width="2"/>'
                '<rect x="30" y="7.5" width="54" height="6" rx="3" fill="currentColor"/><circle cx="11" cy="10.5" r="2" fill="currentColor"/><circle cx="19" cy="10.5" r="2" fill="currentColor"/>' +
                _bbox(16, 30, 40, 22) + _cur(46, 42, .8), 96, 72, "r3-device")


def device_desktop():
    return _svg('<rect x="3" y="3" width="90" height="54" rx="5" fill="var(--v)" stroke="currentColor" stroke-width="2"/><path d="M48 57v12M30 69h36" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>'
                '<path d="M3 47H93" stroke="currentColor" stroke-width="1.5"/>' + "".join(f'<rect x="{38 + i * 8}" y="49.5" width="4" height="4" rx="1" fill="currentColor"/>' for i in range(3)) +
                _bbox(14, 12, 34, 24) + _cur(40, 26, .8), 96, 72, "r3-device")


def device_mobile():
    return _svg('<rect x="29" y="1" width="38" height="70" rx="7" fill="var(--v)" stroke="currentColor" stroke-width="2"/><path d="M42 6h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
                + _bbox(35, 28, 26, 18) + _cur(52, 38, .75) + '<path d="M42 65h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>', 96, 72, "r3-device")


def vig_paper():
    """A paper page with one line boxed, the way an agent reads it."""
    lines = "".join(_line(26, y, w, 4) for y, w in ((70, 136), (82, 148), (94, 118), (118, 148), (130, 140), (142, 96), (166, 148), (178, 124)))
    return _svg(f'<rect x="20" y="16" width="176" height="208" rx="3" fill="none" stroke="currentColor" stroke-width="1.5" transform="rotate(4 108 120)"/>'
                f'<rect x="10" y="12" width="176" height="212" rx="3" fill="var(--v)" stroke="currentColor" stroke-width="2"/>'
                + _line(40, 28, 116, 7) + _line(58, 42, 80, 4) + lines + _bbox(20, 110, 156, 28) + _cur(150, 128), 208, 236, "vig-paper")


def vig_rank():
    """A leaderboard: ranked runs and a cursor on the first. Abstract, no scores."""
    rows = ""
    for i, w in enumerate((104, 78, 56)):
        y = 10 + i * 30
        rows += _dot(14, y + 10, i + 1) + f'<rect x="30" y="{y + 3}" width="{w}" height="14" rx="3" fill="currentColor"/>'
    return _svg(rows + _bbox(26, 7, 114, 26) + _cur(122, 20, .85), 148, 100, "vig-rank")
