# Local Neuronpedia-Compatible `/steer` Endpoint Contract

Status: Issue #32 contract and stub. This document defines the local endpoint shape that Noetica can call through `NEURONPEDIA_BASE_URL=http://localhost:<port>` without changing Noetica code.

This is not the real activation-injection implementation. It does not load model weights, load SAE artifacts, register sourcesets, or intercept a model forward pass.

## Client contract

Client references:

- `SocioProphet/Noetica:lib/providers/neuronpedia.ts`
- `SocioProphet/Noetica:app/api/steer/route.ts`
- `SocioProphet/Noetica:docs/adapter-contracts.md`

Noetica endpoint behavior:

- hosted base URL `https://www.neuronpedia.org` resolves to `/api/steer`
- local base URL `http://localhost:<port>` resolves to `/steer`

Agent Machine satisfies the local form in this contract.

## Endpoint

```text
POST /steer
Content-Type: application/json
```

Minimal request shape:

```json
{
  "prompt": "Write one short sentence about Paris.",
  "model_id": "gpt2-small",
  "steering": {
    "feature_id": "10200",
    "layer": "6-res-jb",
    "strength": 5,
    "preset": "optional"
  }
}
```

Required fields:

- `prompt`: non-empty string
- `model_id`: non-empty string
- `steering.feature_id`: non-empty string
- `steering.layer`: non-empty string
- `steering.strength`: number

Optional fields:

- `steering.preset`: string

Response shape compatible with Noetica `SteeringResult`:

```json
{
  "status": "not_configured",
  "baseline": "Write one short sentence about Paris.",
  "steered": "Write one short sentence about Paris.",
  "diff_summary": "Agent Machine local steering endpoint is not configured for activation.",
  "feature_id": "10200",
  "layer": "6-res-jb",
  "strength": 5
}
```

Allowed statuses:

- `applied`: real activation steering was applied. This is not returned by the Issue #32 stub.
- `not_configured`: sourceset/backend/model/SAE artifacts are unavailable.
- `noop`: request shape was accepted but no runtime intervention was applied.

## Health endpoints

The stub server provides:

```text
GET /health
GET /ready
```

Both return a secret-free JSON readiness payload indicating that the endpoint is stubbed and activation is not implemented.

## Stub commands

Render a response from a request JSON file:

```bash
agent-machine steer stub-response /tmp/steer-request.json --pretty
```

Serve the local contract stub:

```bash
agent-machine steer serve-stub --host 127.0.0.1 --port 8080 --status not_configured
```

Noetica can then be pointed at the stub:

```bash
NEURONPEDIA_BASE_URL=http://localhost:8080
```

No credentials are required for the stub unless Noetica itself enforces `NEURONPEDIA_API_KEY` before dispatch. The endpoint does not inspect or store credentials.

## Implementation posture

The Issue #32 endpoint is implemented as a native Agent Machine CLI stub using Python's standard library HTTP server.

It is not:

- an AgentPod workload
- a production inference provider
- a model loader
- an SAE artifact loader
- an activation-injection path

Future work:

- Issue #33 registers sourcesets such as `gpt2-small.res-jb`.
- Issue #34 implements controlled activation/injection behind policy and grant gates.

## Failure behavior

Invalid payloads return HTTP 400 with:

```json
{
  "error": "invalid_steer_request",
  "message": "..."
}
```

Unavailable sourcesets must return a valid `SteeringResult` with `status: not_configured`, not crash.

## Boundary

This contract exists so Noetica and Agent Machine do not drift. It allows Noetica to validate local endpoint routing, UI rendering, and evidence-chain behavior before real local SAE steering is available.
