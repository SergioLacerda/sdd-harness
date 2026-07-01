package govcompiler

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// ValidationCheck is a named pass/fail check with detail text.
type ValidationCheck struct {
	Name    string
	OK      bool
	Details string
}

// ValidationResult is the structured output of ValidateCompilationDetailed.
type ValidationResult struct {
	OK     bool
	Errors []string
	Checks []ValidationCheck
}

// ValidateCompilation is a boolean wrapper around ValidateCompilationDetailed.
func (c *GovCompiler) ValidateCompilation(outputDir string) bool {
	return c.ValidateCompilationDetailed(outputDir).OK
}

// ValidateCompilationDetailed checks artifact presence, metadata consistency,
// fingerprint invariants, and signature symmetry.
func (c *GovCompiler) ValidateCompilationDetailed(outputDir string) ValidationResult {
	var checks []ValidationCheck
	var errors []string

	add := func(name string, ok bool, details string) {
		checks = append(checks, ValidationCheck{Name: name, OK: ok, Details: details})
		if !ok {
			errors = append(errors, details)
		}
	}

	coreMsgpack := filepath.Join(outputDir, "governance-core.compiled.msgpack")
	clientMsgpack := filepath.Join(outputDir, "governance-client-template.compiled.msgpack")
	coreMetaPath := filepath.Join(outputDir, "metadata-core.json")
	clientMetaPath := filepath.Join(outputDir, "metadata-client-template.json")

	// Artifact presence
	for label, path := range map[string]string{
		"core_msgpack_exists":   coreMsgpack,
		"client_msgpack_exists": clientMsgpack,
	} {
		if _, err := os.Stat(path); err != nil {
			add(label, false, "file not found: "+path)
		} else {
			add(label, true, path)
		}
	}
	if len(errors) > 0 {
		return ValidationResult{OK: false, Errors: errors, Checks: checks}
	}

	// Metadata presence
	for label, path := range map[string]string{
		"core_metadata_exists":   coreMetaPath,
		"client_metadata_exists": clientMetaPath,
	} {
		if _, err := os.Stat(path); err != nil {
			add(label, false, "file not found: "+path)
		} else {
			add(label, true, path)
		}
	}
	if len(errors) > 0 {
		return ValidationResult{OK: false, Errors: errors, Checks: checks}
	}

	// Parse metadata
	coreMeta, err := parseMetadata(coreMetaPath)
	if err != nil {
		add("core_metadata_parse", false, "could not parse: "+coreMetaPath)
		return ValidationResult{OK: false, Errors: errors, Checks: checks}
	}
	add("core_metadata_parse", true, "ok")

	clientMeta, err := parseMetadata(clientMetaPath)
	if err != nil {
		add("client_metadata_parse", false, "could not parse: "+clientMetaPath)
		return ValidationResult{OK: false, Errors: errors, Checks: checks}
	}
	add("client_metadata_parse", true, "ok")

	// Fingerprint validation
	coreFP, _ := coreMeta["fingerprint"].(string)
	clientFP, _ := clientMeta["fingerprint"].(string)

	if !isValidFingerprint(coreFP) {
		add("core_fingerprint_valid", false, "invalid core fingerprint: "+coreFP)
	} else {
		add("core_fingerprint_valid", true, coreFP)
	}

	if !isValidFingerprint(clientFP) {
		add("client_fingerprint_valid", false, "invalid client fingerprint: "+clientFP)
	} else {
		add("client_fingerprint_valid", true, clientFP)
		if coreFP == clientFP {
			add("fingerprints_different", false, "core and client fingerprints are identical")
		} else {
			add("fingerprints_different", true, "ok")
		}
		coreSalt, _ := clientMeta["fingerprint_core_salt"].(string)
		if coreSalt != coreFP {
			add("client_uses_core_salt", false, "core fingerprint not used as salt for client")
		} else {
			add("client_uses_core_salt", true, "ok")
		}
	}

	// Flag checks
	if coreMeta["readonly"] != true {
		add("core_readonly_true", false, "core metadata readonly flag not true")
	} else {
		add("core_readonly_true", true, "ok")
	}
	if clientMeta["customizable"] != true {
		add("client_customizable_true", false, "client metadata customizable flag not true")
	} else {
		add("client_customizable_true", true, "ok")
	}

	// Signature symmetry
	coreSig := filepath.Join(outputDir, "governance-core.json.sig")
	clientSig := filepath.Join(outputDir, "governance-client.json.sig")
	coreHasSig := fileExists(coreSig)
	clientHasSig := fileExists(clientSig)
	if !coreHasSig && !clientHasSig {
		add("signatures_consistent", true, "n/a")
	} else {
		if !coreHasSig {
			add("core_signature_exists", false, "missing core signature file: "+coreSig)
		} else {
			add("core_signature_exists", true, "ok")
		}
		if !clientHasSig {
			add("client_signature_exists", false, "missing client signature file: "+clientSig)
		} else {
			add("client_signature_exists", true, "ok")
		}
	}

	return ValidationResult{OK: len(errors) == 0, Errors: errors, Checks: checks}
}

func parseMetadata(path string) (map[string]any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return m, nil
}

func isValidFingerprint(s string) bool {
	return len(s) == 64
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
