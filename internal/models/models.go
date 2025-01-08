package models

type OptimizationAction struct {
	Rule        string `json:"rule"`
	Filename    string `json:"filename"`
	Title       string `json:"title"`
	Description string `json:"description"`
}
