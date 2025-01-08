package dockerfile

import (
	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

type Stage struct {
	parentDockerfile *Dockerfile
	index            int
	statement        *parser.Node
	baseImage        *Image
	name             string
	layers           []Layer
}

func NewStage(parentDockerfile *Dockerfile, index int, statement *parser.Node, layers []Layer) *Stage {
	stage := &Stage{
		parentDockerfile: parentDockerfile,
		index:            index,
		statement:        statement,
		layers:           layers,
	}

	// The first item in "value" tuple is the full image name
	stage.baseImage = Image{Name: statement.Value[0]}

	// By default, a stage doesn't have a name
	stage.name = ""
	for i := 0; i < len(statement.Value); i++ {
		// If there is a 'AS' in value tuple, the string right after it is the stage's name.
		if statement.Value[i] == "AS" {
			stage.name = statement.Value[i+1]
			break
		}
	}

	return stage
}

func (s *Stage) ParentDockerfile() *Dockerfile {
	return s.parentDockerfile
}

func (s *Stage) Index() int {
	return s.index
}

func (s *Stage) Layers() []Layer {
	return s.layers
}

func (s *Stage) BaseImage() *Image {
	return s.baseImage
}

func (s *Stage) Name() string {
	return s.name
}

func (s *Stage) Text() string {
	return s.statement.Original
}

func (s *Stage) ParsedStatement() *parser.Node {
	return s.statement
}
