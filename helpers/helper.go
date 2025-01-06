package helpers

import (
    "os"
)

func FileExists(filePath string) bool {
    _, err := os.Stat(filePath)
    return !os.IsNotExist(err)
}