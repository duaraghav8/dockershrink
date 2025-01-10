package dockerfile

import (
	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

// Stage represents a single stage in a Dockerfile
type Stage struct {
	// nodeIndex is the index of the current FROM node in the AST.Children array
	nodeIndex uint
	// stageIndex is the index of the current stage in the Dockerfile
	stageIndex uint
	// astNode is the FROM node in the AST
	astNode *parser.Node
}

func (s *Stage) BaseImage() *Image {
	return NewImage(s.astNode.Next.Value)
}
