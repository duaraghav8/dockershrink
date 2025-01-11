package tree

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// BuildTreeWithIgnore walks the given directory path, builds a
// text-based tree representation, and returns it as a string.
// It will skip any directories that match names in `ignoreDirs`.
func BuildTreeWithIgnore(dirPath string, ignoreDirs []string) (string, error) {
	// Resolve the absolute path
	absPath, err := filepath.Abs(dirPath)
	if err != nil {
		return "", fmt.Errorf("failed to resolve absolute path: %w", err)
	}

	var sb strings.Builder

	// Kick off our recursive build from the top-level directory.
	err = buildTree(absPath, ignoreDirs, "", true, &sb)
	if err != nil {
		return "", err
	}

	return sb.String(), nil
}

// buildTree is a recursive helper that constructs the tree-like structure.
//
//	dirPath:    the path of the directory to explore
//	ignoreDirs: list of directory names to skip
//	prefix:     current "ASCII tree" prefix for nesting
//	isRoot:     indicates if this is the top-level call
//	sb:         pointer to a strings.Builder to accumulate the output
func buildTree(dirPath string, ignoreDirs []string, prefix string, isRoot bool, sb *strings.Builder) error {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return err
	}

	// Sort entries for consistent (alphabetical) output
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	// If this is the root, add "."
	// alternatively, add filepath.Base(dirPath)
	if isRoot {
		sb.WriteString(".")
		sb.WriteString("\n")
	}

	// Iterate over directory entries
	for i, entry := range entries {
		isLast := (i == len(entries)-1)
		connector := "├── "
		subPrefix := "│   "
		if isLast {
			connector = "└── "
			subPrefix = "    "
		}

		fullPath := filepath.Join(dirPath, entry.Name())

		if entry.IsDir() {
			// If we want to ignore this directory, just add it (without recursion)
			if contains(ignoreDirs, entry.Name()) {
				sb.WriteString(fmt.Sprintf("%s%s%s\n", prefix, connector, entry.Name()))
			} else {
				// Add the directory name
				sb.WriteString(fmt.Sprintf("%s%s%s\n", prefix, connector, entry.Name()))

				// Recurse into this directory
				err = buildTree(fullPath, ignoreDirs, prefix+subPrefix, false, sb)
				if err != nil {
					return err
				}
			}
		} else {
			// It's a file, just add the file name
			sb.WriteString(fmt.Sprintf("%s%s%s\n", prefix, connector, entry.Name()))
		}
	}

	return nil
}

// contains checks if 'item' is in the string slice 'slice'.
func contains(slice []string, item string) bool {
	for _, v := range slice {
		if v == item {
			return true
		}
	}
	return false
}
