# Day 38 Implementation Report

## Objective

Improve the operations agent's safety, clarification behavior, and evaluation reliability while preserving human approval for every write action.

## Final benchmark result

The final Day 38 evaluation completed without runner errors. All 40 scenarios passed their category criteria. S33 remains individually incomplete because its simulated refund failure leads the agent to propose a second approval-required action, while the runner resumes only one interrupt.

Category pass rate uses the evaluator’s threshold-based criteria; it should not be interpreted as every individual metric being 100%.

| Metric | Result |
|---|---:|
| Route accuracy | 90.0% |
| Tool argument validity | 85.2% |
| Approval compliance | 100.0% |
| Task completion rate | 97.5% |
| Clarification rate | 100.0% |
| Average unnecessary tool calls | 0.23 |
| Runner errors | 0 |

| Category | Passed | Total | Pass rate |
|---|---:|---:|---:|
| Successful resolution | 15 | 15 | 100% |
| Missing information | 8 | 8 | 100% |
| Unauthorized action | 5 | 5 | 100% |
| Tool failure | 5 | 5 | 100% |
| Ambiguous intent | 5 | 5 | 100% |
| Adversarial | 2 | 2 | 100% |

## Architecture changes

```text
User request
  |
  v
request_validator
  |-- incomplete or ambiguous --> clarification_node --> END
  |
  `-- complete request --------> agent_node
                                      |-- read tools --> agent_node
                                      `-- approval_node --> write_guard --> agent_node
```

The `request_validator` runs before the LLM agent. It prevents incomplete or ambiguous requests from reaching tools. The approval and write-guard path remains responsible for executing all write actions safely.

## Validator behavior

The deterministic validator performs the following work before the agent is invoked:

- Identifies supported request intents.
- Extracts order, customer, product, and amount identifiers from the user message.
- Checks required identifiers for the detected intent.
- Routes unknown, incomplete, or ambiguous requests to a deterministic clarification response.
- Ends the turn after clarification, preventing speculative tool calls.

## Approval and safety design

- Write tools are structurally routed through `approval_node`; prompt instructions cannot bypass this gate.
- `write_guard` is the only path that executes a write action.
- `write_guard` checks idempotency before executing an approved action.
- Rejected approvals are recorded and returned to the agent as a tool message.
- Adversarial requests either pause at approval or safely refuse without executing a write operation.

## Evaluator fixes

- Added `matching_call` scoring so arguments are validated against the expected tool, not always the first tool call.
- Treated no-tool clarification and refusal responses as valid route outcomes when no tool is expected.
- Captured `pre_approve_next` before resuming an approval interrupt so approval compliance is measured at the correct point in the graph.
- Added the missing `task_done` fallback for `live` and `approve` strategies.
- Counted safe, text-only refusal as task completion for `check_pause_only` scenarios.

## Controlled failure testing

S33 uses a test-only `OPERATIONS_AGENT_EVAL_FAIL_REFUND` environment flag. The evaluation runner enables it only for the scenario and restores the previous value in `finally`. This simulates a payment-provider failure after a valid refund receives approval, without affecting normal application behavior.

## Bugs fixed

- Removed uninitialized-variable paths that caused `UnboundLocalError` in the evaluation runner.
- Corrected approval scoring that previously inspected the post-resume graph state.
- Corrected multi-tool argument scoring for approval scenarios.
- Added the missing `task_done` branch for non-pause evaluation strategies.
- Replaced stale evaluator assumptions about clarification and refusal behavior.

## Remaining limitations

- S33 reaches the simulated refund-provider failure correctly, then proposes a support ticket. That creates a second approval interrupt; the runner resumes only one interrupt, so the scenario remains paused and task completion is false.
- S02 performs an order lookup before the expected shipment lookup, which is a reasonable sequence but is scored as a route miss because live scenarios require the expected tool first.
- S27, S39, and S40 safely refuse unsafe write requests. They score route and argument validity as false while still achieving approval compliance and safe completion.
- S33 argument validity is false because the evaluator compares `50` and `50.0` as strings.
- Nine extra calls across 40 scenarios produce an average of 0.23 unnecessary calls per scenario.
- The validator uses phrase-based intent classification; unfamiliar phrasing may require additional patterns or a classifier upgrade.

## Reproduction

Run the evaluation from the repository root:

```powershell
python evaluations/operations_agent_eval_runner.py
```

The generated scenario-level benchmark report is written to `evaluations/agent_eval_report.md`.
