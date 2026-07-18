package signing

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestGenerateKeyPairWritesPEMFiles(t *testing.T) {
	dir := t.TempDir()
	privPath := filepath.Join(dir, "dev-01.key")
	pubPath := filepath.Join(dir, "dev-01.pub.pem")

	if err := GenerateKeyPair(privPath, pubPath); err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}

	privBytes, err := os.ReadFile(privPath)
	if err != nil {
		t.Fatalf("read private key: %v", err)
	}
	if !strings.Contains(string(privBytes), "BEGIN PRIVATE KEY") {
		t.Errorf("private key is not PKCS8 PEM: %s", privBytes)
	}

	pubBytes, err := os.ReadFile(pubPath)
	if err != nil {
		t.Fatalf("read public key: %v", err)
	}
	if !strings.Contains(string(pubBytes), "BEGIN PUBLIC KEY") {
		t.Errorf("public key is not PKIX PEM: %s", pubBytes)
	}

	if runtime.GOOS != "windows" {
		info, err := os.Stat(privPath)
		if err != nil {
			t.Fatalf("stat private key: %v", err)
		}
		if perm := info.Mode().Perm(); perm != 0o600 {
			t.Errorf("private key mode = %o, want 0600", perm)
		}
	}
}

func TestGenerateKeyPairCreatesParentDirectories(t *testing.T) {
	dir := t.TempDir()
	privPath := filepath.Join(dir, "trust", "nested", "dev-01.key")
	pubPath := filepath.Join(dir, "trust", "nested", "dev-01.pub.pem")

	if err := GenerateKeyPair(privPath, pubPath); err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}
	if _, err := os.Stat(privPath); err != nil {
		t.Errorf("private key not created: %v", err)
	}
	if _, err := os.Stat(pubPath); err != nil {
		t.Errorf("public key not created: %v", err)
	}
}

func TestGenerateKeyPairSignVerifyRoundTrip(t *testing.T) {
	dir := t.TempDir()
	privPath := filepath.Join(dir, "dev-01.key")
	pubPath := filepath.Join(dir, "dev-01.pub.pem")

	if err := GenerateKeyPair(privPath, pubPath); err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}

	artifactPath := filepath.Join(dir, "artifact.json")
	if err := os.WriteFile(artifactPath, []byte(`{"a":1}`), 0o644); err != nil {
		t.Fatalf("write artifact: %v", err)
	}

	sigPath, err := SignArtifact(artifactPath, "client", "dev-01", privPath)
	if err != nil {
		t.Fatalf("SignArtifact with generated key: %v", err)
	}

	sigBytes, err := os.ReadFile(sigPath)
	if err != nil {
		t.Fatalf("read sig file: %v", err)
	}
	manifest := struct {
		PayloadHash string `json:"payload_hash"`
		Signature   string `json:"signature"`
	}{}
	if err := json.Unmarshal(sigBytes, &manifest); err != nil {
		t.Fatalf("parse manifest: %v", err)
	}

	pubPEM, err := os.ReadFile(pubPath)
	if err != nil {
		t.Fatalf("read public key: %v", err)
	}
	valid, err := VerifySignature(string(pubPEM), []byte(manifest.PayloadHash), manifest.Signature)
	if err != nil {
		t.Fatalf("VerifySignature: %v", err)
	}
	if !valid {
		t.Error("expected signature from generated key to verify successfully")
	}
}
