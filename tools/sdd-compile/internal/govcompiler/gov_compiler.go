// Package govcompiler ports Python's GovernanceCompiler to Go.
// It reads governance-core.json and governance-client.json, serializes them
// to msgpack (no magic header, plain msgpack), and writes metadata files.
package govcompiler

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"sdd-compile/internal/signing"

	shamaton "github.com/shamaton/msgpack/v2"
)

// GovCompiler reads governance JSON from compiledDir and serializes to msgpack.
type GovCompiler struct {
	compiledDir string
}

// CompilationResult mirrors Python's CompilationResult TypedDict.
type CompilationResult struct {
	CoreMsgpackFile     string
	ClientMsgpackFile   string
	CoreMetadata        string
	ClientMetadata      string
	CoreFingerprint     string
	ClientFingerprint   string
	CoreFingerprintSalt any
	CoreItemCount       int
	ClientItemCount     int
	CoreSignatureFile   string
	ClientSignatureFile string
	Signed              bool
	SignerKeyID         string
	SignatureFiles      []string
}

// New creates a GovCompiler reading JSON from compiledDir.
func New(compiledDir string) *GovCompiler {
	return &GovCompiler{compiledDir: compiledDir}
}

// Compile serializes governance JSON to msgpack and generates metadata files.
func (c *GovCompiler) Compile(outputDir string) (*CompilationResult, error) {
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return nil, fmt.Errorf("create output dir: %w", err)
	}
	auditDir := filepath.Join(outputDir, "audit")
	if err := os.MkdirAll(auditDir, 0o755); err != nil {
		return nil, fmt.Errorf("create audit dir: %w", err)
	}

	coreData, err := loadJSON(filepath.Join(c.compiledDir, "governance-core.json"))
	if err != nil {
		return nil, fmt.Errorf("load governance-core.json: %w", err)
	}
	clientData, err := loadJSON(filepath.Join(c.compiledDir, "governance-client.json"))
	if err != nil {
		return nil, fmt.Errorf("load governance-client.json: %w", err)
	}

	coreMsgpackBytes, err := serializeToMsgpack(coreData)
	if err != nil {
		return nil, fmt.Errorf("serialize core to msgpack: %w", err)
	}
	clientMsgpackBytes, err := serializeToMsgpack(clientData)
	if err != nil {
		return nil, fmt.Errorf("serialize client to msgpack: %w", err)
	}

	coreMsgpackFile := filepath.Join(outputDir, "governance-core.compiled.msgpack")
	clientMsgpackFile := filepath.Join(outputDir, "governance-client-template.compiled.msgpack")

	if err := os.WriteFile(coreMsgpackFile, coreMsgpackBytes, 0o644); err != nil {
		return nil, fmt.Errorf("write core msgpack: %w", err)
	}
	if err := os.WriteFile(clientMsgpackFile, clientMsgpackBytes, 0o644); err != nil {
		return nil, fmt.Errorf("write client msgpack: %w", err)
	}

	// Copy canonical JSON to output dir
	coreJSONOut := filepath.Join(outputDir, "governance-core.json")
	clientJSONOut := filepath.Join(outputDir, "governance-client.json")
	if err := writeJSON(coreJSONOut, coreData); err != nil {
		return nil, fmt.Errorf("write core JSON: %w", err)
	}
	if err := writeJSON(clientJSONOut, clientData); err != nil {
		return nil, fmt.Errorf("write client JSON: %w", err)
	}

	// Optional Ed25519 signing (env-driven, mirrors Python behavior)
	var (
		coreSignatureFile   string
		clientSignatureFile string
		compiledSigned      bool
		signerKeyID         string
		signatureFiles      []string
	)
	signingKey := os.Getenv("SDD_SIGNING_PRIVATE_KEY_FILE")
	if envTrue("SDD_SIGNING_REQUIRED") && signingKey == "" {
		return nil, fmt.Errorf("signing is required but SDD_SIGNING_PRIVATE_KEY_FILE is not set")
	}
	if signingKey != "" {
		signerKeyID = os.Getenv("SDD_SIGNING_KEY_ID")
		if signerKeyID == "" {
			signerKeyID = "dev-key"
		}
		coreSigPath, err := signing.SignArtifact(coreJSONOut, "master", signerKeyID, signingKey)
		if err != nil {
			return nil, fmt.Errorf("sign core JSON: %w", err)
		}
		clientSigPath, err := signing.SignArtifact(clientJSONOut, "client", signerKeyID, signingKey)
		if err != nil {
			return nil, fmt.Errorf("sign client JSON: %w", err)
		}
		coreSignatureFile = coreSigPath
		clientSignatureFile = clientSigPath
		compiledSigned = true
		signatureFiles = append(signatureFiles, coreSigPath, clientSigPath)
	}

	coreFingerprint := stringVal(coreData, "fingerprint")
	clientFingerprint := stringVal(clientData, "fingerprint")

	if err := generateMetadata(auditDir, "core", coreData, coreFingerprint, nil); err != nil {
		return nil, err
	}
	if err := generateMetadata(auditDir, "client-template", clientData, clientFingerprint, &coreFingerprint); err != nil {
		return nil, err
	}

	// Backward-compat: keep copies at compiled root
	for _, name := range []string{"metadata-core.json", "metadata-client-template.json"} {
		if err := copyFile(filepath.Join(auditDir, name), filepath.Join(outputDir, name)); err != nil {
			return nil, err
		}
	}

	return &CompilationResult{
		CoreMsgpackFile:     coreMsgpackFile,
		ClientMsgpackFile:   clientMsgpackFile,
		CoreMetadata:        filepath.Join(auditDir, "metadata-core.json"),
		ClientMetadata:      filepath.Join(auditDir, "metadata-client-template.json"),
		CoreFingerprint:     coreFingerprint,
		ClientFingerprint:   clientFingerprint,
		CoreFingerprintSalt: coreData["fingerprint"],
		CoreItemCount:       itemCount(coreData),
		ClientItemCount:     itemCount(clientData),
		CoreSignatureFile:   coreSignatureFile,
		ClientSignatureFile: clientSignatureFile,
		Signed:              compiledSigned,
		SignerKeyID:         signerKeyID,
		SignatureFiles:      signatureFiles,
	}, nil
}

