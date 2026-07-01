// Package cmd implements the CLI commands for the sdd-compile binary.
package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "sdd-compile",
	Short: "SDD governance compiler",
	Long:  "sdd-compile compiles SDD governance JSON artifacts to msgpack format.",
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the sdd-compile version",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("sdd-compile 0.2.0")
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}

// Execute runs the root command.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
