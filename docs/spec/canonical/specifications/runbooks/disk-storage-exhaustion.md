# Disk / Storage Exhaustion

## Symptoms

- Disk usage alerts fire, or writes start failing with `ENOSPC`/out-of-space
  errors.
- Service crashes or refuses new connections once disk fills.
- Log ingestion, database writes, or temp-file operations start failing.

## Diagnosis

1. Identify which volume/mount is full and which process is consuming it.
2. Check for unbounded growth: logs without rotation, temp files without
   cleanup, a runaway cache spilling to disk, or an unbounded queue/WAL.
3. Correlate onset with a recent deploy, traffic pattern change, or a disabled
   cleanup job.
4. Confirm whether this is a single-node issue or affects the whole fleet.

## Resolution Steps

1. Free emergency space immediately: rotate/compress/delete old logs, clear
   temp directories, prune stale artifacts.
2. Disable or throttle the process causing unbounded growth if identified.
3. Expand volume capacity if the growth is legitimate and expected to continue.
4. Validate recovery by confirming disk usage trends flat or downward and
   writes succeed again.

## Rollback

1. Roll back a recent deploy if it introduced the unbounded growth.
2. Restore prior log-rotation/retention configuration if it was changed or
   disabled.

## Post-Incident

- Add or tighten disk-usage alerting with enough lead time to act before
  exhaustion.
- Add automated retention/rotation for whatever grew unbounded.
- Document the growth source and the guardrail added to prevent recurrence.
