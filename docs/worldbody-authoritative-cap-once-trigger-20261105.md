# One explicit WorldBody v1 authoritative movement cap original Paper World — 2026-11-05

This is a **third distinct** standalone disposable DEV World, NOT a retry
of either preserved FAILED original test World.

Frozen previous originals:
- #41999248107: Paper walkSpeed changed to 0.08 but S16 measured
  0.6269065734210617 m twice; no REST. SHA original #13401363197.
- #42009783381: Paper Slowness V potion_active=true and walkSpeed=0.08
  but S16 measured 0.6269065734210617 m twice; no REST.
  SHA original #13406747238.

**Original S49 sole Action issuer and fixed WorldBody laws remain:**
MOVE_FATIGUE_PER_METRE=2.0, STILL_RECOVERY_PER_SERVER_TICK=0.003,
SLOW_AT=0.25, NORMAL_AGAIN_AT=0.05. The externally given WorldBody
physical law now also constrains the *server-accepted* horizontal
movement to 35% of requested movement under degraded condition,
using Bukkit PlayerMoveEvent.setTo. No Self owner can change the
cap/rates, or see server private truth logs.

Offline CI #42011073256 at HEAD
0de207d4d16d9824bc7aa33cb4fddc201b1f2af6 completed SUCCESS,
including the compiled fixed Paper plugin and original S49 negative
controls. A new World may be created **ONLY** on exact message:

run-worldbody-fixed-authoritative-cap-once-20261105

No automatic replay/retry on any failed or uncertain Action.
If this client does not reflect Paper correction, true original S16
movement will not fall and SelfBody MUST refuse REST. Never
substitute World private internal fatigue for S16 physical evidence,
or force native L0 to REST. If World rest is selected, no further
physical Action is to be issued. Post-World auditor shall independently
check both authoritative movement restrictions and physical recovery
of server native speed/potion state. It is NOT yet Self learning.

Original Paper log, exact original S49 World report and SHA manifest
retained regardless of outcome. No compression/emotion engine,
P1 coefficient tuning, M energy credit, L2 provider, or learning
updates. DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
