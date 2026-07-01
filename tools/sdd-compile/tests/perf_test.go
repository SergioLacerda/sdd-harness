package tests

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"sdd-compile/internal/compiler"
)

func generate400Mandates() string {
	var sb strings.Builder
	for i := 1; i <= 400; i++ {
		sb.WriteString(fmt.Sprintf("- [M%03d] **Mandate %d** This is the description for mandate %d.\n", i, i, i))
	}
	return sb.String()
}

func TestCompile400MandatesUnder50ms(t *testing.T) {
	dsl := generate400Mandates()
	start := time.Now()
	out, m := compiler.Compile(dsl, false)
	elapsed := time.Since(start)

	if out == nil {
		t.Fatalf("compilation failed: %v", m.Errors)
	}
	if len(out.Mandates) != 400 {
		t.Errorf("expected 400 mandates, got %d", len(out.Mandates))
	}
	if elapsed > 50*time.Millisecond {
		t.Errorf("compilation took %v, expected <50ms", elapsed)
	}
}

func BenchmarkCompile400Mandates(b *testing.B) {
	dsl := generate400Mandates()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		compiler.Compile(dsl, false)
	}
}
