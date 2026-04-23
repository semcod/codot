
// structs.go - generated from JSON
package main

type ViewBundle struct {
	Bundle      string     `json:"bundle"`
	Kind        string     `json:"kind"`
	Version     string     `json:"version"`
	Description string     `json:"description"`
	Sources     []Source   `json:"sources"`
	Template    Template   `json:"template"`
	Output      Output     `json:"output"`
}

type Source struct {
	Name      string   `json:"name"`
	URI       string   `json:"uri"`
	Refresh   string   `json:"refresh"`
	Type      string   `json:"type"`
	DependsOn []string `json:"depends_on,omitempty"`
}

type Template struct {
	Engine    string `json:"engine"`
	SourceURI string `json:"source_uri"`
}

type Output struct {
	Format   string `json:"format"`
	Runtime  string `json:"runtime"`
	Port     int    `json:"port"`
}
