package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"sdd-compile/internal/signing"

	"github.com/spf13/cobra"
)

type verifyInput struct {
	PublicKeyPEM string `json:"public_key_pem"`
	Message      string `json:"message"`
	SignatureB64 string `json:"signature_b64"`
}

var verifyCmd = &cobra.Command{
	Use:   "verify",
	Short: "Verify an Ed25519 signature (reads JSON request from stdin)",
	Long:  "Verify an Ed25519 signature against a PEM-encoded public key. Reads {\"public_key_pem\", \"message\", \"signature_b64\"} as JSON on stdin. Outputs JSON result to stdout.",
	RunE: func(cmd *cobra.Command, args []string) error {
		var input verifyInput
		if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
			out := map[string]any{"ok": false, "error": fmt.Sprintf("invalid stdin request: %v", err)}
			json.NewEncoder(os.Stdout).Encode(out)
			os.Exit(1)
		}

		valid, err := signing.VerifySignature(input.PublicKeyPEM, []byte(input.Message), input.SignatureB64)
		if err != nil {
			// A malformed key/signature is a verification failure, not a tool
			// failure: report valid=false so callers treat it as an untrusted
			// signature rather than a crashed process.
			out := map[string]any{"ok": true, "valid": false, "error": err.Error()}
			return json.NewEncoder(os.Stdout).Encode(out)
		}

		out := map[string]any{"ok": true, "valid": valid}
		return json.NewEncoder(os.Stdout).Encode(out)
	},
}

func init() {
	rootCmd.AddCommand(verifyCmd)
}
