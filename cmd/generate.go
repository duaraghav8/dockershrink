package cmd

import (
	"errors"
	"os"
	"path/filepath"

	"github.com/duaraghav8/dockershrink/internal/log"
	"github.com/duaraghav8/dockershrink/internal/project"
	"github.com/duaraghav8/dockershrink/internal/restrictedfilesystem"
	"github.com/spf13/cobra"
)

var generateCmd = &cobra.Command{
	Use:   "generate",
	Short: "Generates the Docker image definition for a project",
	Long: `Generates the Dockerfile and .dockerignore files for a NodeJS project.
OpenAI API key is required for this command.`,
	Run: runGenerate,
}

func init() {
	rootCmd.AddCommand(generateCmd)
}

func runGenerate(cmd *cobra.Command, args []string) {
	logger := log.NewLogger(debug)

	aiService, ok := getAIService(logger)
	if !ok {
		logger.Fatalf("OpenAI API key is required for this command")
	}

	packageJson, err := getPackageJson()
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			logger.Warnf("* No package.json file found")
		} else {
			logger.Fatalf("%v", err)
		}
	}

	cwd, err := os.Getwd()
	if err != nil {
		logger.Fatalf("Error getting current working directory: %v", err)
	}
	cwdTree, err := getDirTree(cwd)
	if err != nil {
		logger.Fatalf("%v", err)
	}

	projectDirFS := restrictedfilesystem.NewRestrictedFilesystem(
		cwd, cwdTree, "", "",
	)

	proj := project.NewProject(nil, nil, packageJson, projectDirFS)

	response, err := proj.GenerateDockerImage(aiService)
	if err != nil {
		logger.Fatalf("Error generating Docker image (use --debug to get more info): %s", err)
	}

	// write generated assets to output directory
	if err := os.MkdirAll(outputDir, os.ModePerm); err != nil {
		logger.Fatalf("Error creating output directory: %v", err)
	}
	dockerfileOutputPath := filepath.Join(outputDir, "Dockerfile")
	if err := os.WriteFile(dockerfileOutputPath, []byte(response.Dockerfile), os.ModePerm); err != nil {
		logger.Fatalf("Error writing optimized Dockerfile: %v", err)
	}
	dockerignoreOutputPath := filepath.Join(outputDir, ".dockerignore")
	if err := os.WriteFile(dockerignoreOutputPath, []byte(response.Dockerignore), os.ModePerm); err != nil {
		logger.Fatalf("Error writing optimized Dockerfile: %v", err)
	}

	logger.Infof("Generated Docker files saved to %s/", outputDir)
}
