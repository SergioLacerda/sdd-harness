// Package validator checks DSL syntax and semantics before compilation.
package validator

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

var (
	mandateHeaderRE = regexp.MustCompile(`^\s*-\s*\[([MP]\d{3})\]\s+\*\*(.*?)\*\*(.*)$`)
	guidelineRE     = regexp.MustCompile(`guideline\s+(G\d+)\s*\{([^}]+)\}`)
)

// Issue is a structured validation error.
type Issue struct {
	Code    string
	Message string
	Line    int
	Column  int
	Snippet string
	Hint    string
}

// ValidateDSL returns Issues found in dslText. An empty slice means valid.
func ValidateDSL(dslText string) []Issue {
	var issues []Issue
	lines := strings.Split(dslText, "\n")

	locate := func(token string) (int, int, string) {
		for i, line := range lines {
			col := strings.Index(line, token)
			if col >= 0 {
				snip := line
				if len(snip) > 200 {
					snip = snip[:200]
				}
				return i + 1, col + 1, snip
			}
		}
		snip := ""
		if len(lines) > 0 {
			snip = lines[0]
			if len(snip) > 200 {
				snip = snip[:200]
			}
		}
		return 1, 1, snip
	}

	// Collect mandate headers via line scanner
	type mandateHeader struct {
		id    string
		title string
		num   int
	}
	var headers []mandateHeader

	for _, line := range lines {
		m := mandateHeaderRE.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		id := m[1]
		title := strings.TrimSpace(m[2])
		num, _ := strconv.Atoi(id[1:])
		headers = append(headers, mandateHeader{id: id, title: title, num: num})
	}

	// Sequential ID check
	for i := 0; i+1 < len(headers); i++ {
		if headers[i+1].num != headers[i].num+1 {
			nums := make([]int, len(headers))
			for j, h := range headers {
				nums[j] = h.num
			}
			ln, col, snip := locate(fmt.Sprintf("[%s]", headers[i+1].id))
			issues = append(issues, Issue{
				Code:    "MANDATE_IDS_NOT_SEQUENTIAL",
				Message: fmt.Sprintf("Mandate IDs not sequential: %v", nums),
				Line:    ln,
				Column:  col,
				Snippet: snip,
				Hint:    "Use sequential IDs without gaps (e.g. M001, M002, M003).",
			})
			break
		}
	}

	// Missing title check
	for _, h := range headers {
		if h.title == "" {
			ln, col, snip := locate(fmt.Sprintf("[%s]", h.id))
			issues = append(issues, Issue{
				Code:    "MANDATE_MISSING_TITLE",
				Message: fmt.Sprintf("Mandate %s: missing field 'title'", h.id),
				Line:    ln,
				Column:  col,
				Snippet: snip,
				Hint:    "Provide a non-empty title in '**title**' format.",
			})
		}
	}

	// Guideline checks (single-line blocks — no lookahead needed)
	guidelineMatches := guidelineRE.FindAllStringSubmatch(dslText, -1)
	if len(guidelineMatches) > 0 {
		var guidIDs []int
		for _, m := range guidelineMatches {
			n, _ := strconv.Atoi(m[1][1:])
			guidIDs = append(guidIDs, n)
		}

		sequential := true
		for i, id := range guidIDs {
			if id != i+1 {
				sequential = false
				break
			}
		}
		if !sequential {
			ln, col, snip := locate(guidelineMatches[0][1])
			issues = append(issues, Issue{
				Code:    "GUIDELINE_IDS_NOT_SEQUENTIAL",
				Message: fmt.Sprintf("Guideline IDs not sequential: %v", guidIDs),
				Line:    ln,
				Column:  col,
				Snippet: snip,
				Hint:    "Use sequential guideline IDs (G01, G02, G03...).",
			})
		}

		required := []string{"type", "title"}
		for _, m := range guidelineMatches {
			guidID := m[1]
			body := m[2]
			for _, req := range required {
				if !strings.Contains(body, req+":") {
					ln, col, snip := locate(guidID)
					issues = append(issues, Issue{
						Code:    "GUIDELINE_MISSING_FIELD",
						Message: fmt.Sprintf("Guideline %s: missing field '%s'", guidID, req),
						Line:    ln,
						Column:  col,
						Snippet: snip,
						Hint:    fmt.Sprintf("Add required field '%s:' inside guideline block.", req),
					})
				}
			}
		}
	}

	return issues
}
