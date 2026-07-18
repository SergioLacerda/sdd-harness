package signing

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"
)

// GenerateKeyPair creates a new Ed25519 key pair and writes it as PEM files:
// the private key as PKCS8 at privPath (mode 0600), the public key as
// PKIX/SPKI at pubPath. The output matches the OpenSSL
// `genpkey -algorithm ed25519` / `pkey -pubout` files this replaces, so
// existing keys and the sign/verify contract are unaffected.
func GenerateKeyPair(privPath, pubPath string) error {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("generate key: %w", err)
	}

	privBytes, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		return fmt.Errorf("marshal private key: %w", err)
	}
	privPEM := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privBytes})

	pubBytes, err := x509.MarshalPKIXPublicKey(pub)
	if err != nil {
		return fmt.Errorf("marshal public key: %w", err)
	}
	pubPEM := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pubBytes})

	for _, path := range []string{privPath, pubPath} {
		if dir := filepath.Dir(path); dir != "." {
			if err := os.MkdirAll(dir, 0o755); err != nil {
				return fmt.Errorf("create output directory: %w", err)
			}
		}
	}
	if err := os.WriteFile(privPath, privPEM, 0o600); err != nil {
		return fmt.Errorf("write private key: %w", err)
	}
	if err := os.WriteFile(pubPath, pubPEM, 0o644); err != nil {
		return fmt.Errorf("write public key: %w", err)
	}
	return nil
}
