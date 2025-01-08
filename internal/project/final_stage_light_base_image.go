package project

import (
	"fmt"
	"log"

	"github.com/duaraghav8/dockershrink/internal/dockerfile"
	"github.com/duaraghav8/dockershrink/internal/models"
)

func (p *Project) finalStageLightBaseImage() {
	rule := "final-stage-slim-baseimage"
	filename := "Dockerfile"

	finalStage := p.dockerfile.GetFinalStage()
	finalStageBaseImage := finalStage.BaseImage()

	if finalStageBaseImage.IsAlpineOrSlim() {
		// a light image is already being used, nothing to do, exit
		return
	}

	preferredImage := dockerfile.NewImage("node:alpine")
	if finalStageBaseImage.Name() == "node" {
		tag := getNodeAlpineEquivalentTagForImage(finalStageBaseImage)
		preferredImage = dockerfile.NewImage(fmt.Sprintf("node:%s", tag))
	}

	if p.dockerfile.GetStageCount() == 1 {
		// In case of a single stage, we'll only give a recommendation.
		// This is because this stage is probably building and/or testing, and we don't want to cause limitations in that.
		rec := &models.OptimizationAction{
			Rule:        rule,
			Filename:    filename,
			Title:       "Use a smaller base image for the final image produced",
			Description: fmt.Sprintf("Use '%s' instead of '%s' as the base image. This will significantly decrease the final image's size. This practice is best combined with Multistage builds. The final stage of your Dockerfile must use a slim base image. Since all testing and build processes take place in a previous stage, dev dependencies and a heavy distro isn't really needed in the final image. Enable AI to generate code for multistage build.", preferredImage.FullName(), finalStageBaseImage.FullName()),
		}
		p.addRecommendation(rec)
		return
	}

	// Multistage builds are already being used. Modify the base image in final stage.
	log.Printf("Setting new (smaller) base image for the final stage of multistage Dockerfile: %s", preferredImage.FullName())
	p.dockerfile.SetStageBaseImage(finalStage, preferredImage)

	action := &models.OptimizationAction{
		Rule:        rule,
		Filename:    filename,
		Title:       "Used a new, smaller base image for the final stage in Multistage Dockerfile",
		Description: fmt.Sprintf("Used '%s' instead of '%s' as the base image of the final stage. This becomes the base image of the final image produced, reducing the size significantly.", preferredImage.FullName(), finalStageBaseImage.FullName()),
	}
	p.addActionTaken(action)
}
