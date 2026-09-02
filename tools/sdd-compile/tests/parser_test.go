package tests

import (
	"strings"
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

func TestParseMandateExplicitCategory(t *testing.T) {
	dsl := "- [M010] **Security Mandate** All secrets must be encrypted. category: security\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Category; got != "security" {
		t.Errorf("expected category %q, got %q", "security", got)
	}
}

func TestParseMandateCategoryIsCaseInsensitiveAndLowercased(t *testing.T) {
	dsl := "- [M011] **Mixed Case** Body text. Category: SECURITY\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Category; got != "security" {
		t.Errorf("expected lowercased category %q, got %q", "security", got)
	}
}

func TestParseMandateDefaultCategoryIsCore(t *testing.T) {
	dsl := "- [M012] **No Category** Just a plain description.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Category; got != "core" {
		t.Errorf("expected default category %q, got %q", "core", got)
	}
}

func TestParseMandateRationaleQuoted(t *testing.T) {
	dsl := "- [M020] **Quoted Rationale** Body. rationale: \"because security\"\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Rationale; got != "because security" {
		t.Errorf("expected rationale %q, got %q", "because security", got)
	}
}

func TestParseMandateRationalePlainFallback(t *testing.T) {
	dsl := "- [M021] **Plain Rationale** Body. rationale: because it matters\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Rationale; got != "because it matters" {
		t.Errorf("expected rationale %q, got %q", "because it matters", got)
	}
}

func TestParseMandateRationalePlainDoesNotCaptureNextHeader(t *testing.T) {
	// The plain-rationale fallback must not swallow a following mandate
	// header line as if it were the rationale text (guarded by the
	// "!strings.HasPrefix(candidate, \"-\")" check in parser.go).
	dsl := "- [M022] **No Rationale Here** Body with no rationale field.\n" +
		"- [M023] **Second Mandate** Another body.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 2 {
		t.Fatalf("expected 2 mandates, got %d", len(mandates))
	}
	if got := mandates[0].Rationale; got != "" {
		t.Errorf("expected empty rationale (not the next header), got %q", got)
	}
}

func TestParseMandateValidationCommands(t *testing.T) {
	dsl := "- [M030] **Has Commands** Body. commands: [\"make test\", \"make lint\"]\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	want := []string{"make test", "make lint"}
	got := mandates[0].ValidationCommands
	if len(got) != len(want) {
		t.Fatalf("expected %d commands, got %d (%v)", len(want), len(got), got)
	}
	for i, c := range want {
		if got[i] != c {
			t.Errorf("command %d: expected %q, got %q", i, c, got[i])
		}
	}
}

func TestParseMandateNoValidationCommandsIsNil(t *testing.T) {
	dsl := "- [M031] **No Commands** Just a body.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].ValidationCommands; got != nil {
		t.Errorf("expected nil validation commands, got %v", got)
	}
}

func TestParseMandateMultilineDescriptionStopsAtSeparator(t *testing.T) {
	dsl := "- [M040] **Multiline** First line.\n" +
		"Second line.\n" +
		"Third line.\n" +
		"---\n" +
		"Not part of the mandate.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	desc := mandates[0].Description
	if !strings.Contains(desc, "First line.") || !strings.Contains(desc, "Third line.") {
		t.Errorf("expected description to include all continuation lines, got %q", desc)
	}
	if strings.Contains(desc, "Not part of the mandate") {
		t.Errorf("description must stop at the --- separator, got %q", desc)
	}
}

func TestParseMandateMultilineDescriptionStopsAtNextHeader(t *testing.T) {
	dsl := "- [M041] **First** Line one.\n" +
		"Line two.\n" +
		"- [M042] **Second** Its own body.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 2 {
		t.Fatalf("expected 2 mandates, got %d", len(mandates))
	}
	if strings.Contains(mandates[0].Description, "Its own body") {
		t.Errorf("first mandate must not absorb the second mandate's body, got %q", mandates[0].Description)
	}
	if mandates[1].ID != "M042" {
		t.Errorf("expected second mandate ID M042, got %q", mandates[1].ID)
	}
}

