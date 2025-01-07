package project

type OptimizationResponse struct {
	ActionsTaken    []OptimizationAction
	Recommendations []OptimizationAction
	ModifiedProject map[string]string
}

type OptimizationAction struct {
	Rule        string
	Filename    string
	Title       string
	Description string
}

func (a *OptimizationAction) ToJSON() map[string]interface{} {
	return map[string]interface{}{
		"rule":        a.Rule,
		"filename":    a.Filename,
		"title":       a.Title,
		"description": a.Description,
	}
}
