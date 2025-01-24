package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

// Default version string, to be overridden by Makefile during production build
var Version = "dev"

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of DockerShrink",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("DockerShrink CLI version:", Version)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
