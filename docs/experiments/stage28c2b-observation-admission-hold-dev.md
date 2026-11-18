# Stage 28c-2b observation admission: partial DEV, HOLD

The existing resident login changes the original physical issuer to ONLINE.
Disabling resident MOVE alone still leaves EAT and ATTACK leases available.
The optional `observation_only` policy denies every issuer lease and every
effect at `require_native_effect`, including neutralization. Sensor probes and
shutdown remain outside that effect admission. The recovered-owner preparation
can request this policy without introducing another issuer.

This is not a global process sandbox: legacy direct issuers are outside this
admission, and the native final-stdin guard must actually be installed by the
owned bridge. Observation-only must not be claimed from the flag alone.

This is an incomplete preparation, not an executable World trial. The copy
primitive compares all restored files before and after copying, rechecks the
source, then constructs the original A/B owners pointing at the copy with
observation-only admission. It has only been tested with synthetic source data.
Complete historical session rejection, source-qualified Paper/native correlation, fresh body
adoption, independent audit and controlled cleanup remain to be implemented.
The restored checkpoint's tick and a new Paper process tick have different
epochs. In particular, the existing fresh-L1 eligibility compares the new
World tick numerically with the saved tick; it must not be used as proof of
cross-session clock continuity. No arbitrary offset is permitted. HOLD until
the mapping is explicit and validated.

No real Paper, native, physical Action, peer send or Gemma operation is run by
this change. `FRESH_L1_NOT_RUN / 60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO /
SCIENCE_NOT_RUN`.
