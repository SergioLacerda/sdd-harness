package tests

import (
	"testing"

	"sdd-compile/internal/parser"
)

const mandateDSL = `
- [M001] **Governance Mandate** All agents must follow governance.
- [M002] **Testing Mandate** All code must have tests.
`

const guidelineDSL = `
guideline G01 {
  type: "git"
  title: "Commit message format"
  description: "Use conventional commits"
}
guideline G02 {
  type: "testing"
  title: "Test coverage"
  description: "Maintain 80% coverage"
}
`

func TestParseMandatesCount(t *testing.T) {
	mandates := parser.ParseMandates(mandateDSL)
	if len(mandates) != 2 {
		t.Errorf("expected 2 mandates, got %d", len(mandates))
	}
}

func TestParseMandateFields(t *testing.T) {
	mandates := parser.ParseMandates(mandateDSL)
	if len(mandates) == 0 {
		t.Fatal("no mandates parsed")
	}
	m := mandates[0]
	if m.ID != "M001" {
		t.Errorf("expected ID M001, got %q", m.ID)
	}
	if m.Title != "Governance Mandate" {
		t.Errorf("expected title 'Governance Mandate', got %q", m.Title)
	}
	if m.Type != "HARD" {
		t.Errorf("expected type HARD, got %q", m.Type)
	}
}

func TestParseGuidelinesCount(t *testing.T) {
	guidelines := parser.ParseGuidelines(guidelineDSL)
	if len(guidelines) != 2 {
		t.Errorf("expected 2 guidelines, got %d", len(guidelines))
	}
}

func TestParseGuidelineFields(t *testing.T) {
	guidelines := parser.ParseGuidelines(guidelineDSL)
	if len(guidelines) == 0 {
		t.Fatal("no guidelines parsed")
	}
	g := guidelines[0]
	if g.ID != "G01" {
		t.Errorf("expected ID G01, got %q", g.ID)
	}
	if g.Title != "Commit message format" {
		t.Errorf("expected title 'Commit message format', got %q", g.Title)
	}
}

func TestParseMandateDefaultCategory(t *testing.T) {
	mandates := parser.ParseMandates(mandateDSL)
	for _, m := range mandates {
		if m.Category == "" {
			t.Errorf("mandate %s has empty category", m.ID)
		}
	}
}

func TestParseEmptyDSL(t *testing.T) {
	if mandates := parser.ParseMandates(""); len(mandates) != 0 {
		t.Errorf("empty DSL should yield no mandates, got %d", len(mandates))
	}
	if guidelines := parser.ParseGuidelines(""); len(guidelines) != 0 {
		t.Errorf("empty DSL should yield no guidelines, got %d", len(guidelines))
	}
}
