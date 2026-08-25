package parser

import (
	"reflect"
	"testing"
)

func TestParseMandates_SingleMandateFields(t *testing.T) {
	dsl := `
- [M001] **Governance Mandate** All agents must follow governance.
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	m := mandates[0]
	if m.ID != "M001" {
		t.Errorf("ID = %q, want M001", m.ID)
	}
	if m.Type != "HARD" {
		t.Errorf("Type = %q, want HARD", m.Type)
	}
	if m.Title != "Governance Mandate" {
		t.Errorf("Title = %q, want %q", m.Title, "Governance Mandate")
	}
	if m.Description != "All agents must follow governance." {
		t.Errorf("Description = %q", m.Description)
	}
	if m.Category != "core" {
		t.Errorf("Category = %q, want default %q", m.Category, "core")
	}
}

func TestParseMandates_MultipleMandatesCount(t *testing.T) {
	dsl := `
- [M001] **First** desc one.
- [M002] **Second** desc two.
- [P003] **Third** desc three.
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 3 {
		t.Fatalf("expected 3 mandates, got %d", len(mandates))
	}
	if mandates[2].ID != "P003" {
		t.Errorf("mandates[2].ID = %q, want P003 (P-prefixed IDs must match too)", mandates[2].ID)
	}
}

func TestParseMandates_NoMatchReturnsEmpty(t *testing.T) {
	dsl := "just some prose\nwith no mandate markers at all\n"
	mandates := ParseMandates(dsl)
	if len(mandates) != 0 {
		t.Errorf("expected 0 mandates, got %d", len(mandates))
	}
}

func TestParseMandates_MalformedHeaderNotMatched(t *testing.T) {
	cases := []string{
		"- [X001] **Bad prefix** not M or P",
		"- [M1] **Too short id** wrong digit count",
		"[M001] **Missing dash** no leading bullet",
		"- M001 **Missing brackets** no square brackets",
	}
	for _, dsl := range cases {
		mandates := ParseMandates(dsl)
		if len(mandates) != 0 {
			t.Errorf("dsl %q: expected 0 mandates for malformed header, got %d", dsl, len(mandates))
		}
	}
}

func TestParseMandates_ExplicitCategory(t *testing.T) {
	dsl := `
- [M001] **Title** Some text.
  category: security
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].Category != "security" {
		t.Errorf("Category = %q, want security", mandates[0].Category)
	}
}

func TestParseMandates_CategoryIsCaseInsensitiveAndLowered(t *testing.T) {
	dsl := `
- [M001] **Title** Some text.
  CATEGORY: SECURITY
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].Category != "security" {
		t.Errorf("Category = %q, want lowercased security", mandates[0].Category)
	}
}

func TestParseMandates_QuotedRationaleTakesPrecedence(t *testing.T) {
	dsl := `
- [M001] **Title** Some text.
  rationale: "the quoted reason"
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].Rationale != "the quoted reason" {
		t.Errorf("Rationale = %q, want %q", mandates[0].Rationale, "the quoted reason")
	}
}

func TestParseMandates_PlainRationaleFallback(t *testing.T) {
	dsl := `
- [M001] **Title** Some text.
  rationale: the plain reason
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].Rationale != "the plain reason" {
		t.Errorf("Rationale = %q, want %q", mandates[0].Rationale, "the plain reason")
	}
}

func TestParseMandates_PlainRationaleRejectsMandateHeaderLookalike(t *testing.T) {
	// Guards the `!strings.HasPrefix(candidate, "-")` boundary on line 86:
	// a plain rationale candidate that itself looks like a bullet/header
	// must not be captured as rationale text.
	dsl := `
- [M001] **Title** Some text.
  rationale: - [M002] **Not actually a rationale**
`
	mandates := ParseMandates(dsl)
	if len(mandates) == 0 {
		t.Fatal("no mandates parsed")
	}
	if mandates[0].Rationale != "" {
		t.Errorf("Rationale = %q, want empty (candidate starts with '-')", mandates[0].Rationale)
	}
}

