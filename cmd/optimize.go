package cmd

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/duaraghav8/dockershrink/internal/dockerfile"
	"github.com/duaraghav8/dockershrink/internal/dockerignore"
	"github.com/duaraghav8/dockershrink/internal/log"
	"github.com/duaraghav8/dockershrink/internal/project"
	"github.com/duaraghav8/dockershrink/internal/restrictedfilesystem"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

var (
	dockerfilePath   string
	dockerignorePath string
)

var optimizeCmd = &cobra.Command{
	Use:   "optimize",
	Short: "Optimizes the Docker image definition for a project",
	Long: `Optimizes the Dockerfile and .dockerignore files for a NodeJS project and provides recommendations where applicable.
OpenAI API key is optional for this command, but it is recommended to provide one for better results.`,
	Run: runOptimize,
}

func init() {
	optimizeCmd.Flags().StringVar(&dockerfilePath, "dockerfile", "Dockerfile", "Path to Dockerfile")
	optimizeCmd.Flags().StringVar(&dockerignorePath, "dockerignore", ".dockerignore", "Path to .dockerignore")

	rootCmd.AddCommand(optimizeCmd)
}

func runOptimize(cmd *cobra.Command, args []string) {
	logger := log.NewLogger(debug)
	aiService, _ := getAIService(logger)

	// Read Dockerfile
	dockerfileContents, err := os.ReadFile(dockerfilePath)
	if err != nil {
		logger.Fatalf("Error reading %s: %v", dockerfilePath, err)
	}

	dockerfileObject, err := dockerfile.NewDockerfile(string(dockerfileContents))

	// Read .dockerignore if it exists
	var dockerignoreObject *dockerignore.Dockerignore

	if _, err := os.Stat(dockerignorePath); err == nil {
		content, err := os.ReadFile(dockerignorePath)
		if err != nil {
			logger.Fatalf("Error reading %s: %v", dockerignorePath, err)
		}
		dockerignoreObject = dockerignore.NewDockerignore(string(content))
	} else {
		logger.Warnf("* No dockerignore file found at %s", dockerignorePath)
		// set path to empty string to signify to the rest of the application
		// that .dockerignore does not exist for this project
		dockerignorePath = ""
	}

	packageJson, err := getPackageJson()
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			logger.Warnf("* No package.json file found")
		} else {
			logger.Fatalf("Failed to read package.json: %v", err)
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
		cwd,
		cwdTree,
		dockerfilePath,
		dockerignorePath,
	)

	proj := project.NewProject(dockerfileObject, dockerignoreObject, packageJson, projectDirFS)

	response, err := proj.OptimizeDockerImage(aiService)
	if err != nil {
		logger.Fatalf("Error optimizing Docker image (use --debug to get more info): %s", err)
	}

	if len(response.ActionsTaken) > 0 {
		// Save optimized files
		if err := os.MkdirAll(outputDir, os.ModePerm); err != nil {
			logger.Fatalf("Error creating output directory: %v", err)
		}

		// write Dockerfile to file
		dockerfileOutputPath := filepath.Join(outputDir, "Dockerfile")
		if err := os.WriteFile(dockerfileOutputPath, []byte(response.Dockerfile), os.ModePerm); err != nil {
			logger.Fatalf("Error writing optimized Dockerfile: %v", err)
		}

		// if Dockerignore exists, write it to file
		if response.Dockerignore != "" {
			dockerignoreOutputPath := filepath.Join(outputDir, ".dockerignore")
			if err := os.WriteFile(dockerignoreOutputPath, []byte(response.Dockerignore), os.ModePerm); err != nil {
				logger.Fatalf("Error writing optimized Dockerfile: %v", err)
			}
		}

		logger.Infof("Optimized file(s) saved to %s/", outputDir)

		fmt.Printf("\n============ %d Action(s) Taken ============\n", len(response.ActionsTaken))
		for _, action := range response.ActionsTaken {
			color.Cyan("File: " + color.BlueString(action.Filepath))
			color.Cyan("Title: " + color.GreenString(action.Title))
			color.Cyan("Description: " + color.WhiteString(action.Description))
			fmt.Println("---------------------------------")
		}
	}

	if len(response.Recommendations) > 0 {
		fmt.Printf("\n\n============ %d Recommendation(s) ============\n", len(response.Recommendations))
		for _, rec := range response.Recommendations {
			color.Cyan("File: " + color.BlueString(rec.Filepath))
			color.Cyan("Title: " + color.GreenString(rec.Title))
			color.Cyan("Description: " + color.WhiteString(rec.Description))
			fmt.Println("---------------------------------")
		}
	}

	if len(response.ActionsTaken) == 0 && len(response.Recommendations) == 0 {
		logger.Infof("Docker image is already optimized, no further actions were taken.")
	}
}
