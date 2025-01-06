package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/duaraghav8/dockershrink/ai"
	"github.com/duaraghav8/dockershrink/dockerfile"
	"github.com/duaraghav8/dockershrink/dockerignore"
	"github.com/duaraghav8/dockershrink/package_json"
	"github.com/duaraghav8/dockershrink/project"
	"github.com/fatih/color"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/spf13/cobra"
)

var optimizeCmd = &cobra.Command{
	Use:   "optimize",
	Short: "Optimize your NodeJS Docker project to reduce image size",
	Run:   runOptimize,
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
	optimizeCmd.Flags().StringVar(&dockerfilePath, "dockerfile", "Dockerfile", "Path to Dockerfile (default: ./Dockerfile)")
	optimizeCmd.Flags().StringVar(&dockerignorePath, "dockerignore", ".dockerignore", "Path to .dockerignore (default: ./.dockerignore)")
	optimizeCmd.Flags().StringVar(&packageJsonPath, "package-json", "", "Path to package.json (default: ./package.json or ./src/package.json)")
	optimizeCmd.Flags().StringVar(&outputDir, "output-dir", "dockershrink.optimized", "Directory to save optimized files (default: ./dockershrink.optimized)")
	optimizeCmd.Flags().StringVar(&openaiApiKey, "openai-api-key", "", "Your OpenAI API key to enable Generative AI features (alternatively, set the OPENAI_API_KEY environment variable)")
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
	dockerfileFd, err := os.Open(dockerfilePath)
	if err != nil {
		color.Red("Error accessing Dockerfile: %v", err)
		os.Exit(1)
	}
	defer dockerfileFd.Close()

	dockerfile, err := dockerfile.NewDockerfile(dockerfileFd)

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
		color.Yellow("No .dockerignore file found")
	}
	dockerignore, err := dockerignore.NewDockerignore(dockerignoreContent)

	// Read package.json
	var packageJson *package_json.PackageJSON
	if packageJsonPath != "" {
		content, err := os.ReadFile(packageJsonPath)
		if err != nil {
			color.Red("Error reading package.json: %v", err)
			os.Exit(1)
		}
		packageJson = package_json.NewPackageJSON(string(content))
	} else {
		// Default paths searched: current directory and ./src
		paths := []string{"package.json", "src/package.json"}
		for _, path := range paths {
			if _, err := os.Stat(path); err == nil {
				content, err := os.ReadFile(path)
				if err != nil {
					color.Red("Error reading package.json: %v", err)
					os.Exit(1)
				}
				packageJson = package_json.NewPackageJSON(string(content))
				break
			}
		}
		if packageJson == nil {
			color.Yellow("No package.json found in the default paths")
		}
	}

	proj := project.NewProject(dockerfile, dockerignore, packageJson)

	response, err := proj.OptimizeDockerImage(aiService)
	if err != nil {
		color.Red("Error optimizing Docker image: %v", err)
		if verbose {
			fmt.Println(err)
		}
		os.Exit(1)
	}

	actionsTaken := response.ActionsTaken
	recommendations := response.Recommendations
	optimizedProject := response.ModifiedProject

	if len(actionsTaken) > 0 {
		// Save optimized files
		if err := os.MkdirAll(outputDir, os.ModePerm); err != nil {
			color.Red("Error creating output directory: %v", err)
			os.Exit(1)
		}

		for filename, content := range optimizedProject {
			outputPath := filepath.Join(outputDir, filename)
			if err := os.WriteFile(outputPath, []byte(content), os.ModePerm); err != nil {
				color.Red("Error writing optimized file: %v", err)
				os.Exit(1)
			}
		}

		color.Green("Optimized files saved to %s/", outputDir)

		// Display actions taken
		fmt.Printf("\n============ %d Action(s) Taken ============\n", len(actionsTaken))
		for _, action := range actionsTaken {
			color.Cyan("File: " + color.BlueString(action.Filename))
			color.Cyan("Title: " + color.GreenString(action.Title))
			color.Cyan("Description: " + color.WhiteString(action.Description))
			fmt.Println("---------------------------------")
		}
	}

	// Display Recommendations
	if len(recommendations) > 0 {
		fmt.Printf("\n\n============ %d Recommendation(s) ============\n", len(recommendations))
		for _, rec := range recommendations {
			color.Cyan("File: " + color.BlueString(rec.Filename))
			color.Cyan("Title: " + color.GreenString(rec.Title))
			color.Cyan("Description: " + color.WhiteString(rec.Description))
			fmt.Println("---------------------------------")
		}
	}

	if len(actionsTaken) == 0 && len(recommendations) == 0 {
		color.Green("Docker image is already optimized, no further actions were taken.")
	}
}
