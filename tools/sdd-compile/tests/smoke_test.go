// Package tests contains smoke tests for the sdd-compile binary.
package tests

import (
	"os/exec"
	"strings"
	"testing"
)

func TestVersionCommand(t *testing.T) {
	out, err := exec.Command("go", "run", "..", "version").CombinedOutput()
	if err != nil {
		t.Fatalf("version command failed: %v\n%s", err, out)
	}
	if !strings.Contains(string(out), "sdd-compile") {
		t.Errorf("version output missing 'sdd-compile': %q", string(out))
	}
}

func TestCompileCommandFailsCleanlyOnMissingInput(t *testing.T) {
	cmd := exec.Command("go", "run", "..", "compile", "--input", "/nonexistent-input-dir")
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Error("expected non-zero exit for missing input dir")
	}
	if !strings.Contains(string(out), "\"ok\":false") {
		t.Errorf("expected JSON failure result, got: %q", string(out))
	}
}

func TestValidateCommandFailsCleanlyOnMissingDir(t *testing.T) {
	cmd := exec.Command("go", "run", "..", "validate", "--dir", "/nonexistent-validate-dir")
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Error("expected non-zero exit for missing artifacts dir")
	}
	if !strings.Contains(string(out), "\"ok\":false") {
		t.Errorf("expected JSON failure result, got: %q", string(out))
	}
}
