# Architecture

Ruleset version: `{{ standalone_ruleset_version }}`

Function/file size, naming, typing, and dependency-direction rules that apply regardless of language. Language-specific detail lives in `python.md` and `go.md`.

## Function and File Size

- Functions: 4–20 lines. One thing, done well. Split when longer.
- Files: under 500 lines. Split by responsibility when exceeded.
- One responsibility per module. When a file is hard to name, it does too much.

## Naming

- Names must be specific and unique. Target: no more than a handful of matches when you search the codebase for the name.
- Avoid `data`, `handler`, `Manager`, `Helper`, `Utils`, `Common` — names that could mean anything mean nothing.
- Names reveal intention. A reader should be able to guess what a function does from its name alone.

## Types

- Types must be explicit. No `any`, no untyped dict/map, no untyped function signatures.
- Typed code is unambiguous for both humans and anyone reading it later.
- Validate external input at system boundaries — never trust raw input from outside the process.

## Duplication

- No code duplication. Extract shared logic into named functions or modules.
- Three similar lines is a pattern. Four is a function.
- Duplication in logic should be eliminated; duplication in configuration is sometimes correct.

## Control Flow

- Early returns over nested ifs. Prefer no more than 2 levels of indentation.
- Guard clauses at the top. Happy path at the bottom.
- Error messages must include the offending value and the expected shape.

## Dependencies

- Inject dependencies via constructor or parameter.
- Never via global state, module-level singletons, or import-time mutation.
- Wrap third-party libraries behind a thin interface you own, so a library swap touches one place.