func TestParseMandates_CommandsList(t *testing.T) {
	dsl := `
- [M001] **Title** Some text.
  commands: ["make test", "make lint"]
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	want := []string{"make test", "make lint"}
	if !reflect.DeepEqual(mandates[0].ValidationCommands, want) {
		t.Errorf("ValidationCommands = %#v, want %#v", mandates[0].ValidationCommands, want)
	}
}

func TestParseMandates_NoCommandsIsNil(t *testing.T) {
	dsl := `
- [M001] **Title** Some text, no commands field.
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if mandates[0].ValidationCommands != nil {
		t.Errorf("ValidationCommands = %#v, want nil", mandates[0].ValidationCommands)
	}
}

func TestParseMandates_DescriptionStopsAtSeparator(t *testing.T) {
	dsl := `
- [M001] **Title** line one.
  line two.
---
this line must not be part of the description
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 1 {
		t.Fatalf("expected 1 mandate, got %d", len(mandates))
	}
	if got := mandates[0].Description; got != "line one.\n  line two." {
		t.Errorf("Description = %q, want it to stop before the --- separator", got)
	}
}

func TestParseMandates_DescriptionStopsAtNextHeader(t *testing.T) {
	dsl := `
- [M001] **First** line one.
  line two.
- [M002] **Second** other text.
`
	mandates := ParseMandates(dsl)
	if len(mandates) != 2 {
		t.Fatalf("expected 2 mandates, got %d", len(mandates))
	}
	if got := mandates[0].Description; got != "line one.\n  line two." {
		t.Errorf("mandates[0].Description = %q, want it to stop before the next header", got)
	}
	if mandates[1].Title != "Second" {
		t.Errorf("mandates[1].Title = %q, want Second", mandates[1].Title)
	}
}

func TestParseGuidelines_SingleGuidelineFields(t *testing.T) {
	dsl := `
guideline G01 {
  type: "git"
  title: "Commit message format"
  description: "Use conventional commits"
  category: "workflow"
  tags: [commit, format]
  examples: [feat, fix]
}
`
	guidelines := ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	g := guidelines[0]
	if g.ID != "G01" {
		t.Errorf("ID = %q, want G01", g.ID)
	}
	if g.Type != "git" {
		t.Errorf("Type = %q, want git", g.Type)
	}
	if g.Title != "Commit message format" {
		t.Errorf("Title = %q", g.Title)
	}
	if g.Description != "Use conventional commits" {
		t.Errorf("Description = %q", g.Description)
	}
	if g.Category != "workflow" {
		t.Errorf("Category = %q, want workflow", g.Category)
	}
	want := []string{"commit", "format"}
	if !reflect.DeepEqual(g.Tags, want) {
		t.Errorf("Tags = %#v, want %#v", g.Tags, want)
	}
	wantEx := []string{"feat", "fix"}
	if !reflect.DeepEqual(g.Examples, wantEx) {
		t.Errorf("Examples = %#v, want %#v", g.Examples, wantEx)
	}
}

func TestParseGuidelines_MultipleGuidelinesCount(t *testing.T) {
	dsl := `
guideline G01 {
  type: "git"
  title: "One"
}
guideline G02 {
  type: "testing"
  title: "Two"
}
`
	guidelines := ParseGuidelines(dsl)
	if len(guidelines) != 2 {
		t.Fatalf("expected 2 guidelines, got %d", len(guidelines))
	}
	if guidelines[1].ID != "G02" {
		t.Errorf("guidelines[1].ID = %q, want G02", guidelines[1].ID)
	}
}

func TestParseGuidelines_NoMatchReturnsEmpty(t *testing.T) {
	guidelines := ParseGuidelines("no guideline blocks here at all")
	if len(guidelines) != 0 {
		t.Errorf("expected 0 guidelines, got %d", len(guidelines))
	}
}

func TestParseGuidelines_MissingCategoryDefaultsToGeneral(t *testing.T) {
	dsl := `
guideline G01 {
  type: "git"
  title: "No category field here"
}
`
	guidelines := ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	if guidelines[0].Category != "general" {
		t.Errorf("Category = %q, want default general", guidelines[0].Category)
	}
}

func TestParseGuidelines_MissingArraysAreNil(t *testing.T) {
	dsl := `
guideline G01 {
  type: "git"
  title: "No tags or examples"
}
`
	guidelines := ParseGuidelines(dsl)
	if len(guidelines) != 1 {
		t.Fatalf("expected 1 guideline, got %d", len(guidelines))
	}
	if guidelines[0].Tags != nil {
		t.Errorf("Tags = %#v, want nil", guidelines[0].Tags)
	}
	if guidelines[0].Examples != nil {
		t.Errorf("Examples = %#v, want nil", guidelines[0].Examples)
	}
}

func TestExtractField_QuotedTakesPrecedenceOverPlain(t *testing.T) {
	got := extractField(`title: "Quoted Title"`, "title")
	if got != "Quoted Title" {
		t.Errorf("extractField quoted = %q, want %q", got, "Quoted Title")
	}
}

func TestExtractField_PlainFallback(t *testing.T) {
	got := extractField("title: Plain Title, other: x", "title")
	if got != "Plain Title" {
		t.Errorf("extractField plain = %q, want %q", got, "Plain Title")
	}
}

func TestExtractField_MissingFieldReturnsEmpty(t *testing.T) {
	got := extractField("other: value", "title")
	if got != "" {
		t.Errorf("extractField missing = %q, want empty", got)
	}
}

func TestExtractField_EmptyQuotedFallsThroughToPlain(t *testing.T) {
	// The quoted branch requires a non-empty trimmed value (line 140's
	// `if v := ...; v != ""` guard) before returning — an empty quoted
	// string must fall through to the plain-pattern attempt instead of
	// short-circuiting to "".
	got := extractField(`title: "" fallback: title: Recovered`, "fallback")
	if got != "title: Recovered" {
		t.Errorf("extractField empty-quoted fallthrough = %q, want %q", got, "title: Recovered")
	}
}

func TestExtractArray_ParsesCommaSeparatedItems(t *testing.T) {
	got := extractArray(`tags: [a, "b", 'c']`, "tags")
	want := []string{"a", "b", "c"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("extractArray = %#v, want %#v", got, want)
	}
}

func TestExtractArray_MissingFieldReturnsNil(t *testing.T) {
	got := extractArray("no array here", "tags")
	if got != nil {
		t.Errorf("extractArray missing = %#v, want nil", got)
	}
}

func TestExtractArray_EmptyBracketsReturnsNil(t *testing.T) {
	got := extractArray("tags: []", "tags")
	if got != nil {
		t.Errorf("extractArray empty = %#v, want nil", got)
	}
}

func TestDefaultStr(t *testing.T) {
	if got := defaultStr("", "fallback"); got != "fallback" {
		t.Errorf("defaultStr(empty) = %q, want fallback", got)
	}
	if got := defaultStr("value", "fallback"); got != "value" {
		t.Errorf("defaultStr(non-empty) = %q, want value", got)
	}
}

func TestIDToNum(t *testing.T) {
	cases := []struct {
		id   string
		want int
	}{
		{"M001", 1},
		{"P042", 42},
		{"G123", 123},
		{"M000", 0},
		{"M1", 1},   // len == 2, the boundary of `len(id) < 2`
		{"X", 0},    // len < 2
		{"", 0},     // empty
		{"MABC", 0}, // non-numeric suffix
	}
	for _, c := range cases {
		if got := IDToNum(c.id); got != c.want {
			t.Errorf("IDToNum(%q) = %d, want %d", c.id, got, c.want)
		}
	}
}
