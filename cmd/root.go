package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	openaiApiKey    string
	apiKey					string
	baseUrl   			string
	model     			string
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
		"DEPRECATED: Use --api-key instead. OpenAI API key (alternatively, set the OPENAI_API_KEY environment variable)",
	)
	rootCmd.PersistentFlags().StringVar(
		&apiKey,
		"api-key",
		"",
		"API key for OpenAI-compatible services (env: DOCKERSHRINK_API_KEY)",
	)
	rootCmd.PersistentFlags().StringVar(
		&baseUrl,
		"base-url",
		"",
		"Base URL for model endpoint (default: https://api.openai.com/v1, env: DOCKERSHRINK_BASE_URL)",
	)
	rootCmd.PersistentFlags().StringVar(
		&model,
		"model",
		"",
		"Model to use (default: gpt-4o-2024-08-06, env: DOCKERSHRINK_MODEL)",
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
