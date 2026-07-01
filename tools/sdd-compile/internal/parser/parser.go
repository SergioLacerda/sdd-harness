// Package parser extracts mandates and guidelines from DSL text using a line scanner.
package parser

import (
	"regexp"
	"strconv"
	"strings"
)

var (
	mandateHeaderRE  = regexp.MustCompile(`^\s*-\s*\[([MP]\d{3})\]\s+\*\*(.*?)\*\*(.*)$`)
	guidelineBlockRE = regexp.MustCompile(`guideline\s+(G\d+)\s*\{([^}]+)\}`)
	categoryRE       = regexp.MustCompile(`(?i)category:\s*(\w+)`)
	rationaleRE      = regexp.MustCompile(`(?i)rationale:\s*"([^"]+)"`)
	rationalePlainRE = regexp.MustCompile(`(?i)rationale:\s*(.+)`)
	commandsRE       = regexp.MustCompile(`(?i)commands:\s*\[([^\]]+)\]`)
)

// Mandate represents a parsed mandate entry.
type Mandate struct {
	ID                 string
	Type               string
	Title              string
	Description        string
	Category           string
	Rationale          string
	ValidationCommands []string
}

// Guideline represents a parsed guideline entry.
type Guideline struct {
	ID          string
	Type        string
	Title       string
	Description string
	Category    string
	Tags        []string
	Examples    []string
}

// ParseMandates extracts all mandate entries from dslText using a line scanner.
func ParseMandates(dslText string) []Mandate {
	lines := strings.Split(dslText, "\n")
	var mandates []Mandate

	i := 0
	for i < len(lines) {
		m := mandateHeaderRE.FindStringSubmatch(lines[i])
		if m == nil {
			i++
			continue
		}

		id := m[1]
		title := strings.TrimSpace(m[2])
		firstRest := strings.TrimSpace(m[3])

		// Collect continuation lines until next mandate header or separator
		descLines := []string{}
		if firstRest != "" {
			descLines = append(descLines, firstRest)
		}
		j := i + 1
		for j < len(lines) {
			next := strings.TrimSpace(lines[j])
			if mandateHeaderRE.MatchString(lines[j]) || next == "---" {
				break
			}
			descLines = append(descLines, lines[j])
			j++
		}

		description := strings.TrimSpace(strings.Join(descLines, "\n"))

		category := "core"
		if cm := categoryRE.FindStringSubmatch(description); cm != nil {
			category = strings.ToLower(cm[1])
		}

		rationale := ""
		if rm := rationaleRE.FindStringSubmatch(description); rm != nil {
			rationale = rm[1]
		} else if rm := rationalePlainRE.FindStringSubmatch(description); rm != nil {
			candidate := strings.TrimSpace(rm[1])
			// Avoid capturing lines that are mandate headers as rationale
			if !strings.HasPrefix(candidate, "-") {
				rationale = candidate
			}
		}

		var validationCommands []string
		if cm := commandsRE.FindStringSubmatch(description); cm != nil {
			for _, c := range strings.Split(cm[1], ",") {
				c = strings.TrimSpace(strings.Trim(strings.TrimSpace(c), `"'`))
				if c != "" {
					validationCommands = append(validationCommands, c)
				}
			}
		}

		mandates = append(mandates, Mandate{
			ID:                 id,
			Type:               "HARD",
			Title:              title,
			Description:        description,
			Category:           category,
			Rationale:          rationale,
			ValidationCommands: validationCommands,
		})
		i = j
	}
	return mandates
}

// ParseGuidelines extracts all guideline entries from dslText.
// Guidelines use brace-delimited blocks so a single regex suffices.
func ParseGuidelines(dslText string) []Guideline {
	var guidelines []Guideline
	for _, m := range guidelineBlockRE.FindAllStringSubmatch(dslText, -1) {
		id := strings.TrimSpace(m[1])
		body := m[2]
		guidelines = append(guidelines, Guideline{
			ID:          id,
			Type:        extractField(body, "type"),
			Title:       extractField(body, "title"),
			Description: extractField(body, "description"),
			Category:    defaultStr(extractField(body, "category"), "general"),
			Tags:        extractArray(body, "tags"),
			Examples:    extractArray(body, "examples"),
		})
	}
	return guidelines
}

// extractField extracts a scalar value from a DSL body block.
// Tries quoted form first, then plain unquoted form.
func extractField(text, name string) string {
	pattern := regexp.MustCompile(`(?s)` + regexp.QuoteMeta(name) + `\s*:\s*"([^"]*)(?:"|$)`)
	if m := pattern.FindStringSubmatch(text); m != nil {
		if v := strings.TrimSpace(m[1]); v != "" {
			return v
		}
	}
	plain := regexp.MustCompile(regexp.QuoteMeta(name) + `\s*:\s*([^,}\n]*?)(?:,|}|\n|$)`)
	if m := plain.FindStringSubmatch(text); m != nil {
		if v := strings.TrimSpace(m[1]); v != "" {
			return v
		}
	}
	return ""
}

// extractArray extracts an array field from a DSL body block.
func extractArray(text, name string) []string {
	pattern := regexp.MustCompile(`(?s)` + regexp.QuoteMeta(name) + `\s*:\s*\[([^\]]*)\]`)
	m := pattern.FindStringSubmatch(text)
	if m == nil {
		return nil
	}
	var items []string
	for _, item := range strings.Split(m[1], ",") {
		item = strings.TrimSpace(strings.Trim(strings.TrimSpace(item), `"'`))
		if item != "" {
			items = append(items, item)
		}
	}
	return items
}

func defaultStr(s, def string) string {
	if s == "" {
		return def
	}
	return s
}

// IDToNum converts a mandate/guideline ID string (e.g. "M001") to its numeric part.
func IDToNum(id string) int {
	if len(id) < 2 {
		return 0
	}
	n, _ := strconv.Atoi(id[1:])
	return n
}
