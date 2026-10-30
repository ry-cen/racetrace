// Package outcome defines the result categories of a RaceTrace run and
// their mapping to CLI exit codes.
//
// The categories are deliberately disjoint: a harness or infrastructure
// error is never reported as a pass, and an invariant violation is kept
// separate from an application crash or a recovery timeout.
package outcome

import "fmt"

// Outcome is the classified result of a scenario run.
type Outcome int

const (
	// Passed means the workload completed, recovery finished within its
	// deadline, and every invariant held.
	Passed Outcome = iota
	// InvariantViolated means the system recovered but a business
	// invariant did not hold.
	InvariantViolated
	// ApplicationFailure means the application under test failed in a way
	// not caused by an injected fault (e.g. a worker crashed on its own).
	ApplicationFailure
	// RecoveryTimeout means the system did not reach a quiescent state
	// within the configured recovery deadline.
	RecoveryTimeout
	// HarnessError means RaceTrace itself or the test environment failed
	// (Docker, controller, database unreachable). The correctness of the
	// application is unknown.
	HarnessError
)

// Exit codes returned by the racetrace CLI.
const (
	ExitPassed             = 0
	ExitInvariantViolated  = 1
	ExitUsage              = 2
	ExitHarnessError       = 3
	ExitRecoveryTimeout    = 4
	ExitApplicationFailure = 5
)

// String returns the stable machine-readable name used in JSON reports.
func (o Outcome) String() string {
	switch o {
	case Passed:
		return "passed"
	case InvariantViolated:
		return "invariant_violated"
	case ApplicationFailure:
		return "application_failure"
	case RecoveryTimeout:
		return "recovery_timeout"
	case HarnessError:
		return "harness_error"
	default:
		return fmt.Sprintf("outcome(%d)", int(o))
	}
}

// ExitCode maps an outcome to the CLI exit code. Unknown outcomes map to
// ExitHarnessError so that a bug in classification can never look like a pass.
func (o Outcome) ExitCode() int {
	switch o {
	case Passed:
		return ExitPassed
	case InvariantViolated:
		return ExitInvariantViolated
	case ApplicationFailure:
		return ExitApplicationFailure
	case RecoveryTimeout:
		return ExitRecoveryTimeout
	default:
		return ExitHarnessError
	}
}
