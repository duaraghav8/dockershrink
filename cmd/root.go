package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	openaiApiKey    string
	debug           bool
	packageJsonPath string
	outputDir       string
)

var rootCmd = &cobra.Command{
	Use:   "dockershrink",
	Short: "Dockershrink is an AI tool to reduce the size of Docker images",
}

func Execute() {
	rootCmd.PersistentFlags().StringVarP(&outputDir, "output-dir", "o", "dockershrink.out", "Directory to save optimized files")
	rootCmd.PersistentFlags().StringVar(
		&openaiApiKey,
		"openai-api-key",
		"",
		"OpenAI API key (alternatively, set the OPENAI_API_KEY environment variable)",
	)
	rootCmd.PersistentFlags().StringVar(
		&packageJsonPath, "package-json", "", "Path to package.json (default: ./package.json or ./src/package.json)",
	)
	rootCmd.PersistentFlags().BoolVarP(&debug, "debug", "d", false, "Output detailed logs for debugging")

	rootCmd.CompletionOptions.DisableDefaultCmd = true

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
