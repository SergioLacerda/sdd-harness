// Package compiler orchestrates DSL validation, parsing, and output generation.
package compiler

import (
	"fmt"
	"time"

	"sdd-compile/internal/parser"
	"sdd-compile/internal/pool"
	"sdd-compile/internal/validator"
)

// CategoryMap mirrors the Python DSLValidator.CATEGORY_MAP.
var CategoryMap = map[string]int{
	"architecture":  1,
	"core":          1,
	"general":       2,
	"performance":   3,
	"security":      4,
	"git":           5,
	"documentation": 6,
	"testing":       7,
	"naming":        8,
	"code-style":    9,
}

// Metrics captures compilation performance data.
type Metrics struct {
	InputSize        int
	OutputSize       int
	CompilationTimeMs float64
	StringPoolSize   int
	MandatesCompiled int
	GuidelinesCompiled int
	UniqueStrings    int
	Errors           []string
	Issues           []validator.Issue
}

// CompiledOutput is the in-memory representation of a compiled DSL.
type CompiledOutput struct {
	FormatVersion string                   `json:"format_version"`
	CompiledAt    string                   `json:"compiled_at"`
	Mandates      []map[string]interface{} `json:"mandates"`
	Guidelines    []map[string]interface{} `json:"guidelines"`
	StringPool    []string                 `json:"string_pool"`
	Categories    map[string]int           `json:"categories"`
}

// Compile converts dslText into a CompiledOutput.
// Returns nil, non-empty Metrics.Errors on validation failure.
func Compile(dslText string, validate bool) (*CompiledOutput, Metrics) {
	start := time.Now()
	m := Metrics{InputSize: len([]byte(dslText))}

	if validate {
		issues := validator.ValidateDSL(dslText)
		if len(issues) > 0 {
			m.Issues = issues
			for _, iss := range issues {
				m.Errors = append(m.Errors, iss.Message)
			}
			return nil, m
		}
	}

	mandates := parser.ParseMandates(dslText)
	guidelines := parser.ParseGuidelines(dslText)

	sp := pool.New()

	compiledMandates := make([]map[string]interface{}, 0, len(mandates))
	for _, mandate := range mandates {
		var n int
		fmt.Sscanf(mandate.ID[1:], "%d", &n)
		entry := map[string]interface{}{
			"id":           n,
			"type":         mandate.Type,
			"title_idx":    sp.Add(mandate.Title),
			"description_idx": sp.Add(mandate.Description),
			"category":     categoryCode(mandate.Category),
			"rationale_idx": sp.Add(mandate.Rationale),
			"validation_commands": mandate.ValidationCommands,
		}
		compiledMandates = append(compiledMandates, entry)
	}

	compiledGuidelines := make([]map[string]interface{}, 0, len(guidelines))
	for _, g := range guidelines {
		var n int
		fmt.Sscanf(g.ID[1:], "%d", &n)
		var exIdx interface{}
		if len(g.Examples) > 0 {
			idxList := make([]int, 0, len(g.Examples))
			for _, ex := range g.Examples {
				idxList = append(idxList, sp.Add(ex))
			}
			exIdx = idxList
		}
		entry := map[string]interface{}{
			"id":           n,
			"type":         g.Type,
			"title_idx":    sp.Add(g.Title),
			"description_idx": sp.Add(g.Description),
			"category":     categoryCode(g.Category),
			"examples_idx": exIdx,
		}
		compiledGuidelines = append(compiledGuidelines, entry)
	}

	out := &CompiledOutput{
		FormatVersion: "3.1",
		CompiledAt:    time.Now().UTC().Format("2006-01-02T15:04:05Z"),
		Mandates:      compiledMandates,
		Guidelines:    compiledGuidelines,
		StringPool:    sp.GetArray(),
		Categories:    CategoryMap,
	}

	m.CompilationTimeMs = float64(time.Since(start).Microseconds()) / 1000.0
	m.MandatesCompiled = len(compiledMandates)
	m.GuidelinesCompiled = len(compiledGuidelines)
	m.StringPoolSize = sp.Size()
	m.UniqueStrings = sp.Size()

	return out, m
}

func categoryCode(category string) int {
	if code, ok := CategoryMap[category]; ok {
		return code
	}
	return 2
}
