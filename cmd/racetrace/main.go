// Command racetrace is the RaceTrace CLI.
//
// Only the command surface exists today; run, explore, and report are
// planned for later milestones (see ROADMAP.md) and exit with a usage
// error instead of pretending to succeed.
package main

import (
	"fmt"
	"io"
	"os"

	"github.com/ry-cen/racetrace/internal/outcome"
)

// version is overridden at build time with -ldflags "-X main.version=...".
var version = "0.0.0-dev"

const usage = `racetrace - crash the worker, break the ordering, find the bug.

Usage:
  racetrace <command> [arguments]

Commands:
  run <scenario.yaml>      run a scenario with its configured faults (planned: Week 4)
  explore <scenario.yaml>  crash at every discovered checkpoint (planned: Week 5)
  report <run-id>          print a stored run report (planned: Week 4)
  version                  print the version
  help                     print this help

Exit codes:
  0 passed   1 invariant violated   2 usage error   3 harness error
  4 recovery timeout   5 application failure
`

var planned = map[string]string{
	"run":     "Week 4",
	"explore": "Week 5",
	"report":  "Week 4",
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprint(stderr, usage)
		return outcome.ExitUsage
	}
	switch cmd := args[0]; cmd {
	case "help", "-h", "--help":
		fmt.Fprint(stdout, usage)
		return outcome.ExitPassed
	case "version", "--version":
		fmt.Fprintf(stdout, "racetrace %s\n", version)
		return outcome.ExitPassed
	default:
		if milestone, ok := planned[cmd]; ok {
			fmt.Fprintf(stderr, "racetrace %s: not implemented yet (planned for %s, see ROADMAP.md)\n", cmd, milestone)
			return outcome.ExitUsage
		}
		fmt.Fprintf(stderr, "racetrace: unknown command %q\n\n%s", cmd, usage)
		return outcome.ExitUsage
	}
}
