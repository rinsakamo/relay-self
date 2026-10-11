"""Read-only RelayUI-compatible replay of an already completed Self/S49 World run.

Never starts Minecraft/Node/llama, issues Actions, changes owner cognition,
or promotes observed Memory into S10 learning or a learned S11 Habit.
Native/trace/retention consistency is verified before a new preview is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.self_demo import (
    DemoRejected,
    project_native_report,
    retain_native_observations,
)
from relay_self.persistent_cognition import load_persistent_cognition

MAX_SOURCE_BYTES = 5 * 1024 * 1024
NATIVE_FILES = ("native_report.json", "self_trace.jsonl", "observed_memory.json")
L2_FILE = "live_l2.jsonl"


class ReplayRejected(ValueError):
    """Unverified source, incoherent provenance, or unsafe output location."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ReplayRejected("duplicate JSON source key")
        value[key] = item
    return value


def _json(raw: bytes) -> object:
    def reject_constant(_value: str) -> None:
        raise ReplayRejected("non-finite JSON number")
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=reject_constant,
    )


def _source(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ReplayRejected("required source file missing or symlinked")
    if not 0 < path.stat().st_size <= MAX_SOURCE_BYTES:
        raise ReplayRejected("source file outside size limit")
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ReplayRejected("source read outside size limit")
    return raw


def _lines(raw: bytes) -> list[dict[str, Any]]:
    decoded = raw.decode("utf-8").splitlines()
    if not decoded or len(decoded) > 128:
        raise ReplayRejected("source JSONL row count outside bound")
    rows = [_json(line.encode("utf-8")) for line in decoded]
    if any(not isinstance(row, dict) for row in rows):
        raise ReplayRejected("non-object JSONL row")
    return rows


def load_replay(evidence_dir: Path) -> dict[str, Any]:
    """Verify already-stored product evidence and make a non-authoritative view."""
    if (not evidence_dir.is_dir() or evidence_dir.is_symlink()
            or evidence_dir.resolve() != evidence_dir.absolute()):
        raise ReplayRejected("evidence directory must be a physical absolute directory")
    files = {name: _source(evidence_dir / name) for name in NATIVE_FILES}
    sidecar = evidence_dir / L2_FILE
    if sidecar.is_symlink():
        raise ReplayRejected("L2 sidecar symlink denied")
    if sidecar.exists():
        files[L2_FILE] = _source(sidecar)
    report = _json(files["native_report.json"])
    if not isinstance(report, dict):
        raise ReplayRejected("native report is not a JSON object")
    try:
        projected = project_native_report(report)
        expected_memory = retain_native_observations(projected)
        observed_memory = load_persistent_cognition(
            evidence_dir / "observed_memory.json"
        )
    except (DemoRejected, OSError, ValueError, TypeError) as exc:
        raise ReplayRejected("native evidence or retained snapshot invalid") from exc
    if observed_memory != expected_memory:
        raise ReplayRejected("retained Memory differs from native evidence projection")
    rows = _lines(files["self_trace.jsonl"])
    if rows[:len(projected)] != list(projected):
        raise ReplayRejected("original Self trace differs from native report")
    extras = rows[len(projected):]
    l2 = None
    if L2_FILE in files:
        l2_rows = _lines(files[L2_FILE])
        if len(l2_rows) != 1 or len(extras) != 2 or extras[0] != l2_rows[0]:
            raise ReplayRejected("L2 sidecar and trace identity mismatch")
        l2 = l2_rows[0]
        if (
            l2.get("kind") != "l2_live_observer"
            or l2.get("session") != report.get("session_id")
            or l2.get("l0_blocked_on_l2") is not False
            or l2.get("l2_used_as_action") is not False
            or l2.get("authorized_actions") != 0
            or l2.get("learning_updates") != 0
            or l2.get("habit_grants") != 0
            or type(l2.get("model_attempts")) is not int
            or l2["model_attempts"] not in (0, 1)
        ):
            raise ReplayRejected("unqualified L2 source or Action authority")
        if l2.get("status") == "EXPIRED_WORLD_ADVANCED" and (
            l2.get("text_current") is not False
            or type(l2.get("source_world_seq")) is not int
            or type(l2.get("latest_world_seq")) is not int
            or l2["latest_world_seq"] <= l2["source_world_seq"]
        ):
            raise ReplayRejected("stale L2 is incorrectly marked current")
    elif len(extras) != 1:
        raise ReplayRejected("unexpected source rows without L2 sidecar")
    tail = extras[-1]
    if (
        tail.get("kind") != "observed_memory"
        or tail.get("retained_episodes") != len(expected_memory.memories)
        or tail.get("learning_preference_changed") is not False
        or tail.get("habit_auto_granted") is not False
        or tail.get("durable_file") != "observed_memory.json"
    ):
        raise ReplayRejected("unqualified Memory projection or learning promotion")
    events = []
    for row in projected:
        kind = row["kind"]
        if kind not in ("native_observation", "decision", "native_action_outcome"):
            continue
        event: dict[str, object] = {
            "kind": kind,
            "epoch": row["epoch"],
            "source_type": row["source_type"],
        }
        if kind == "native_observation":
            event.update({
                "event_seq": row["event_seq"],
                "probe_seq": row["probe_seq"],
                "entity_id": row["target_entity_id"],
                "distance_m": row["target_distance_m"],
            })
        elif kind == "decision":
            event.update({
                "layer": "L0",
                "selected": row["selected"],
                "issued_action": row["issued_native_action"],
            })
        else:
            event.update({
                "action_id": row["action_id"],
                "terminal": row["terminal"],
                "movement_m": row["movement_m"],
                "execution_evidence_sha256": row["execution_evidence_sha256"],
                "goal_success_attested": False,
                "learning_update": False,
            })
        events.append(event)
    return {
        "schema": "RELAYUI_SELF1_OFFLINE_REPLAY_V1",
        "qualification": "NATIVE_REPLAY_VALIDATED_NOT_CONTINUOUS_LIVE",
        "session": report["session_id"],
        "minecraft_version": report.get("minecraft_version"),
        "mineflayer_version": report.get("mineflayer_version"),
        "event_count": len(events),
        "observations": 3,
        "decisions": 3,
        "native_actions": 2,
        "retained_observed_episodes": len(expected_memory.memories),
        "retained_origin": report.get("retained_origin"),
        "learning_updates": 0,
        "habit_grants": 0,
        "goal_success_attested": False,
        "l2": {
            "status": l2.get("status"),
            "attempts": l2.get("model_attempts"),
            "text_current": l2.get("text_current"),
            "source_world_seq": l2.get("source_world_seq"),
            "latest_world_seq": l2.get("latest_world_seq"),
            "text_observation_only": l2.get("text_observation_only"),
        } if l2 else {"status": "NOT_RECORDED", "attempts": 0, "text_current": False},
        "sources": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            for name, raw in sorted(files.items())
        },
        "events": events,
    }


