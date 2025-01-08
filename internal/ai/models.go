package ai

import "github.com/duaraghav8/dockershrink/internal/models"

type OptimizeRequest struct {
	Dockerfile   string
	Dockerignore string
	PackageJSON  string

	StageCount uint
}

type OptimizeResponse struct {
	Dockerfile      string
	Recommendations []*models.OptimizationAction
	ActionsTaken    []*models.OptimizationAction
}
