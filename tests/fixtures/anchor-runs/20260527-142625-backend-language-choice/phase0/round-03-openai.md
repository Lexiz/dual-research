## Stance

I am not ready to emit `STATUS: AGREED` because Claude’s final interpretation introduced one new, material overstatement about .NET Native AOT: the direction is right, but the artifact treats AOT-compiled .NET as categorically in the Go/Rust operational tier. [U] Microsoft’s own ASP.NET Core Native AOT examples show very strong startup/memory gains, including 48 ms startup and 57% lower working set for a simple API, but a more complex sample with JWT auth and PostgreSQL shows 115 ms startup and 37% lower working set, and the same docs warn that not all ASP.NET Core features or libraries are AOT-compatible. [V] ([devblogs.microsoft.com](https://devblogs.microsoft.com/dotnet/announcing-asp-net-core-in-dotnet-8/)) The final interpretation should preserve the mitigation but avoid making Native AOT a blanket assumption for this service until the actual Azure SDK, OpenTelemetry, MCP, auth, Npgsql, document-processing, and provider-abstraction dependency set is checked for AOT compatibility. [U]

## Status

STATUS: IN_PROGRESS  
RAISED_THIS_TURN: [D-dotnet-aot-scope]  
ADDRESSED_THIS_TURN: []  
RESOLVED_THIS_TURN: []  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 0  
OPEN_DISAGREEMENTS: 1  
ADDRESSED_QUESTIONS: 0  
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me

None.

## Ratifying my own items

None.

## New items I'm raising

### RAISE D-dotnet-aot-scope
kind: disagreement
body: |
  I disagree with carrying forward the artifact language that says “C#/.NET with Native AOT ... achieves sub-50ms cold starts and 60–80% memory reduction vs JIT, putting it in the same performance tier as Go and Rust” as a general scoring rule. [U] The direction is correct — Native AOT materially improves .NET startup and memory footprint — but the statement is too absolute for this service. [U]

  Microsoft’s ASP.NET Core .NET 8 announcement reports 48 ms startup and 57% lower working set for a simple API, but its more complex API sample with model validation, OpenAPI, JWT authorization, configuration binding, and PostgreSQL via Npgsql reports 115 ms startup and 37% lower working set. [V] It also explicitly warns that not all ASP.NET Core features and commonly used libraries are compatible with Native AOT, and Microsoft’s Native AOT deployment overview lists limitations including no dynamic loading, no runtime code generation, trimming constraints, and limited support for some ASP.NET Core features. [V] ([devblogs.microsoft.com](https://devblogs.microsoft.com/dotnet/announcing-asp-net-core-in-dotnet-8/))

  This matters because the Document Verification Service is not a trivial minimal API: it needs OAuth/OIDC, OpenTelemetry, Azure SDKs, Npgsql/Postgres RLS patterns, Redis, Key Vault, Blob, MCP, document parsing, and AI-provider abstractions. [U] The final document should therefore say: “.NET Native AOT is a strong 2.4 mitigation and may put a carefully constrained API/worker subset near Go/Rust startup characteristics, but C# should be scored on standard .NET operational fit unless the chosen framework and dependency graph are verified AOT-compatible.” [U]

  Resolving this one way versus the other changes the final document’s 2.4 scoring: .NET either receives an unconditional Go/Rust-level operational score, or a conditional strong score with an explicit AOT-compatibility validation dependency. [U]
anchor_type: quote
anchor_text: "putting it in the same performance tier as Go and Rust"
evidence_required: true
> quote: putting it in the same performance tier as Go and Rust