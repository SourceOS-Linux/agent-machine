# Attestation Model (v0.1)

## Attestation vs activation
**Attestation** measures host trust (SIP, NVRAM, MDM, SEP, security-DB schema,
DNS, TLS, EFI) and emits an `AttestationDecision`. **Activation** (existing
`ActivationDecision`) decides whether an AgentPod may run. Attestation is a
*prerequisite input* to activation: `activation_permitted: false` from
attestation blocks activation regardless of policy/grant state.

## Check taxonomy
- **Blocking** (a single failure denies activation): `SIP_STATUS`,
  `NVRAM_INTEGRITY`, `MDM_PROFILE_AUDIT`, `SEP_PARTICIPATION`,
  `SECURITY_DB_SCHEMA`, `DNS_INTEGRITY`, `TLS_CIPHER_AUDIT`, `EFI_SIGNATURE`.
- **Advisory** (warn only): `TELEMETRY_BOUNDARY` (SEAM-013),
  `DISPLAY_UUID_STABILITY` (SEAM-008).

`activation_permitted` is true **iff every blocking check passes** — enforced by
`scripts/validate-attestation.py`.

## Failure-mode basis (SEAM references)
Each check maps to an observed diagnostic failure mode:
- `SIP_STATUS` — SIP disabled via NVRAM (csr-active-config=0x67) — SEAM-001.
- `NVRAM_INTEGRITY` — world-writable nvram.plist — SEAM-001.
- `MDM_PROFILE_AUDIT` — unauthorized MDM enrollment (IBM MaaS360) — SEAM-002.
- `SEP_PARTICIPATION` — SEP non-participation in keybag (ANOMALY-007) — SEAM-003.
- `SECURITY_DB_SCHEMA` — iCloud Keychain schema mismatch (v24.6 vs v25+;
  missing ZSEQUENCENUMBER in ZPEER; broken escrow chain).
- `DNS_INTEGRITY` — resolution returning 102.165.31.x (adversary IPs) — SEAM-004.
- `TLS_CIPHER_AUDIT` — cipher downgrade (RC4_128_MD5) — SEAM-005.
- `EFI_SIGNATURE` — unsigned/tampered EFI — SEAM-001.

## Telemetry boundary (SEAM-013)
`TELEMETRY_BOUNDARY` is **advisory, not blocking**: Claude Desktop
`sessionSampleRate:100` means sensitive output must not route through a
100%-sampled surface. Recorded as a warn signal in the decision, not a hard
gate.

## Out-of-band ledger
The `attest` runtime CLI (T2-3, follow-up) must append each decision to
`$LEDGER_PATH` as NDJSON and never silently drop; `$LEDGER_PATH` must never be
local-only for a ledger-writing artifact.

## References
`AttestationDecision` (T2-1, `contracts/attestation-decision.schema.json`);
`ActivationDecision` (existing). Runtime `attest` subcommand: T2-3 (deferred to a
macOS attestation environment — the schema/contract here is what T4-4 depends on).
