"""Static, offline HTML projection of the verified Self product timeline.

No JavaScript, network fetch, external fonts, script execution, extra model
calls, Mineflayer effects, or changes to original cognition and Action owners.
"""
from __future__ import annotations

from html import escape
from typing import Any

SCHEMA = "relay-self.product.cognition-timeline.v1"


def _safe(text: Any) -> str:
    return escape(str(text), quote=True)


def render_html(rows: tuple[dict[str, Any], ...]) -> str:
    """Return a browser-openable timeline. All source strings are escaped."""
    if (not isinstance(rows, tuple) or len(rows) < 3
            or rows[0].get("kind") != "session"
            or rows[-1].get("kind") != "summary"
            or any(not isinstance(r, dict) or r.get("schema") != SCHEMA
                   or r.get("session") != rows[0].get("session") for r in rows)):
        raise ValueError("completed and source-aligned timeline required")
    session = _safe(rows[0]["session"])
    events: list[str] = []
    for row in rows[1:-1]:
        kind = row["kind"]
        if kind == "present":
            title, label = "WORLD", "OBSERVE"
            detail = (f"Zombie at {_safe(row['target_distance_m'])} m "
                      f"· source probe #{_safe(row['probe_seq'])}")
        elif kind == "selection":
            title, label = "L0", "DECIDE"
            detail = (_safe(row["candidate"])
                      + (" · native Action issued" if row["issued_action"]
                         else " · WAIT, no Action"))
        elif kind == "action_outcome":
            title, label = "S16", "OUTCOME"
            detail = (f"{_safe(row['terminal'])} · "
                      f"{_safe(row['observed_movement_m'])} m observed · "
                      "goal UNKNOWN")
        elif kind == "l2_observer":
            title, label = "L2", "READ ONLY"
            detail = (
                f"{_safe(row['status'])} · "
                f"{_safe(row['model_attempts'])} model attempts · "
                "no Action permission"
            )
            if row.get("text_untrusted"):
                detail += (
                    "<p class='model-note'>Model commentary (untrusted): "
                    + _safe(row["text_untrusted"]) + "</p>"
                )
        elif kind == "memory":
            title, label = "MEM", "RETAIN"
            detail = (
                f"{_safe(row['observed_action_episodes'])} stored movement "
                "observations · no new Habit"
            )
        else:
            raise ValueError("unsupported timeline kind for browser view")
        epoch = row.get("epoch")
        epoch_txt = f"Epoch {_safe(epoch)}" if epoch is not None else "Session summary"
        events.append(
            "<li class='event'>"
            f"<div class='lane'>{_safe(title)}</div>"
            "<div class='panel'>"
            f"<div class='event-meta'>{_safe(label)} · {epoch_txt}</div>"
            f"<div class='event-detail'>{detail}</div>"
            "</div></li>"
        )
    l2_present = any(r["kind"] == "l2_observer" for r in rows)
    mem_present = any(r["kind"] == "memory" for r in rows)
    chips = [
        "3 native decisions", "2 native movement outcomes",
        "Goal: UNKNOWN",
        "L2: source report" if l2_present else "L2: not supplied",
        "Memory: supplied" if mem_present else "Memory: not supplied",
    ]
    chips_html = "".join(f"<span class='chip'>{_safe(x)}</span>" for x in chips)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; script-src 'none'; connect-src 'none'; form-action 'none'">
<title>RelaySelf · Cognition timeline</title>
<style>
:root {{color-scheme:dark; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:#0b101b; color:#e9edf5}}
* {{box-sizing:border-box}}
body {{margin:0; min-height:100vh; padding:clamp(18px,5vw,64px);}}
main {{max-width:860px; margin:auto;}}
header {{border-bottom:1px solid #354052; padding-bottom:22px; margin-bottom:28px;}}
.kicker {{letter-spacing:.14em; font-size:.72rem; font-weight:750; color:#96b9ff}}
h1 {{font-size:clamp(1.8rem,5vw,2.8rem); margin:12px 0 8px; letter-spacing:-.03em}}
.subtitle {{color:#9caac2; line-height:1.55}}
.source {{font-family:ui-monospace,monospace; font-size:.8rem; overflow-wrap:anywhere; color:#bbc5dc}}
.chips {{display:flex; flex-wrap:wrap; gap:8px; margin-top:20px}}
.chip {{padding:6px 10px; border:1px solid #344259; border-radius:14px; font-size:.77rem; color:#c9d5ed}}
ol {{padding:0; margin:0; list-style:none;}}
.event {{display:grid; grid-template-columns:68px 1fr; gap:16px; position:relative; margin-bottom:12px;}}
.event:not(:last-child)::after {{content:""; position:absolute; top:45px; bottom:-12px; left:32px; border-left:1px solid #35435c}}
.lane {{z-index:1; width:64px; height:38px; background:#1c2f52; color:#c4daff; border:1px solid #426199; border-radius:9px; display:flex; align-items:center; justify-content:center; font-weight:750; font-size:.8rem}}
.panel {{background:#131e30; border:1px solid #324058; border-radius:12px; padding:15px 18px; min-width:0}}
.event-meta {{font-size:.75rem; letter-spacing:.09em; color:#8db5ff; font-weight:750; margin-bottom:7px}}
.event-detail {{overflow-wrap:anywhere; line-height:1.6}}
.model-note {{color:#adbdd7; background:#1c2940; border-radius:8px; padding:12px; white-space:pre-wrap; font-size:.86rem; margin:10px 0 0}}
footer {{border-top:1px solid #354052; margin-top:30px; padding-top:20px; color:#a6b6cf; font-size:.83rem; line-height:1.6}}
strong {{color:#d4e5ff}}
@media(max-width:460px) {{.event {{grid-template-columns:56px 1fr; gap:10px}} .lane {{width:54px}} .event:not(:last-child)::after {{left:26px}}}}
</style>
</head>
<body>
<main>
<header>
<div class="kicker">RELAYSELF · OBSERVATIONAL PLAYBACK</div>
<h1>One Self session</h1>
<div class="subtitle">Existing S49 World → L0 → Action outcomes, with optional L2 and Memory records.</div>
<p class="source">Session: {session}</p>
<div class="chips">{chips_html}</div>
</header>
<ol aria-label="Observed cognition timeline">
{''.join(events)}
</ol>
<footer><strong>Evidence boundary:</strong> Recorded source only, not independently attested physical causality.
No newly executed World Actions, model calls, certified task goals, learned Habits or GPU-release claims.
L2 appears as a summary and is not placed in a physically proven temporal overlap.</footer>
</main>
</body>
</html>
"""
