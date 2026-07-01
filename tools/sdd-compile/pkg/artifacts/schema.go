// Package artifacts defines the shared result types for sdd-compile output.
package artifacts

// CompilationResult is written to stdout as JSON by the compile command.
type CompilationResult struct {
	Success          bool     `json:"success"`
	CoreMsgpackPath  string   `json:"core_msgpack_path"`
	ClientMsgpackPath string  `json:"client_msgpack_path"`
	CoreFingerprint  string   `json:"core_fingerprint"`
	ClientFingerprint string  `json:"client_fingerprint"`
	Errors           []string `json:"errors,omitempty"`
}

// ValidationResult is written to stdout as JSON by the validate command.
type ValidationResult struct {
	Valid   bool              `json:"valid"`
	Checks  []ValidationCheck `json:"checks"`
	Errors  []string          `json:"errors,omitempty"`
}

// ValidationCheck is a single validation step result.
type ValidationCheck struct {
	Name    string `json:"name"`
	OK      bool   `json:"ok"`
	Details string `json:"details,omitempty"`
}
