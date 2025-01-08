package project

import "github.com/duaraghav8/dockershrink/internal/models"

type OptimizationResponse struct {
	Dockerfile   string
	Dockerignore string

	ActionsTaken    []*models.OptimizationAction
	Recommendations []*models.OptimizationAction
}
