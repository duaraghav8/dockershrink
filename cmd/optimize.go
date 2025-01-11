package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/duaraghav8/dockershrink/internal/ai"
	"github.com/duaraghav8/dockershrink/internal/dockerfile"
	"github.com/duaraghav8/dockershrink/internal/dockerignore"
	"github.com/duaraghav8/dockershrink/internal/packagejson"
	"github.com/duaraghav8/dockershrink/internal/project"
	"github.com/duaraghav8/dockershrink/internal/restrictedfilesystem"
	"github.com/duaraghav8/dockershrink/internal/tree"
	"github.com/fatih/color"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/spf13/cobra"
)

var optimizeCmd = &cobra.Command{
	Use:   "optimize",
	Short: "Optimizes the Docker image definition for a project",
	Long: `Optimizes the Dockerfile and .dockerignore files and provides recommendations where applicable.
NOTE: This command currently only supports NodeJS projects.`,
	Run: runOptimize,
}

var (
	dockerfilePath   string
	dockerignorePath string
	packageJsonPath  string
	outputDir        string
	openaiApiKey     string
	verbose          bool
)

func init() {
	optimizeCmd.Flags().StringVar(&dockerfilePath, "dockerfile", "Dockerfile", "Path to Dockerfile")
	optimizeCmd.Flags().StringVar(&dockerignorePath, "dockerignore", ".dockerignore", "Path to .dockerignore")
	optimizeCmd.Flags().StringVar(&packageJsonPath, "package-json", "", "Path to package.json (default: ./package.json or ./src/package.json)")
	optimizeCmd.Flags().StringVar(&outputDir, "output-dir", "dockershrink.optimized", "Directory to save optimized files")
	optimizeCmd.Flags().StringVar(&openaiApiKey, "openai-api-key", "", "OpenAI API key to enable Generative AI features (alternatively, set the OPENAI_API_KEY environment variable)")
	optimizeCmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "Print complete stack trace in case of failures")

	rootCmd.AddCommand(optimizeCmd)
}

func runOptimize(cmd *cobra.Command, args []string) {
	// Initialize AI service if API key is provided or environment variable is set
	var aiService *ai.AIService
	if openaiApiKey == "" {
		openaiApiKey = os.Getenv("OPENAI_API_KEY")
	}
	if openaiApiKey != "" {
		client := openai.NewClient(
			option.WithAPIKey(openaiApiKey),
		)
		aiService = ai.NewAIService(client)
	}

	// Read Dockerfile
	dockerfileContents, err := os.ReadFile(dockerfilePath)
	if err != nil {
		color.Red("Error reading %s: %v", dockerfilePath, err)
		os.Exit(1)
	}

	dockerfileObject, err := dockerfile.NewDockerfile(string(dockerfileContents))

	// Read .dockerignore
	var dockerignoreContent string
	if _, err := os.Stat(dockerignorePath); err == nil {
		content, err := os.ReadFile(dockerignorePath)
		if err != nil {
			color.Red("Error reading .dockerignore: %v", err)
			os.Exit(1)
		}
		dockerignoreContent = string(content)
	} else {
		color.Yellow("* No .dockerignore file found at %s", dockerignorePath)
		// set path to empty string to signify to the rest of the application
		// that .dockerignore does not exist for this project
		dockerignorePath = ""
	}
	dockerignore, err := dockerignore.NewDockerignore(dockerignoreContent)

	// Read package.json
	var packageJson *packagejson.PackageJSON
	if packageJsonPath != "" {
		content, err := os.ReadFile(packageJsonPath)
		if err != nil {
			color.Red("Error reading package.json at %s: %v", packageJsonPath, err)
			os.Exit(1)
		}
		packageJson, err = packagejson.NewPackageJSON(string(content))
		if err != nil {
			color.Red("Failed to parse package.json: %v", err)
			os.Exit(1)
		}
	} else {
		// Search default paths
		paths := []string{"package.json", "src/package.json"}
		for _, path := range paths {
			if _, err := os.Stat(path); err == nil {
				content, err := os.ReadFile(path)
				if err != nil {
					color.Red("Error reading package.json: %v", err)
					os.Exit(1)
				}
				packageJson, err = packagejson.NewPackageJSON(string(content))
				if err != nil {
					color.Red("Failed to parse package.json: %v", err)
					os.Exit(1)
				}
				break
			}
		}
		if packageJson == nil {
			color.Yellow("* No package.json found in the default paths")
		}
	}

	cwd, err := os.Getwd()
	if err != nil {
		color.Red("Error getting current working directory: %v", err)
		os.Exit(1)
	}

	// Create directory tree string representation for the LLM prompt
	// Exclude all directories that don't directly contain the project's files.
	// These dirs increase prompt token count without adding much value.
	dirsExcludedFromTreeStructure := append(defaultDirsExcludedFromTreeStructure[:], outputDir)
	cwdTree, err := tree.BuildTreeWithIgnore(cwd, dirsExcludedFromTreeStructure)
	if err != nil {
		color.Red("Error building directory tree: %v", err)
		os.Exit(1)
	}
	if len(cwdTree) > dirTreeStrLenLimit {
		cwdTree = cwdTree[:dirTreeStrLenLimit] + "\n... (truncated)"
	}

	projectDirFS := restrictedfilesystem.NewRestrictedFilesystem(
		cwd,
		cwdTree,
		dockerfilePath,
		dockerignorePath,
	)

	proj := project.NewProject(dockerfileObject, dockerignore, packageJson, projectDirFS)

	response, err := proj.OptimizeDockerImage(aiService)
	if err != nil {
		color.Red("Error optimizing Docker image: %v", err)
		if verbose {
			fmt.Println(err)
		}
		os.Exit(1)
	}

	if len(response.ActionsTaken) > 0 {
		// Save optimized files
		if err := os.MkdirAll(outputDir, os.ModePerm); err != nil {
			color.Red("Error creating output directory: %v", err)
			os.Exit(1)
		}

		// write Dockerfile to file
		dockerfileOutputPath := filepath.Join(outputDir, "Dockerfile")
		if err := os.WriteFile(dockerfileOutputPath, []byte(response.Dockerfile), os.ModePerm); err != nil {
			color.Red("Error writing optimized Dockerfile: %v", err)
			os.Exit(1)
		}

		// if Dockerignore exists, write it to file
		if response.Dockerignore != "" {
			dockerignoreOutputPath := filepath.Join(outputDir, ".dockerignore")
			if err := os.WriteFile(dockerignoreOutputPath, []byte(response.Dockerignore), os.ModePerm); err != nil {
				color.Red("Error writing optimized Dockerfile: %v", err)
				os.Exit(1)
			}
		}

		color.Green("Optimized file(s) saved to %s/", outputDir)

		// Display actions taken
		fmt.Printf("\n============ %d Action(s) Taken ============\n", len(response.ActionsTaken))
		for _, action := range response.ActionsTaken {
			color.Cyan("File: " + color.BlueString(action.Filepath))
			color.Cyan("Title: " + color.GreenString(action.Title))
			color.Cyan("Description: " + color.WhiteString(action.Description))
			fmt.Println("---------------------------------")
		}
	}

	// Display Recommendations
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
		color.Green("Docker image is already optimized, no further actions were taken.")
	}
}
