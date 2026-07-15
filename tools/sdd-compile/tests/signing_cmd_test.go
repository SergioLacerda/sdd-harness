// Package tests contains smoke tests for the sdd-compile binary.
package tests

import (
	"crypto/ed25519"
	"crypto/x509"
	"encoding/pem"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func writeSigningKeyPair(t *testing.T, dir string) (privPath, pubPath string) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatalf("generate key: %v", err)
	}

	privBytes, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		t.Fatalf("marshal private key: %v", err)
	}
	privPath = filepath.Join(dir, "test.key")
	if err := os.WriteFile(privPath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privBytes}), 0o600); err != nil {
		t.Fatalf("write private key: %v", err)
	}

	pubBytes, err := x509.MarshalPKIXPublicKey(pub)
	if err != nil {
		t.Fatalf("marshal public key: %v", err)
	}
	pubPath = filepath.Join(dir, "test.pub.pem")
	if err := os.WriteFile(pubPath, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pubBytes}), 0o644); err != nil {
		t.Fatalf("write public key: %v", err)
	}
	return privPath, pubPath
}

func TestSignCommandProducesVerifiableManifest(t *testing.T) {
	dir := t.TempDir()
	privPath, pubPath := writeSigningKeyPair(t, dir)

	artifactPath := filepath.Join(dir, "governance-core.json")
	if err := os.WriteFile(artifactPath, []byte(`{"a":1}`), 0o644); err != nil {
		t.Fatalf("write artifact: %v", err)
	}

	signOut, err := exec.Command(
		"go", "run", "..", "sign",
		"--artifact", artifactPath,
		"--key", privPath,
		"--key-id", "test-01",
		"--profile", "master",
	).CombinedOutput()
	if err != nil {
		t.Fatalf("sign command failed: %v\n%s", err, signOut)
	}
	if !strings.Contains(string(signOut), `"ok":true`) {
		t.Fatalf("expected ok:true, got: %s", signOut)
	}

	sigManifest, err := os.ReadFile(artifactPath + ".sig")
	if err != nil {
		t.Fatalf("read sig manifest: %v", err)
	}

	pubPEM, err := os.ReadFile(pubPath)
	if err != nil {
		t.Fatalf("read pub key: %v", err)
	}

	// Extract payload_hash and signature without a JSON dependency here;
	// reuse the same fields the Python bridge reads.
	payloadHash := extractJSONField(t, sigManifest, "payload_hash")
	signature := extractJSONField(t, sigManifest, "signature")

	verifyRequest := `{"public_key_pem":` + jsonQuote(string(pubPEM)) + `,"message":` + jsonQuote(payloadHash) + `,"signature_b64":"` + signature + `"}`
	cmd := exec.Command("go", "run", "..", "verify")
	cmd.Stdin = strings.NewReader(verifyRequest)
	verifyOut, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("verify command failed: %v\n%s", err, verifyOut)
	}
	if !strings.Contains(string(verifyOut), `"valid":true`) {
		t.Errorf("expected valid:true, got: %s", verifyOut)
	}
}

func TestVerifyCommandRejectsTamperedSignature(t *testing.T) {
	dir := t.TempDir()
	_, pubPath := writeSigningKeyPair(t, dir)
	pubPEM, _ := os.ReadFile(pubPath)

	verifyRequest := `{"public_key_pem":` + jsonQuote(string(pubPEM)) + `,"message":"deadbeef","signature_b64":"aW52YWxpZC1zaWc="}`
	cmd := exec.Command("go", "run", "..", "verify")
	cmd.Stdin = strings.NewReader(verifyRequest)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("verify command failed: %v\n%s", err, out)
	}
	if !strings.Contains(string(out), `"valid":false`) {
		t.Errorf("expected valid:false for tampered signature, got: %s", out)
	}
}

func TestSignCommandFailsCleanlyOnMissingKey(t *testing.T) {
	dir := t.TempDir()
	artifactPath := filepath.Join(dir, "artifact.json")
	os.WriteFile(artifactPath, []byte(`{}`), 0o644)

	out, err := exec.Command(
		"go", "run", "..", "sign",
		"--artifact", artifactPath,
		"--key", filepath.Join(dir, "missing.key"),
		"--key-id", "k",
		"--profile", "master",
	).CombinedOutput()
	if err == nil {
		t.Error("expected non-zero exit for missing key file")
	}
	if !strings.Contains(string(out), `"ok":false`) {
		t.Errorf("expected JSON failure result, got: %q", out)
	}
}

// extractJSONField does a minimal string-based extraction to avoid pulling in
// an extra dependency for these black-box CLI tests.
func extractJSONField(t *testing.T, jsonBytes []byte, field string) string {
	t.Helper()
	s := string(jsonBytes)
	marker := `"` + field + `": "`
	idx := strings.Index(s, marker)
	if idx == -1 {
		t.Fatalf("field %q not found in %s", field, s)
	}
	start := idx + len(marker)
	end := strings.Index(s[start:], `"`)
	if end == -1 {
		t.Fatalf("unterminated field %q in %s", field, s)
	}
	return s[start : start+end]
}

func jsonQuote(s string) string {
	replacer := strings.NewReplacer("\\", "\\\\", "\"", "\\\"", "\n", "\\n", "\r", "\\r")
	return `"` + replacer.Replace(s) + `"`
}
