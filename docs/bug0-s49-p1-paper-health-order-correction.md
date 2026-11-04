# Bug-0 Paper DEV sequential Health console source correction

Second DEV Paper World [#41836155063](https://github.com/rinsakamo/relay-self/actions/runs/41836155063)
stopped **before irreversible ATTACK**, Action count zero. The original
server log demonstrated that Paper published the `/data get ... Health`
command result before the `/say START` and `/say END` console-chat
markers despite their actual command issuance order. The old strict parser
correctly refused to infer a missing/ambiguous source.

This child-only correction adds an optional Paper-only **sequential**
source reader: dispatch START, wait for the original single collector to
publish it, dispatch exactly one target Health query, wait for its unique
logged answer, then dispatch END and require the existing original
bracket parser to succeed. Historical Mojang/default S49 ATTACK behavior
is unchanged. Offline negative tests model the asynchronous publication
reordering and confirm the old batched case still fails closed.

First DEV World #41835442063 also stopped before ATTACK on modifiable World
full-time clock; fixed by monotone `Bukkit.getCurrentTick()` and source
start just before original Action execution, after operator staging.

This exact commit authorizes another **single disposable DEV World**
with the same original S49 ATTACK → REST owner and no model/Gemma calls.
No qualification/science claims. All failed originals remain retained;
do not automatically retry if any native Action becomes UNKNOWN.
