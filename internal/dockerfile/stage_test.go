package dockerfile

import (
	"testing"

	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

func TestStage_BaseImage(t *testing.T) {
	fromNode := &parser.Node{
		Value: "FROM",
		Next: &parser.Node{
			Value: "node:18-alpine",
		},
	}

	s := Stage{
		nodeIndex:  0,
		stageIndex: 0,
		astNode:    fromNode,
	}

	baseImg := s.BaseImage()
	if baseImg.FullName() != "node:18-alpine" {
		t.Errorf("expected 'node:18-alpine', got '%s'", baseImg.FullName())
	}
}
