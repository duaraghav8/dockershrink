package cmd

import (
	"fmt"
	"os"

	"github.com/duaraghav8/dockershrink/internal/ai"
	"github.com/duaraghav8/dockershrink/internal/log"
	"github.com/duaraghav8/dockershrink/internal/packagejson"
	"github.com/duaraghav8/dockershrink/internal/tree"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

const (
	// max number of characters allowed in the directory tree structure
	dirTreeStrLenLimit   = 4400 // ~1K tokens in LLM prompt

	// 2024_08 version is performing better than 2024_11 for dockershrink
	OpenAIPreferredModel = openai.ChatModelGPT4o2024_08_06

	ollamaKey            = "ollama"
	ollamaDefaultBaseURL = "http://localhost:11434/v1/"
)

var defaultDirsExcludedFromTreeStructure = [...]string{
	"node_modules",
	"jspm_packages",
	"web_modules",
	".npm",
	".yarn",
	".grunt",
	".cache",
	".git",
	".github",
	".gitlab",
	".idea",
	"vendor",
	"__pycache__",
	"venv",
	// "dist",
}

func resolveAPIKey() string {
	if apiKey != "" {
		return apiKey
	}
	if key := os.Getenv("DOCKERSHRINK_API_KEY"); key != "" {
		return key
	}

	// support legacy api key config if not provided via new config
	if openaiApiKey != "" {
		return openaiApiKey
	}
	if key := os.Getenv("OPENAI_API_KEY"); key != "" {
		return key
	}

	return ""
}

func resolveBaseURL() string {
	if baseUrl != "" {
		return baseUrl
	}
	if url := os.Getenv("DOCKERSHRINK_BASE_URL"); url != "" {
		return url
	}

	// use ollama default if base url not provided and apiKey == "ollama"
	if resolveAPIKey() == ollamaKey {
		return ollamaDefaultBaseURL
	}

	return ""
}

func resolveModel() string {
	if model != "" {
		return model
	}
	if m := os.Getenv("DOCKERSHRINK_MODEL"); m != "" {
		return m
	}

	return OpenAIPreferredModel
}

// getAIService returns an instance of AIService if the OpenAI API key is set
// this function does not treat the absence of openai API key as an error
func getAIService(logger *log.Logger) (*ai.AIService, bool) {
	key := resolveAPIKey()
	if key == "" {
		// api key was not provided via a valid flag or environment variable
		return nil, false
	}

	opts := []option.RequestOption{option.WithAPIKey(key)}
	url := resolveBaseURL()

	if url != "" {
		// add overridden base url as client argument
		opts = append(opts, option.WithBaseURL(url))
	}

	client := openai.NewClient(opts...)

	aiModel := resolveModel()
	
	return ai.NewAIService(logger, client, aiModel), true
}

// getPackageJson reads the package.json file and returns it as a PackageJSON object
// this function returns an error if the file is not found
func getPackageJson() (*packagejson.PackageJSON, error) {
	if packageJsonPath != "" {
		// path is provided as a flag, give it preference
		content, err := os.ReadFile(packageJsonPath)
		if err != nil {
			return nil, fmt.Errorf("Error reading package.json at %s: %w", packageJsonPath, err)
		}
		return packagejson.NewPackageJSON(string(content))
	}

	// no path provided in flag, search the default paths
	paths := []string{"package.json", "src/package.json"}
	for _, path := range paths {
		if _, err := os.Stat(path); err == nil {
			content, err := os.ReadFile(path)
			if err != nil {
				return nil, fmt.Errorf("Error reading package.json: %w", err)
			}
			return packagejson.NewPackageJSON(string(content))
		}
	}

	return nil, fmt.Errorf("No package.json found in the default paths: %w", os.ErrNotExist)
}

// getDirTree returns the given directory's tree string representation suitable for LLM prompt
func getDirTree(dir string) (string, error) {
	// Exclude all directories that don't directly contain the project's files.
	// These dirs increase prompt token count without adding much value.
	dirsExcludedFromTreeStructure := append(defaultDirsExcludedFromTreeStructure[:], outputDir)
	cwdTree, err := tree.BuildTreeWithIgnore(dir, dirsExcludedFromTreeStructure)
	if err != nil {
		return "", fmt.Errorf("Error building directory tree: %w", err)
	}
	if len(cwdTree) > dirTreeStrLenLimit {
		cwdTree = cwdTree[:dirTreeStrLenLimit] + "\n... (truncated)"
	}
	return cwdTree, nil
}
