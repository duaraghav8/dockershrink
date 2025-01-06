package project

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