// loadJSON reads a JSON file into map[string]any with proper number types.
func loadJSON(path string) (map[string]any, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	dec := json.NewDecoder(f)
	dec.UseNumber()
	var raw map[string]any
	if err := dec.Decode(&raw); err != nil {
		return nil, err
	}
	return convertNumbers(raw).(map[string]any), nil
}

// convertNumbers recursively converts json.Number to int64 or float64.
// This ensures msgpack encodes numbers as ints/floats rather than strings.
func convertNumbers(v any) any {
	switch x := v.(type) {
	case json.Number:
		if i, err := x.Int64(); err == nil {
			return i
		}
		if f, err := x.Float64(); err == nil {
			return f
		}
		return x.String()
	case map[string]any:
		out := make(map[string]any, len(x))
		for k, val := range x {
			out[k] = convertNumbers(val)
		}
		return out
	case []any:
		for i, val := range x {
			x[i] = convertNumbers(val)
		}
		return x
	}
	return v
}

// serializeToMsgpack encodes data as plain msgpack (no magic header), matching
// Python's msgpack.packb(data, use_bin_type=True).
func serializeToMsgpack(data map[string]any) ([]byte, error) {
	return shamaton.Marshal(data)
}

// writeJSON writes data as indented JSON to path.
func writeJSON(path string, data map[string]any) error {
	b, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o644)
}

// generateMetadata writes metadata-{fileType}.json to outputDir.
func generateMetadata(outputDir, fileType string, data map[string]any, fingerprint string, coreFP *string) error {
	meta := map[string]any{
		"version":               "3.0",
		"type":                  fileType,
		"generated_at":          time.Now().UTC().Format(time.RFC3339),
		"fingerprint":           fingerprint,
		"item_count":            int64(itemCount(data)),
		"items_by_type":         countByType(data),
		"items_by_criticality":  countByCriticality(data),
		"readonly":              fileType == "core",
		"customizable":          fileType == "client-template",
	}
	if fileType == "client-template" && coreFP != nil {
		meta["fingerprint_core_salt"] = *coreFP
	}
	path := filepath.Join(outputDir, "metadata-"+fileType+".json")
	b, err := json.MarshalIndent(meta, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal metadata: %w", err)
	}
	return os.WriteFile(path, b, 0o644)
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func itemCount(data map[string]any) int {
	items, ok := data["items"].([]any)
	if !ok {
		return 0
	}
	return len(items)
}

func countByType(data map[string]any) map[string]int {
	counts := map[string]int{}
	for _, item := range asList(data["items"]) {
		if m, ok := item.(map[string]any); ok {
			t, _ := m["type"].(string)
			if t == "" {
				t = "UNKNOWN"
			}
			counts[toUpper(t)]++
		}
	}
	return counts
}

func countByCriticality(data map[string]any) map[string]int {
	counts := map[string]int{}
	for _, item := range asList(data["items"]) {
		if m, ok := item.(map[string]any); ok {
			c, _ := m["criticality"].(string)
			if c == "" {
				c = "UNKNOWN"
			}
			counts[c]++
		}
	}
	return counts
}

func stringVal(data map[string]any, key string) string {
	v, _ := data[key].(string)
	return v
}

func asList(v any) []any {
	s, _ := v.([]any)
	return s
}

func toUpper(s string) string {
	out := make([]byte, len(s))
	for i := range s {
		c := s[i]
		if c >= 'a' && c <= 'z' {
			c -= 32
		}
		out[i] = c
	}
	return string(out)
}

func envTrue(key string) bool {
	v := os.Getenv(key)
	switch v {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}
