package tests

import (
	"os"
	"path/filepath"
	"testing"

	"sdd-compile/internal/state"
)

func TestStateLoadEmpty(t *testing.T) {
	dir := t.TempDir()
	s, err := state.Load(filepath.Join(dir, "nonexistent.json"))
	if err != nil {
		t.Fatalf("Load should not error on missing file: %v", err)
	}
	if s == nil {
		t.Fatal("Load should return non-nil state")
	}
}

func TestStateSourceChangedOnNewFile(t *testing.T) {
	dir := t.TempDir()
	s, _ := state.Load(filepath.Join(dir, "state.json"))

	f := filepath.Join(dir, "source.dsl")
	os.WriteFile(f, []byte("content"), 0o644)

	if !s.SourceChanged("src", f) {
		t.Error("new file should be reported as changed")
	}
}

func TestStateSourceNotChangedAfterUpdate(t *testing.T) {
	dir := t.TempDir()
	statePath := filepath.Join(dir, "state.json")
	s, _ := state.Load(statePath)

	f := filepath.Join(dir, "source.dsl")
	os.WriteFile(f, []byte("content"), 0o644)

	s.UpdateSource("src", f)
	s.Save()

	s2, _ := state.Load(statePath)
	if s2.SourceChanged("src", f) {
		t.Error("unchanged file should not be reported as changed after update")
	}
}
