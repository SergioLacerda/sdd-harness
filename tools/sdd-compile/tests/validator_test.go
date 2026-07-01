package tests

import (
	"strings"
	"testing"

	"sdd-compile/internal/validator"
)

const validMandateDSL = `
- [M001] **First mandate** Some description here.
- [M002] **Second mandate** Another description.
`

const nonSequentialMandateDSL = `
- [M001] **First mandate** Some description.
- [M003] **Third mandate** Skipped M002.
`

const missingTitleDSL = `
- [M001] **** Empty title.
`

func TestValidDSLHasNoIssues(t *testing.T) {
	issues := validator.ValidateDSL(validMandateDSL)
	if len(issues) != 0 {
		t.Errorf("valid DSL should have no issues, got: %+v", issues)
	}
}

func TestNonSequentialMandateIDs(t *testing.T) {
	issues := validator.ValidateDSL(nonSequentialMandateDSL)
	found := false
	for _, iss := range issues {
		if iss.Code == "MANDATE_IDS_NOT_SEQUENTIAL" {
			found = true
		}
	}
	if !found {
		t.Error("expected MANDATE_IDS_NOT_SEQUENTIAL issue")
	}
}

func TestEmptyDSLHasNoIssues(t *testing.T) {
	issues := validator.ValidateDSL("")
	if len(issues) != 0 {
		t.Errorf("empty DSL should have no issues, got: %+v", issues)
	}
}

func TestIssueHasRequiredFields(t *testing.T) {
	issues := validator.ValidateDSL(nonSequentialMandateDSL)
	if len(issues) == 0 {
		t.Skip("no issues to check")
	}
	iss := issues[0]
	if iss.Code == "" {
		t.Error("issue Code must not be empty")
	}
	if iss.Message == "" {
		t.Error("issue Message must not be empty")
	}
	if iss.Hint == "" {
		t.Error("issue Hint must not be empty")
	}
}

func TestGuidelineNonSequential(t *testing.T) {
	dsl := `
guideline G01 {
  type: "git"
  title: "First"
}
guideline G03 {
  type: "git"
  title: "Third"
}
`
	issues := validator.ValidateDSL(dsl)
	found := false
	for _, iss := range issues {
		if iss.Code == "GUIDELINE_IDS_NOT_SEQUENTIAL" {
			found = true
		}
	}
	if !found {
		t.Errorf("expected GUIDELINE_IDS_NOT_SEQUENTIAL, got %+v", issues)
	}
}

func TestGuidelineMissingRequiredField(t *testing.T) {
	dsl := `
guideline G01 {
  title: "Missing type"
}
`
	issues := validator.ValidateDSL(dsl)
	found := false
	for _, iss := range issues {
		if strings.Contains(iss.Code, "MISSING_FIELD") {
			found = true
		}
	}
	if !found {
		t.Errorf("expected GUIDELINE_MISSING_FIELD, got %+v", issues)
	}
}
