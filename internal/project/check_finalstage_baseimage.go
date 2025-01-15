package project

import (
	"fmt"
	"log"
	"slices"
	"strings"

	"github.com/duaraghav8/dockershrink/internal/dockerfile"
	"github.com/duaraghav8/dockershrink/internal/models"
)

const (
	imageTagAlpine = "alpine"
	imageTagSlim   = "slim"
)

// isAlpineOrSlim return true if the given image is an alpine or slim image.
func isAlpineOrSlim(image *dockerfile.Image) bool {
	tag := image.Tag()
	return strings.Contains(tag, imageTagAlpine) || strings.Contains(tag, imageTagSlim)
}

// getNodeAlpineEquivalentTagForImage returns the alpine equivalent tag for a given nodjes docker image.
// eg. node:14 -> node:14-alpine (so "14-alpine" is returned as response)
func getNodeAlpineEquivalentTagForImage(image *dockerfile.Image) string {
	/*
		Conversion Rules:
		latest = alpine
		[word|version] = [word|version]-alpine
		  eg- iron = iron-alpine, lts = lts-alpine, hydrogen = hydrogen-alpine,
		  20 = 20-alpine, 18.10.3 = 18.10.3-alpine
		[word|version]-[<slim-only images>] = [word|version]-[<slim-only images>]-slim
		  eg- current-bullseye = current-bullseye-slim, lts-bookworm = lts-bookworm-slim

		https://github.com/nodejs/docker-node?tab=readme-ov-file#image-variants
	*/
	slimOnlyImageTypes := []string{"bullseye", "bookworm", "buster", "iron"}

	if image.Name() != "node" {
		return ""
	}
	tag := image.Tag()
	if tag == dockerfile.DefaultTag {
		return imageTagAlpine
	}
	if isAlpineOrSlim(image) {
		return tag
	}

	parts := strings.Split(tag, "-")
	if len(parts) == 1 {
		return parts[0] + "-" + imageTagAlpine
	}
	if len(parts) == 2 && slices.Contains(slimOnlyImageTypes, parts[1]) {
		return parts[0] + "-" + parts[1] + "-" + imageTagSlim
	}

	return imageTagAlpine
}

func (p *Project) finalStageLightBaseImage() {
	rule := "final-stage-slim-baseimage"

	finalStage, _ := p.dockerfile.GetFinalStage()
	finalStageBaseImage := finalStage.BaseImage()

	if isAlpineOrSlim(finalStageBaseImage) {
		// a light image is already being used, nothing to do, exit
		return
	}

	preferredImage := dockerfile.NewImage("node:" + imageTagAlpine)
	if finalStageBaseImage.Name() == "node" {
		tag := getNodeAlpineEquivalentTagForImage(finalStageBaseImage)
		preferredImage = dockerfile.NewImage(fmt.Sprintf("node:%s", tag))
	}

	if p.dockerfile.GetStageCount() == 1 {
		// In case of a single stage, we'll only give a recommendation.
		// This is because this stage is probably building and/or testing, and we don't want to cause limitations in that.
		rec := &models.OptimizationAction{
			Rule:        rule,
			Filepath:    p.directory.GetDockerfileFilePath(),
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
		Filepath:    p.directory.GetDockerfileFilePath(),
		Title:       "Used a new, smaller base image for the final stage in Multistage Dockerfile",
		Description: fmt.Sprintf("Used '%s' instead of '%s' as the base image of the final stage. This becomes the base image of the final image produced, reducing the size significantly.", preferredImage.FullName(), finalStageBaseImage.FullName()),
	}
	p.addActionTaken(action)
}
