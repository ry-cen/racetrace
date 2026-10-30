package outcome

import "testing"

func TestExitCodes(t *testing.T) {
	cases := []struct {
		o    Outcome
		name string
		code int
	}{
		{Passed, "passed", ExitPassed},
		{InvariantViolated, "invariant_violated", ExitInvariantViolated},
		{ApplicationFailure, "application_failure", ExitApplicationFailure},
		{RecoveryTimeout, "recovery_timeout", ExitRecoveryTimeout},
		{HarnessError, "harness_error", ExitHarnessError},
	}
	for _, c := range cases {
		if got := c.o.String(); got != c.name {
			t.Errorf("%d.String() = %q, want %q", int(c.o), got, c.name)
		}
		if got := c.o.ExitCode(); got != c.code {
			t.Errorf("%s.ExitCode() = %d, want %d", c.name, got, c.code)
		}
	}
}

func TestUnknownOutcomeIsNeverAPass(t *testing.T) {
	unknown := Outcome(99)
	if got := unknown.ExitCode(); got != ExitHarnessError {
		t.Fatalf("unknown outcome exit code = %d, want %d", got, ExitHarnessError)
	}
	if got := unknown.String(); got != "outcome(99)" {
		t.Fatalf("unknown outcome name = %q", got)
	}
}

func TestExitCodesAreDistinct(t *testing.T) {
	seen := map[int]string{}
	for name, code := range map[string]int{
		"passed": ExitPassed, "violated": ExitInvariantViolated, "usage": ExitUsage,
		"harness": ExitHarnessError, "timeout": ExitRecoveryTimeout, "app": ExitApplicationFailure,
	} {
		if prev, ok := seen[code]; ok {
			t.Fatalf("exit code %d shared by %s and %s", code, prev, name)
		}
		seen[code] = name
	}
}
