package tests

// Cross-language contract tests: verify Go-compiled msgpack is readable by Python.
// These tests invoke a Python subprocess to unpack the Go-generated msgpack and
// confirm fingerprint values match what was in the source JSON.

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"sdd-compile/internal/govcompiler"
)

// pythonAvailable returns true if python3 with msgpack is importable.
func pythonAvailable() bool {
	cmd := exec.Command("python3", "-c", "import msgpack")
	return cmd.Run() == nil
}

func TestGoOutputReadableByPython(t *testing.T) {
	if !pythonAvailable() {
		t.Skip("python3 with msgpack not available")
	}
	src := sddCompiledDir(t)
	out := t.TempDir()

	if _, err := govcompiler.New(src).Compile(out); err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	script := fmt.Sprintf(`
import msgpack, sys
with open(%q, "rb") as f:
    data = msgpack.unpackb(f.read(), raw=False)
assert isinstance(data, dict), f"expected dict, got {type(data)}"
assert "fingerprint" in data, "fingerprint key missing"
print("ok:", data["fingerprint"][:8])
`, filepath.Join(out, "governance-core.compiled.msgpack"))

	out2, err := exec.Command("python3", "-c", script).CombinedOutput()
	if err != nil {
		t.Fatalf("Python readability check failed:\n%s\n%v", out2, err)
	}
	if !strings.HasPrefix(string(out2), "ok:") {
		t.Errorf("unexpected Python output: %s", out2)
	}
}

func TestGoFingerprintMatchesPythonSource(t *testing.T) {
	if !pythonAvailable() {
		t.Skip("python3 with msgpack not available")
	}
	src := sddCompiledDir(t)
	out := t.TempDir()

	result, err := govcompiler.New(src).Compile(out)
	if err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	// Read the source JSON fingerprint directly
	srcCoreJSON := filepath.Join(src, "governance-core.json")
	rawJSON, err := os.ReadFile(srcCoreJSON)
	if err != nil {
		t.Fatalf("read source JSON: %v", err)
	}
	var srcData map[string]any
	if err := json.Unmarshal(rawJSON, &srcData); err != nil {
		t.Fatalf("parse source JSON: %v", err)
	}
	srcFingerprint, _ := srcData["fingerprint"].(string)

	if result.CoreFingerprint != srcFingerprint {
		t.Errorf("Go fingerprint %q != source JSON fingerprint %q", result.CoreFingerprint, srcFingerprint)
	}

	// Verify Python also sees the same fingerprint in the Go-compiled msgpack
	script := fmt.Sprintf(`
import msgpack
with open(%q, "rb") as f:
    data = msgpack.unpackb(f.read(), raw=False)
assert data.get("fingerprint") == %q, f"fingerprint mismatch: {{data.get('fingerprint')}}"
print("match")
`, filepath.Join(out, "governance-core.compiled.msgpack"), srcFingerprint)

	out2, err := exec.Command("python3", "-c", script).CombinedOutput()
	if err != nil {
		t.Fatalf("Python fingerprint check failed:\n%s\n%v", out2, err)
	}
}

func TestGoClientMsgpackReadableByPython(t *testing.T) {
	if !pythonAvailable() {
		t.Skip("python3 with msgpack not available")
	}
	src := sddCompiledDir(t)
	out := t.TempDir()

	if _, err := govcompiler.New(src).Compile(out); err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	script := fmt.Sprintf(`
import msgpack
with open(%q, "rb") as f:
    data = msgpack.unpackb(f.read(), raw=False)
assert isinstance(data, dict), f"expected dict, got {type(data)}"
assert "fingerprint" in data, "fingerprint key missing"
assert "fingerprint_core_salt" in data, "fingerprint_core_salt key missing"
print("ok")
`, filepath.Join(out, "governance-client-template.compiled.msgpack"))

	out2, err := exec.Command("python3", "-c", script).CombinedOutput()
	if err != nil {
		t.Fatalf("Python client readability check failed:\n%s\n%v", out2, err)
	}
}
