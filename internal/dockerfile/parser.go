package dockerfile

import (
    "github.com/moby/buildkit/frontend/dockerfile/parser"
    "strings"
)

func ParseDockerfile(content string) (*Dockerfile, error) {
    reader := strings.NewReader(content)
    result, err := parser.Parse(reader)
    if err != nil {
        return nil, err
    }

    return &Dockerfile{AST: result.AST}, nil
}