// T1n DEV-only instrumentation of the EXISTING bridge emit() path.
// This helper is called only for paper_snapshot with explicit native-sidecar
// opt-in. The canonical envelope, source seq, stream, and admission stay intact.
export function emitWithT1nTiming ({
  sessionId, seq, type, payload, makeEnvelope, advanceSequence,
  traceEnabled, traceWriter, stdoutWriter, diagnosticWriter,
  clock = () => process.hrtime.bigint(),
  cpuUsage = previous => process.cpuUsage(previous)
}) {
  if (type !== 'paper_snapshot' || typeof diagnosticWriter !== 'function' ||
      typeof stdoutWriter !== 'function' || typeof advanceSequence !== 'function' ||
      typeof makeEnvelope !== 'function') throw Error('T1n DEV Paper-only emitter required')
  const cpuStart = cpuUsage()
  const entry = clock()
  const message = makeEnvelope(sessionId, seq, type, payload)
  const envelopeReturn = clock()
  let traceSerializeReturn = null
  let traceWriteReturn = null
  if (traceEnabled) {
    const traceLine = JSON.stringify({
      node_monotonic_ns: clock().toString(), ...message
    }) + '\n'
    traceSerializeReturn = clock()
    traceWriter(traceLine)
    traceWriteReturn = clock()
  }
  // The original bridge advances exactly once after the native trace, and
  // before formatting and writing the same canonical stdout message.
  advanceSequence()
  const nativeLine = JSON.stringify(message) + '\n'
  const stdoutSerializeReturn = clock()
  const stdoutWriteAccepted = stdoutWriter(nativeLine)
  const stdoutWriteReturn = clock()
  const cpu = cpuUsage(cpuStart)
  const diagnostic = {
    kind: 't1n_emit_paper_snapshot', diagnostic_version: 1,
    session_id: sessionId, seq, source_index: payload?.data?.snapshot?.index ?? null,
    challenge: payload?.data?.snapshot?.challenge ?? null,
    source_status: payload?.data?.status ?? null,
    entry_ns: entry.toString(),
    envelope_return_ns: envelopeReturn.toString(),
    trace_serialize_return_ns: traceSerializeReturn?.toString() ?? null,
    trace_write_return_ns: traceWriteReturn?.toString() ?? null,
    stdout_serialize_return_ns: stdoutSerializeReturn.toString(),
    stdout_write_return_ns: stdoutWriteReturn.toString(),
    stdout_write_accepted: Boolean(stdoutWriteAccepted),
    process_cpu_user_us: cpu.user,
    process_cpu_system_us: cpu.system,
    node_clock_only: true, stdout_write_return_is_delivery_ack: false,
    event_loop_or_gc_causality_proven: false,
    source_qualification: false
  }
  // Diagnostic failure must not alter the already-issued canonical native
  // source; the local read-only reducer detects absent diagnostic rows.
  try { diagnosticWriter(JSON.stringify(diagnostic) + '\n') } catch {}
  return message
}
