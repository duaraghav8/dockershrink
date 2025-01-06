package project

import (
	"fmt"
	"strings"

	"github.com/duaraghav8/dockershrink/ai"
	"github.com/duaraghav8/dockershrink/dockerfile"
	"github.com/duaraghav8/dockershrink/dockerignore"
	"github.com/duaraghav8/dockershrink/package_json"
)

type OptimizationResponse struct {
	ActionsTaken    []OptimizationAction
	Recommendations []OptimizationAction
	ModifiedProject map[string]string
}

type Project struct {
	Dockerfile   *dockerfile.Dockerfile
	Dockerignore *dockerignore.Dockerignore
	PackageJSON  *package_json.PackageJSON

	Recommendations []OptimizationAction
	ActionsTaken    []OptimizationAction
}

func NewProject(dockerfile *dockerfile.Dockerfile, dockerignore *dockerignore.Dockerignore, packageJson *package_json.PackageJSON) *Project {
	return &Project{
		Dockerfile:      dockerfile,
		Dockerignore:    dockerignore,
		PackageJSON:     packageJson,
		Recommendations: []OptimizationAction{},
		ActionsTaken:    []OptimizationAction{},
	}
}

func (p *Project) OptimizeDockerImage(aiService *ai.AIService) (*OptimizationResponse, error) {
	// Ensure that .dockerignore exists and contains the recommended entries
	if !p.Dockerignore.Exists() {
		p.Dockerignore.Create()
		action := OptimizationAction{
			Rule:        "create-dockerignore",
			Filename:    ".dockerignore",
			Title:       "Created .dockerignore file",
			Description: "Created a new .dockerignore file to exclude unnecessary files from the Docker build context.",
		}
		p.ActionsTaken = append(p.ActionsTaken, action)
	}

	entries := []string{"node_modules", "npm_debug.log", ".git"}
	added := p.Dockerignore.AddIfNotPresent(entries)
	if len(added) > 0 {
		action := OptimizationAction{
			Rule:        "update-dockerignore",
			Filename:    ".dockerignore",
			Title:       "Updated .dockerignore file",
			Description: fmt.Sprintf("Added the following entries to .dockerignore to exclude them from the Docker build context:\n%s", strings.Join(added, "\n")),
		}
		p.ActionsTaken = append(p.ActionsTaken, action)
	}

	// We prefer to run the AI-powered rules first, then the rule engine.
	// Always run the deterministic checks AFTER the non-deterministic ones to get better results.
	if aiService != nil {
		// First, we try to include multistage build. Using Multistage is always recommended.
		// Because in the final stage, you can just use a light base image, leave out everything and only cherry-pick
		// what you need. Nothing unknown/unexpected is present.
		// Another benefit of implementing multistage first is that all other rules execute on the final stage,
		// which is more useful than optimizing previous stage(s).
		if p.Dockerfile.GetStageCount() == 1 {
			p.DockerfileUseMultistageBuilds(aiService)
		}

		// Rest of the rules must operate regardless of the number of stages in the Dockerfile (1 or more).
		// In case of multistage, the final stage could be either user-generated or AI-generated. Shouldn't matter.
		// TODO: All rules using AI must be moved here
	}

	p.DockerfileFinalStageUseLightBaseImage()
	p.DockerfileExcludeDevDependencies()
	p.DockerfileUseDepcheck()

	// TODO: Implement other optimization methods

	return &OptimizationResponse{
		ActionsTaken:    p.ActionsTaken,
		Recommendations: p.Recommendations,
		ModifiedProject: map[string]string{
			"Dockerfile":    p.Dockerfile.Raw(),
			".dockerignore": p.Dockerignore.Raw(),
		},
	}, nil
}

func (p *Project) DockerfileUseMultistageBuilds(aiService *ai.AIService) {
	// Implementation of _dockerfile_use_multistage_builds method
}

func (p *Project) DockerfileFinalStageUseLightBaseImage() {
	// Implementation of _dockerfile_finalstage_use_light_baseimage method
}

func (p *Project) DockerfileExcludeDevDependencies() {
	// Implementation of _dockerfile_exclude_dev_dependencies method
}

func (p *Project) DockerfileUseDepcheck() {
	// Implementation of _dockerfile_use_depcheck method
}

func (p *Project) AddRecommendation(r OptimizationAction) {
	p.Recommendations = append(p.Recommendations, r)
}

func (p *Project) AddActionTaken(a OptimizationAction) {
	p.ActionsTaken = append(p.ActionsTaken, a)
}
