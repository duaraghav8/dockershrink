package dockerfile

import (
	"errors"
	"fmt"
	"strings"

	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

const (
	CmdFrom string = "FROM"
	CmdRun         = "RUN"
	CmdCopy        = "COPY"
)

const Linebreak = "\n"

type Dockerfile struct {
	code string
	ast  *parser.Node
}

func NewDockerfile(contents string) (*Dockerfile, error) {
	if len(strings.TrimSpace(contents)) == 0 {
		return nil, errors.New("Dockerfile is empty")
	}
	result, err := parser.Parse(strings.NewReader(contents))
	if err != nil {
		return nil, err
	}
	return &Dockerfile{
		code: contents,
		ast:  result.AST,
	}, nil
}

func (d *Dockerfile) Raw() string {
	return d.code
}

func (d *Dockerfile) GetStageCount() uint {
	count := 0
	for _, child := range d.ast.Children {
		if child.Value == CmdFrom {
			count++
		}
	}
	return uint(count)
}

// GetFinalStage returns the last stage in the Dockerfile
func (d *Dockerfile) GetFinalStage() (*Stage, error) {
	var lastStageNode *parser.Node
	lastStageNodeIndex := -1
	lastStageIndex := -1

	for i, child := range d.ast.Children {
		if child.Value == CmdFrom {
			lastStageNode = child
			lastStageIndex++
			lastStageNodeIndex = i
		}
	}
	if lastStageNodeIndex < 0 || lastStageIndex < 0 {
		return nil, fmt.Errorf("No stages found in Dockerfile: %s", d.code)
	}
	return &Stage{
		nodeIndex:  uint(lastStageNodeIndex),
		stageIndex: uint(lastStageIndex),
		astNode:    lastStageNode,
	}, nil
}

func (d *Dockerfile) SetStageBaseImage(stage *Stage, image *Image) {
	// Find the exact string in the Dockerfile that specifies the Image name for the stage
	// Replace the image name with the new image name.
	codeLines := strings.Split(d.code, Linebreak)

	origImageNode := stage.astNode.Next
	stageDeclarationCode := codeLines[stage.astNode.StartLine-1]

	codeLines[stage.astNode.StartLine-1] = strings.Replace(stageDeclarationCode, origImageNode.Value, image.FullName(), 1)

	modifiedCode := strings.Join(codeLines, Linebreak)
	parsed, _ := parser.Parse(strings.NewReader(modifiedCode))

	d.code = modifiedCode
	d.ast = parsed.AST
}
