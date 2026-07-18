package cmd

import (
	"encoding/json"
	"os"

	"sdd-compile/internal/signing"

	"github.com/spf13/cobra"
)

var keygenCmd = &cobra.Command{
	Use:   "keygen",
	Short: "Generate a native Ed25519 key pair",
	Long:  "Generate an Ed25519 key pair: a PEM-encoded (PKCS8) private key and a PEM-encoded (PKIX) public key. Outputs JSON result to stdout.",
	RunE: func(cmd *cobra.Command, args []string) error {
		privPath, _ := cmd.Flags().GetString("priv")
		pubPath, _ := cmd.Flags().GetString("pub")

		if err := signing.GenerateKeyPair(privPath, pubPath); err != nil {
			out := map[string]any{"ok": false, "error": err.Error()}
			json.NewEncoder(os.Stdout).Encode(out)
			os.Exit(1)
		}

		out := map[string]any{
			"ok":               true,
			"private_key_path": privPath,
			"public_key_path":  pubPath,
		}
		return json.NewEncoder(os.Stdout).Encode(out)
	},
}

func init() {
	rootCmd.AddCommand(keygenCmd)
	keygenCmd.Flags().String("priv", "", "Output path for the PEM-encoded Ed25519 private key (PKCS8)")
	keygenCmd.Flags().String("pub", "", "Output path for the PEM-encoded Ed25519 public key (PKIX)")
	_ = keygenCmd.MarkFlagRequired("priv")
	_ = keygenCmd.MarkFlagRequired("pub")
}
