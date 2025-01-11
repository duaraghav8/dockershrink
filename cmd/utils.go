package cmd

// max number of characters allowed in the directory tree structure
const dirTreeStrLenLimit = 4400 // ~1K tokens in LLM prompt

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
