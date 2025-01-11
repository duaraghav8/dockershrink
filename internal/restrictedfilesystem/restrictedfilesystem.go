package restrictedfilesystem

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// RestrictedFilesystem is a filesystem that limits access to files and folders inside a specific root directory.
// It is used to prevent access to files outside the root directory - whether intentional or accidental.
type RestrictedFilesystem struct {
	rootDir          string
	dockerfilePath   string
	dockerignorePath string
	dirTree          string
}

func NewRestrictedFilesystem(
	rootDir string,
	rootDirTree string,
	dockerfilePath string,
	dockerinorePath string,
) *RestrictedFilesystem {
	return &RestrictedFilesystem{
		rootDir:          rootDir,
		dirTree:          rootDirTree,
		dockerfilePath:   dockerfilePath,
		dockerignorePath: dockerinorePath,
	}
}

func (rfs *RestrictedFilesystem) ReadFiles(filepaths []string) (map[string]string, error) {
	result := make(map[string]string)
	for _, path := range filepaths {
		absPath, err := filepath.Abs(filepath.Join(rfs.rootDir, path))
		if err != nil {
			return nil, err
		}
		if !strings.HasPrefix(absPath, rfs.rootDir) {
			return nil, fmt.Errorf("access denied: attempting to access files outside the root directory: %s", path)
		}
		file, err := os.Open(absPath)
		if err != nil {
			return nil, err
		}
		defer file.Close()
		content, err := io.ReadAll(file)
		if err != nil {
			return nil, err
		}
		result[path] = string(content)
	}
	return result, nil
}

func (rfs *RestrictedFilesystem) DirTree() string {
	return rfs.dirTree
}

// GetDockerignoreFilePath returns the path to the .dockerignore file inside the project.
// If the file doesn't exist, an empty string is returned.
func (rfs *RestrictedFilesystem) GetDockerignoreFilePath() string {
	return rfs.dockerignorePath
}

func (rfs *RestrictedFilesystem) GetDockerfileFilePath() string {
	return rfs.dockerfilePath
}