func TestParseMandateNonMatchingLinesAreSkipped(t *testing.T) {
	dsl := "this is not a mandate line\n" +
		"neither is this one\n" +
		"- [M050] **Real Mandate** Body.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate (garbage lines skipped), got %d", len(mandates))
	}
	if mandates[0].ID != "M050" {
		t.Errorf("expected ID M050, got %q", mandates[0].ID)
	}
}

func TestParseMandateProhibitionType(t *testing.T) {
	// mandateHeaderRE accepts both M (mandate) and P (prohibition) prefixes,
	// but ParseMandates always assigns Type "HARD" regardless of the letter —
	// this pins that (possibly surprising) current behavior explicitly.
	dsl := "- [P001] **A Prohibition** Must not do X.\n"
	mandates := parser.ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].ID != "P001" {
		t.Errorf("expected ID P001, got %q", mandates[0].ID)
	}
	if mandates[0].Type != "HARD" {
		t.Errorf("expected type HARD even for P-prefixed IDs, got %q", mandates[0].Type)
	}
}

func TestParseGuidelineTagsAndExamples(t *testing.T) {
	dsl := `guideline G10 {
  type: "style"
  title: "Naming"
  tags: [naming, style, "python"]
  examples: ["snake_case", "PascalCase"]
}
`
	guidelines := parser.ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	g := guidelines[0]
	wantTags := []string{"naming", "style", "python"}
	if len(g.Tags) != len(wantTags) {
		t.Fatalf("expected %d tags, got %d (%v)", len(wantTags), len(g.Tags), g.Tags)
	}
	for i, tag := range wantTags {
		if g.Tags[i] != tag {
			t.Errorf("tag %d: expected %q, got %q", i, tag, g.Tags[i])
		}
	}
	wantExamples := []string{"snake_case", "PascalCase"}
	if len(g.Examples) != len(wantExamples) {
		t.Fatalf("expected %d examples, got %d (%v)", len(wantExamples), len(g.Examples), g.Examples)
	}
}

func TestParseGuidelineDefaultCategoryIsGeneral(t *testing.T) {
	dsl := `guideline G20 {
  type: "misc"
  title: "No category set"
}
`
	guidelines := parser.ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	if got := guidelines[0].Category; got != "general" {
		t.Errorf("expected default category %q, got %q", "general", got)
	}
}

func TestParseGuidelineExplicitCategoryOverridesDefault(t *testing.T) {
	dsl := `guideline G21 {
  type: "misc"
  category: security
}
`
	guidelines := parser.ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	if got := guidelines[0].Category; got != "security" {
		t.Errorf("expected category %q, got %q", "security", got)
	}
}

func TestParseGuidelinePlainFieldFallback(t *testing.T) {
	// extractField tries the quoted form first, then falls back to an
	// unquoted plain value terminated by comma/brace/newline.
	dsl := `guideline G30 {
  type: testing
}
`
	guidelines := parser.ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	if got := guidelines[0].Type; got != "testing" {
		t.Errorf("expected plain-form type %q, got %q", "testing", got)
	}
}

func TestParseGuidelineNoMatchYieldsNil(t *testing.T) {
	if guidelines := parser.ParseGuidelines("no guideline blocks here"); guidelines != nil {
		t.Errorf("expected nil guidelines for non-matching input, got %v", guidelines)
	}
}

func TestIDToNum(t *testing.T) {
	cases := []struct {
		id   string
		want int
	}{
		{"M001", 1},
		{"M042", 42},
		{"G100", 100},
		{"P007", 7},
		{"M", 0},    // len < 2
		{"", 0},     // empty
		{"MXYZ", 0}, // non-numeric suffix — strconv.Atoi fails, error ignored, returns 0
	}
	for _, c := range cases {
		if got := parser.IDToNum(c.id); got != c.want {
			t.Errorf("IDToNum(%q) = %d, want %d", c.id, got, c.want)
		}
	}
}
