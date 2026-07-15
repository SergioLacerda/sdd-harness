package cmd

import (
	"encoding/json"
	"os"

	"sdd-compile/internal/signing"

	"github.com/spf13/cobra"
)

var signCmd = &cobra.Command{
	Use:   "sign",
	Short: "Sign an artifact with a native Ed25519 private key",
	Long:  "Sign an artifact file with a PEM-encoded (PKCS8) Ed25519 private key and write a compatible .sig manifest. Outputs JSON result to stdout.",
	RunE: func(cmd *cobra.Command, args []string) error {
		artifact, _ := cmd.Flags().GetString("artifact")
		keyPath, _ := cmd.Flags().GetString("key")
		keyID, _ := cmd.Flags().GetString("key-id")
		profile, _ := cmd.Flags().GetString("profile")

		sigPath, err := signing.SignArtifact(artifact, profile, keyID, keyPath)
		if err != nil {
			out := map[string]any{"ok": false, "error": err.Error()}
			json.NewEncoder(os.Stdout).Encode(out)
			os.Exit(1)
		}

		out := map[string]any{"ok": true, "sig_path": sigPath}
		return json.NewEncoder(os.Stdout).Encode(out)
	},
}

func init() {
	rootCmd.AddCommand(signCmd)
	signCmd.Flags().String("artifact", "", "Path to the artifact file to sign")
	signCmd.Flags().String("key", "", "Path to the PEM-encoded Ed25519 private key (PKCS8)")
	signCmd.Flags().String("key-id", "", "Signing key identifier to embed in the signature manifest")
	signCmd.Flags().String("profile", "", "Artifact profile: master or client")
	_ = signCmd.MarkFlagRequired("artifact")
	_ = signCmd.MarkFlagRequired("key")
	_ = signCmd.MarkFlagRequired("key-id")
	_ = signCmd.MarkFlagRequired("profile")
}
