package main

import (
	"bytes"
	"strings"
	"testing"

	"github.com/ry-cen/racetrace/internal/outcome"
)

func TestRun(t *testing.T) {
	cases := []struct {
		name       string
		args       []string
		wantCode   int
		wantStdout string
		wantStderr string
	}{
		{"no args", nil, outcome.ExitUsage, "", "Usage:"},
		{"help", []string{"help"}, outcome.ExitPassed, "Usage:", ""},
		{"version", []string{"version"}, outcome.ExitPassed, "racetrace 0.0.0-dev", ""},
		{"unknown", []string{"frobnicate"}, outcome.ExitUsage, "", `unknown command "frobnicate"`},
		{"run is planned", []string{"run", "scenario.yaml"}, outcome.ExitUsage, "", "not implemented yet"},
		{"explore is planned", []string{"explore", "scenario.yaml"}, outcome.ExitUsage, "", "Week 5"},
		{"report is planned", []string{"report", "abc"}, outcome.ExitUsage, "", "not implemented yet"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := run(c.args, &stdout, &stderr)
			if code != c.wantCode {
				t.Errorf("exit code = %d, want %d", code, c.wantCode)
			}
			if c.wantStdout != "" && !strings.Contains(stdout.String(), c.wantStdout) {
				t.Errorf("stdout %q does not contain %q", stdout.String(), c.wantStdout)
			}
			if c.wantStderr != "" && !strings.Contains(stderr.String(), c.wantStderr) {
				t.Errorf("stderr %q does not contain %q", stderr.String(), c.wantStderr)
			}
		})
	}
}
