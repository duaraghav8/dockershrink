package ai

import (
	"github.com/duaraghav8/dockershrink/internal/models"
	"github.com/duaraghav8/dockershrink/internal/restrictedfilesystem"
	"github.com/invopop/jsonschema"
)

type OptimizeRequest struct {
	Dockerfile   string
	Dockerignore string
	PackageJSON  string

	DockerfileStageCount uint
	ProjectDirectory     *restrictedfilesystem.RestrictedFilesystem
}

type OptimizeResponse struct {
	Dockerfile string `json:"dockerfile" jsonschema_description:"The optimized Dockerfile"`

	Recommendations []*models.OptimizationAction `json:"recommendations" jsonschema_description:"List of Recommendations for further the Dockerfile or whole project"`
	ActionsTaken    []*models.OptimizationAction `json:"actions_taken" jsonschema_description:"List of modifictions made in the Dockerfile"`
}

type GenerateRequest struct {
	PackageJSON      string
	ProjectDirectory *restrictedfilesystem.RestrictedFilesystem
}

type GenerateResponse struct {
	Dockerfile string `json:"dockerfile" jsonschema_description:"The generated dockerfile"`
	Comments   string `json:"comments" jsonschema_description:"Additional comments"`
}

func GenerateSchema[T any]() interface{} {
	// Structured Outputs uses a subset of JSON schema
	// These flags are necessary to comply with the subset
	reflector := jsonschema.Reflector{
		AllowAdditionalProperties: false,
		DoNotReference:            true,
	}
	var v T
	schema := reflector.Reflect(v)
	return schema
}

// Generate the JSON schema at initialization time
var optimizeResponseSchema = GenerateSchema[OptimizeResponse]()
var generateResponseSchema = GenerateSchema[GenerateResponse]()
