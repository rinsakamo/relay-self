# B original resident CPU Present (offline)

`ResidentCognitiveWorkOwner.read_coverage_inquiry_cpu` is the explicit,
read-only CPU entry for the existing coverage inquiry consumer. It holds the
resident lock while `read_present_cpu` calls `build_bd1b_owner_present`, which
qualifies both original Native and Paper sources, retrieves the registered
Schema, and projects ThreeSelf and Present. The consumer reprojects and compares
the supplied readout before reading SelfWorld. No periodic scheduler or live
L1/L2 consumer is installed by this entry. A returned readout is not a lease:
later consumers must revalidate it before using it as current.

The projection rechecks the original source and schema after projection. The
resident lock fences owner-mediated state changes, while the second source
qualification detects a changed external Paper receipt during projection.
The source producer must supply a fresh receipt after Paper log changes.

E2c remains HOLD. Its future integration point is inside
`build_bd1b_owner_present`, after original source qualification and inside the
same resident lock: capture a current, identity-qualified SenseFrame together
with its immutable revision, compose its independent `mineflayer:` ref with
the original `native:` and `paper:` refs, and revalidate all inputs before
returning. The producer must publish its snapshot under this lock (or provide
an equivalent atomic snapshot and revision recheck). Preserve each claim's
original provenance; native SENSE does not become Paper evidence. No SenseFrame
is accepted or projected by this change.
