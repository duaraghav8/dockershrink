package restrictedfilesystem

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type RestrictedFilesystem struct {
	rootDir string
}

func NewRestrictedFilesystem(rootDir string) *RestrictedFilesystem {
	return &RestrictedFilesystem{rootDir: rootDir}
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