_HTML_START = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RelaySelf · World Replay</title>
<style>
:root{color-scheme:dark;font-family:ui-sans-serif,system-ui,sans-serif;background:#0e1016;color:#f2f4f8}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#19304a 0%,#0e1016 48%);min-height:100vh}
main{max-width:1100px;margin:auto;padding:38px 24px 65px}.tag{font-size:12px;letter-spacing:.14em;color:#87acd3;text-transform:uppercase}
h1{font-size:clamp(29px,5vw,50px);letter-spacing:-.045em;margin:12px 0}h2{font-size:17px;font-weight:600}
.sub{color:#98a8bd;line-height:1.55;max-width:850px}.badge{display:inline-block;border:1px solid #52677b;border-radius:50px;padding:6px 11px;color:#b2c9df;font-size:11px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:28px 0}
.metric,.panel,.event{background:#171d28;border:1px solid #293545;border-radius:14px;padding:17px}
.metric strong{font-size:30px;display:block;margin-top:9px}.metric small,.muted{color:#94a6bb}
.layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(240px,1fr);gap:20px}
.panel h2{margin:0 0 16px}.timeline{display:flex;flex-direction:column;gap:12px}
.event{border-left:4px solid #6e99c4}.event.action{border-left-color:#66c4b1}.event.decision{border-left-color:#e4bc6e}
.event .meta{color:#9cb0c8;font-size:12px}.event .value{font-weight:650;margin:8px 0;font-size:16px}.event .details{font-size:12px;color:#a9b8cb;overflow-wrap:anywhere}
.controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0 20px}
button{color:#cfe4fa;border:1px solid #42566a;border-radius:8px;background:#1b2b3a;padding:8px 12px;cursor:pointer}
button[aria-pressed=true]{background:#34516b;border-color:#79a4ce}button:focus-visible{outline:2px solid #c6e2f7}
.kv{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #2c3949;padding:12px 0;font-size:13px}
.kv span{color:#9fb0c4}.kv strong{font-size:12px;text-align:right;overflow-wrap:anywhere}
.note{margin-top:18px;border-top:1px solid #334154;padding-top:16px;color:#9fb0c4;font-size:12px;line-height:1.6}
code{font-size:11px;overflow-wrap:anywhere;color:#aac8df}
@media(max-width:750px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.layout{grid-template-columns:1fr}}
</style></head>
<body><main><div class="tag">RELAYSELF · EVIDENCE-BOUND VIEWER</div>
<h1>World Replay <span class="badge">OFFLINE / READ ONLY</span></h1>
<p class="sub">保存済みの実World証拠から、観測・L0判断・Action OUTCOME・L2の状態を再構成したリプレイです。現在のMinecraftへ接続せず、Actionを発行しません。</p>
<div id="metrics" class="metrics"></div>
<div class="layout"><section class="panel"><h2>認知・行動タイムライン</h2>
<div id="controls" class="controls"></div><div id="timeline" class="timeline"></div></section>
<aside class="panel"><h2>実行と根拠</h2><div id="details"></div>
<div class="note">Memory保存 ≠ 学習成功。L2の生成 ≠ Action権限。OUTCOME ≠ ゴール達成。
S49の固定3判断を再生しています。常時稼働・自律的な目標選択は未実装です。</div>
<h2 style="margin-top:24px">検証した入力のハッシュ</h2><div id="hashes"></div>
</aside></div></main>
<script type="application/json" id="relay-data">"""
_HTML_END = r"""</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('relay-data').textContent);
const el=id=>document.getElementById(id);
const add=(parent,tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;node.textContent=String(text);parent.appendChild(node);return node};
[['観測',data.observations],['決定',data.decisions],['Action / OUTCOME',data.native_actions],['記憶episode',data.retained_observed_episodes]].forEach(pair=>{
 const card=add(el('metrics'),'div','metric','');add(card,'small','',pair[0]);add(card,'strong','',pair[1])
});
const types=[['all','すべて'],['native_observation','観測'],['decision','L0判断'],['native_action_outcome','Action']];
const holder=el('controls');
const timeline=el('timeline');
function render(filter){
 timeline.replaceChildren();
 data.events.filter(e=>filter==='all'||e.kind===filter).forEach(e=>{
   const box=add(timeline,'article','event '+(e.kind==='native_action_outcome'?'action':e.kind),'');
   add(box,'div','meta','EPOCH '+e.epoch+' · '+e.kind);
   if(e.kind==='native_observation'){
     add(box,'div','value','World観測 · entity '+e.entity_id);
     add(box,'div','details','event seq '+e.event_seq+' → probe seq '+e.probe_seq+' · distance '+e.distance_m+' m');
   }else if(e.kind==='decision'){
     add(box,'div','value','L0 · '+e.selected);
     add(box,'div','details',e.issued_action?'Action発行権限は既存S49 owner':'WAIT · Action発行なし');
   }else{
     add(box,'div','value',e.terminal+' · '+e.movement_m+' m');
     add(box,'div','details','action '+e.action_id+' · evidence '+(e.execution_evidence_sha256||'NOT_RETAINED'));
   }
 });
}
types.forEach(([name,label])=>{
 const button=add(holder,'button','',label);button.type='button';
 button.setAttribute('aria-pressed',String(name==='all'));
 button.addEventListener('click',()=>{holder.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render(name)});
});
render('all');
const detail=el('details');
[['Session',data.session],['Minecraft',data.minecraft_version],['Mineflayer',data.mineflayer_version],
 ['L2',data.l2.status],['L2 attempts',data.l2.attempts],
 ['L2 current',data.l2.text_current],['Retained origin',data.retained_origin],
 ['Learning updates',data.learning_updates],['Habit grants',data.habit_grants],['Goal success',data.goal_success_attested]]
 .forEach(([key,val])=>{const row=add(detail,'div','kv','');add(row,'span','',key);add(row,'strong','',val??'UNKNOWN')});
Object.entries(data.sources).forEach(([name,meta])=>{
 const block=add(el('hashes'),'div','kv','');add(block,'span','',name);add(block,'code','',meta.sha256)
});
</script></body></html>
"""


def render_replay(replay: dict[str, Any]) -> str:
    payload = json.dumps(replay, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    # Scripts are static; never allow any source-controlled </script> to break
    # the JSON data tag. The viewer renders all source data via textContent.
    return _HTML_START + payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + _HTML_END


def write_replay(replay: dict[str, Any], evidence_dir: Path, output_file: Path) -> None:
    if output_file.is_symlink() or output_file.exists():
        raise ReplayRejected("viewer destination must not already exist")
    if not output_file.is_absolute() or not output_file.parent.is_dir():
        raise ReplayRejected("viewer output requires existing physical parent")
    if output_file.parent.is_symlink():
        raise ReplayRejected("viewer output parent symlink denied")
    if evidence_dir == output_file.parent or evidence_dir in output_file.parents:
        raise ReplayRejected("viewer cannot be written inside source evidence")
    with output_file.open("x", encoding="utf-8") as stream:
        stream.write(render_replay(replay))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline read-only RelaySelf native World viewer")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run and args.output_file is None:
        parser.error("--output-file is required unless --dry-run is set")
    try:
        replay = load_replay(args.evidence_dir)
        if args.output_file is not None and not args.dry_run:
            write_replay(replay, args.evidence_dir, args.output_file)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        print(json.dumps({
            "classification": "RELAYUI_REPLAY_SOURCE_BLOCKED",
            "reason": type(exc).__name__,
            "model_launched": False, "world_launched": False,
            "action_issued": False,
        }, sort_keys=True))
        return 2
    print(json.dumps({
        "classification": replay["qualification"],
        "session": replay["session"],
        "events": replay["event_count"],
        "l2_status": replay["l2"]["status"],
        "output_file": str(args.output_file) if not args.dry_run else None,
        "model_launched": False, "world_launched": False,
        "action_issued": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
