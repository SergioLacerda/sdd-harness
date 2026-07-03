package tests

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"sdd-compile/internal/govcompiler"
)

// writePathologicalCompiledDir writes a governance-core.json with nesting far
// beyond what any real governance artifact needs, plus a minimal valid
// governance-client.json, into a fresh compiledDir.
func writePathologicalCompiledDir(t *testing.T, depth int) string {
	t.Helper()
	dir := t.TempDir()

	// Build a deeply nested map: {"a": {"a": {"a": ... }}}
	var nested any = map[string]any{"leaf": true}
	for i := 0; i < depth; i++ {
		nested = map[string]any{"a": nested}
	}
	core := map[string]any{
		"fingerprint": strings.Repeat("a", 64),
		"items":       []any{nested},
	}
	client := map[string]any{
		"fingerprint": strings.Repeat("b", 64),
		"items":       []any{},
	}

	writeJSONFixture(t, filepath.Join(dir, "governance-core.json"), core)
	writeJSONFixture(t, filepath.Join(dir, "governance-client.json"), client)
	return dir
}

func writeJSONFixture(t *testing.T, path string, data any) {
	t.Helper()
	b, err := json.Marshal(data)
	if err != nil {
		t.Fatalf("marshal fixture: %v", err)
	}
	if err := os.WriteFile(path, b, 0o644); err != nil {
		t.Fatalf("write fixture: %v", err)
	}
}

func TestGovCompilerRejectsPathologicallyDeepInput(t *testing.T) {
	src := writePathologicalCompiledDir(t, 1000)
	out := t.TempDir()

	_, err := govcompiler.New(src).Compile(out)
	if err == nil {
		t.Fatal("expected Compile() to reject a pathologically deep governance-core.json, got nil error")
	}
	if !strings.Contains(err.Error(), "nesting depth") {
		t.Errorf("expected error to mention nesting depth, got: %v", err)
	}
}

func TestGovCompilerAcceptsShallowInput(t *testing.T) {
	src := writePathologicalCompiledDir(t, 3)
	out := t.TempDir()

	if _, err := govcompiler.New(src).Compile(out); err != nil {
		t.Fatalf("expected Compile() to accept shallow input, got error: %v", err)
	}
}
