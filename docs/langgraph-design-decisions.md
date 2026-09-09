# LangGraph Design Decisions — Operations Agent

**Project:** Customer Operations Agent  
**Phase:** 4 — LangGraph Foundations (Days 28–39)  
**File:** `projects/operations_agent/`  
**Purpose:** Design rationale for every structural choice in the graph.

---

## 1. Why a graph instead of a simple agent loop?

A simple agent loop — `while model_has_tool_calls: run_tools()` — is sufficient when every step is uniform: the model calls a tool, the result comes back, the model decides again. The operations agent is not uniform. It has categorically different node types: a deterministic validator that runs before the model, a model-driven tool-calling loop for reads, a hard interrupt gate for writes, an idempotency check, and an audit write. Putting all of that logic inside one `while` loop with `if/elif` branches produces code that is difficult to test, impossible to interrupt mid-execution, and impossible to checkpoint. You cannot pause a `while` loop, save its state to disk, and resume it in a different process. A graph is the correct data structure for a workflow with multiple distinct execution paths and the possibility of mid-execution pause.

The second reason is testability. Because each node is a plain Python function with a typed input (`AgentState`) and a typed output (a partial state dict or a `Command`), every node can be unit-tested in isolation. `request_validator` was tested without ever invoking the LLM — it just receives a state and returns a classification. `write_guard` was tested by seeding an audit log entry and confirming that `is_duplicate_action` blocked re-execution. None of that is possible when the logic lives inside a monolithic loop. Explicit graph edges also make the execution path inspectable: `graph.get_state()` returns the current node, the current state values, and the full checkpoint history. An agent loop gives you none of that.

The third reason is the interrupt mechanism. `langgraph.types.interrupt()` only works inside a compiled `StateGraph`. It suspends execution at a named node, persists the state to the checkpointer, and waits for an external `Command(resume=...)` call before continuing. This is how the human approval gate works: `approve_node` calls `interrupt()`, the graph pauses, a human sees the proposed action, and `graph.invoke(Command(resume=True/False), config)` continues from exactly where it stopped. There is no equivalent primitive in a simple loop.

---

## 2. What remained deterministic — never delegated to the model?

**Request validation and field extraction.** `request_validator` runs before the LLM on every turn. It classifies intent using keyword matching (`_classify_intent`) and extracts identifiers using regex (`_extract_fields` — patterns `\bO\d+\b`, `\bC\d+\b`, `\bP\d+\b`, `\$\d+`). It then checks whether all required fields for that intent are present and sets `needs_clarification`. None of this touches the LLM. The routing decision — go to `clarification_node` or go to `agent_node` — is made entirely in Python based on the validator's output. This matters because an LLM asked "is this request complete?" can hallucinate a yes. A Python check cannot.

**Write tool routing.** The decision of whether a tool call requires human approval is not made by the model. It is made in `route_from_agent`: if the called tool name is in `WRITE_TOOL_NAMES = {"issue_refund", "create_support_ticket"}`, the edge goes to `approve_node`. Otherwise it goes to `read_tools`. The model is never asked "does this require approval?" The model cannot affect this routing — it can only decide *which* tool to call; the graph decides what happens next based on a static lookup against a set. This is the structural guarantee that no prompt can bypass the approval gate.

**Idempotency checking.** Inside `write_guard`, before any tool is executed, `is_duplicate_action(action_id)` queries the `audit_logs` table for the UUID generated in `approval_node`. If a row exists with that `action_id`, execution is skipped and a `ToolMessage` explaining the skip is returned. The check is a SQL query against a unique column — `AuditLog.action_id` is declared `unique=True` in the schema. There is no LLM involved, no semantic comparison, no float-vs-string ambiguity. The idempotency key is a UUID generated at approval time, stored in state, consumed by `write_guard`, and cleared from state after use.

**Audit logging.** Every write action result — success or rejection — is written to `AuditLog` by Python code in `write_guard` or `log_rejection`, not by the model. The model never sees the audit log and cannot modify it.

---

## 3. What decisions were delegated to the model, and why?

**Tool selection for read operations.** The model decides which read tools to call based on the user's message. Given "Where is order O001 for customer C001?", the model calls `get_order_db` and `get_shipment_db`. Given "What is the refund policy?", it calls `get_refund_policy_db` only. The model is better at this than any keyword-based dispatcher because natural language queries are inherently variable. "Has my package shipped?", "Where's my stuff?", and "Any update on delivery?" all map to `shipment_status` but use different surface forms. The system prompt constrains the model: "Perform only the tool calls needed for the user's requested action" and "Never guess IDs or details — always retrieve first." These instructions reduce unnecessary tool calls (average 0.23 extra per scenario in the Day 38 evaluation) without replacing the model with a rule system.

**Answer formulation.** The model writes the response to the user after tool results come back. The data — order status, shipment tracking, refund policy text — comes from the database via tools. The model's job is to convert that structured dict output into a natural-language response. This is exactly what a language model is good at and what a template cannot do well for variable tool result shapes.

**Argument extraction for write tools.** When the model decides to call `issue_refund`, it extracts `order_id`, `amount`, and `reason` from the conversation. This is delegated because it requires reading across multiple turns — the customer may have mentioned the order ID two messages ago and the damage reason in the current message. The model has the full message history in its context window; a rule-based extractor does not. The Pydantic schema on `IssueRefundInput` validates the extracted arguments before the tool runs, so the model's extraction is checked deterministically even though the extraction itself is model-driven.

**Rejection response.** After an approval is rejected, a `ToolMessage` with the rejection reason is added to state and routed back to `agent_node`. The model reads this message and formulates a response to the customer — acknowledging the rejection, explaining that the action was not taken, and offering alternatives. The system prompt specifies: "If an action is rejected, acknowledge it and ask how else you can help." The model handles the phrasing; the routing and the audit log entry are handled by the graph.

---

## 4. How does state persist between conversation turns?

State persistence is handled by `InMemorySaver`, a checkpointer compiled into the graph: `graph = builder.compile(checkpointer=memory)`. Every time a node completes, LangGraph serializes the full `AgentState` dict and writes it to the checkpointer keyed by `thread_id`. On the next `graph.invoke()` call with the same `config = {"configurable": {"thread_id": "session-001"}}`, LangGraph loads the last checkpoint for that thread and merges the new input into the loaded state before running any node. The caller never sends a conversation history — they send only the new message. The framework reconstructs the full context.

The `messages` field uses the `add_messages` reducer: `messages: Annotated[list[AnyMessage], add_messages]`. This means node return values are *merged* into the existing list, not replaced. A node that returns `{"messages": [new_ai_message]}` appends that message to the existing history. `add_messages` also deduplicates by message ID — if the same message ID appears twice, the second copy replaces the first, preventing duplicate entries during retry scenarios. The `tool_calls_made` and `errors` fields use `operator.add` as their reducer, which accumulates entries across nodes across all turns in the session.

In production, `InMemorySaver` would be replaced with `PostgresSaver` or `RedisSaver`. The swap requires no code changes in any node — only the `builder.compile(checkpointer=...)` line changes. `graph.get_state(config)` returns the full current state at any point, and `graph.get_state_history(config)` returns the complete checkpoint history, which is how the Day 34 experiment verified that 3 turns in the same thread produced 3 growing snapshots while a different `thread_id` produced an isolated fresh state with no shared context.

---

## 5. How does the approval workflow prevent unauthorized write actions?

The structural guarantee has three layers. **Layer one** is the routing function `route_from_agent`:

```python
def route_from_agent(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if not last_msg.tool_calls:
        return END
    tool_name = last_msg.tool_calls[0]["name"]
    if tool_name in WRITE_TOOL_NAMES:      # {"issue_refund", "create_support_ticket"}
        return "approve_node"
    return "read_tools"
```

This is a Python function, not a prompt. `WRITE_TOOL_NAMES` is a static set defined at module load time. The model has no mechanism to modify `WRITE_TOOL_NAMES`, no mechanism to change the routing function, and no mechanism to add edges to the compiled graph. If the model calls a write tool, it goes to `approve_node`. Always.

**Layer two** is the `interrupt()` inside `approve_node`. The graph suspends here. Nothing runs until an external `graph.invoke(Command(resume=value), config)` call arrives. The interrupt payload shows the human the tool name and arguments. If `approved` is `True`, `approve_node` generates a UUID as `action_id` and routes to `write_guard`. If `approved` is `False`, `log_rejection()` writes the rejection to `AuditLog` and a `ToolMessage` is added to state routing back to `agent_node`. The write tool is never called.

**Layer three** is `write_guard` being the exclusive execution path for write tools. Write tools are not in `ToolNode` — `read_tool_node = ToolNode(READ_TOOLS, ...)` contains only read tools. Write tools are invoked only by the direct call `tool_fn.invoke(tool_args)` inside `write_guard`, which runs only after `approve_node` routes there with an `action_id`. Write tools contain no audit logging, no approval logic, and no routing — they do one thing: validate inputs and return a result dict. All safety work is in the graph, not in the tools. The Day 38 evaluation ran 5 unauthorized action scenarios and 2 adversarial scenarios — approval compliance was 100% across all 7, confirming that no user message framing can bypass the gate.

---

## 6. What happens when a tool fails mid-graph?

There are six failure modes, each handled at a different layer. The handlers are documented in `projects/operations_agent/errors/handlers.py`.

**Mode 1 — Transient timeout (read tools).** The `read_tools` node is compiled with `retry_policy=RetryPolicy(max_attempts=2, initial_interval=0.5)`. On a transient failure (`ConnectionError`, `TimeoutError`), LangGraph retries the entire node up to 2 times with a 0.5-second initial interval before propagating the exception. This is configured at the graph level: `builder.add_node("read_tools", read_tool_node, retry_policy=...)`. The agent never sees the first failure.

**Mode 2 — Database unreachable (read tools).** `db_tools.py` wraps `SessionLocal()` in a try/except for `OperationalError`. On a DB error, `handle_db_error()` returns a graceful dict: `{"error": "Database temporarily unavailable. Please try again shortly.", "tool": tool_name}`. `ToolNode` converts this dict into a `ToolMessage` and passes it to `agent_node`. The model reads the error message and tells the user the service is temporarily unavailable. No stack trace reaches the user.

**Mode 3 — Invalid tool arguments.** Write tools raise `ValueError` on invalid input (negative refund amount, invalid priority). Read tools raise `ValueError` for non-existent IDs. `ToolNode` is compiled with `handle_tool_errors=True`, which catches these exceptions and converts them into `ToolMessage` content describing the error. The model receives this message, reads the validation failure, and asks the user to clarify.

**Mode 4 — Malformed or failed LLM response.** `agent_node` wraps `llm_with_tools.invoke()` in a try/except. On any exception, it returns a fallback `AIMessage`: "I'm having trouble processing your request right now. A human agent will follow up with you shortly." It also sets `approval_required: True` in state and appends to the `errors` accumulator. The graph continues to `END` with the fallback message rather than crashing the session.

**Mode 5 — Duplicate write execution.** Before calling any write tool, `write_guard` calls `is_duplicate_action(action_id)`. If the UUID already exists in `audit_logs.action_id` (a unique-indexed column), execution is skipped. A `ToolMessage` explaining the skip is returned to `agent_node`. `action_id` is cleared from state in both the success and skip branches. This prevents double-refunds when a client retries after a network error between the `write_guard` execution and the response delivery.

**Mode 6 — Approval rejected.** `approval_node` calls `log_rejection()` before routing back to `agent_node`. `log_rejection()` writes an `AuditLog` row with `action="rejected"` and a reason string. A `ToolMessage` describing the rejection is added to state. The model reads this and informs the user. The write tool was never called. The rejection is on record in the audit log regardless of what happens to the session afterward.

---

## 7. How would you scale this to 1000 concurrent users?

The first change is the checkpointer. `InMemorySaver` stores all state in a Python dict in the process that runs the graph — it does not survive process restarts and is not shareable across workers. At 1000 concurrent users you need `PostgresSaver` (or `RedisSaver` for lower-latency session reads). The swap is one line: `graph = builder.compile(checkpointer=PostgresSaver(conn))`. Every other line of code — nodes, tools, routing functions — is unchanged. PostgreSQL provides durability, concurrent reads, and the ability to run multiple graph-worker processes against the same session store.

The second change is the interrupt mechanism. `interrupt()` pauses the graph and stores the suspended state in the checkpointer. For 1000 concurrent users with active approval interrupts, you need the supervisor interface to be able to query pending interrupts from the database, display them, and submit `Command(resume=...)` calls back to the correct `thread_id`. This is an application-layer concern — the graph itself handles it correctly because `thread_id` is the isolation key. LangGraph Cloud provides this infrastructure as a managed service. Self-hosted, you would build a supervisor API that queries `audit_logs` for rows with `action="pending_approval"` and routes approval decisions back to the graph via a queue.

The third consideration is the LLM call in `agent_node`. Each turn makes one or more calls to Azure OpenAI. At 1000 concurrent users, throughput is bounded by your deployment's tokens-per-minute quota. The graph architecture helps here because `request_validator` and `clarification_node` terminate many turns before the LLM is invoked at all — in the Day 38 evaluation, all 8 missing-information scenarios ended at `clarification_node` without an LLM call. A higher clarification rate means fewer LLM calls per unit of user traffic. The database tools (`db_tools.py`) are synchronous SQLAlchemy calls — at scale these would move to an async connection pool (`asyncpg` + `AsyncSession`) with `read_tools` becoming an async node, allowing the graph worker to yield the event loop during DB I/O rather than blocking a thread.

---

## Reference: Full graph edges

```
START
  └─► request_validator
            │── needs_clarification=True  ──► clarification_node ──► END
            └── needs_clarification=False ──► agent_node
                      │── no tool calls                ──► END
                      │── read tool called             ──► read_tools ──► agent_node
                      └── write tool called            ──► approve_node
                                  │── approved=True    ──► write_guard ──► agent_node
                                  └── approved=False   ──► agent_node
```

## Reference: State field ownership

| Field | Written by | Reducer |
|---|---|---|
| `messages` | every node that adds a message | `add_messages` (append + deduplicate by ID) |
| `customer_id`, `customer_name`, `product_id` | agent / tools | last-write-wins |
| `order_id`, `issue_category` | request_validator / agent | last-write-wins |
| `order_data`, `shipment_data`, `policy_evidence` | read tools | last-write-wins |
| `proposed_action`, `approval_required` | agent_node | last-write-wins |
| `approval_status` | approve_node, write_guard | last-write-wins |
| `action_executed` | write_guard | last-write-wins |
| `action_id` | approve_node (set), write_guard (clear to None) | last-write-wins |
| `tool_calls_made` | any node tracking tool use | `operator.add` (accumulate) |
| `errors` | agent_node (mode 4), write_guard | `operator.add` (accumulate) |
| `intent`, `required_fields`, `provided_fields`, `needs_clarification` | request_validator | last-write-wins |

## Reference: Error mode assignment

| Mode | Trigger | Handler | Layer |
|---|---|---|---|
| 1 — Transient timeout | `ConnectionError` in read tool | `RetryPolicy(max_attempts=2)` | Node compilation |
| 2 — DB unreachable | `OperationalError` in `SessionLocal()` | `handle_db_error()` → graceful dict | Tool try/except |
| 3 — Invalid tool args | `ValueError` in tool | `ToolNode(handle_tool_errors=True)` | ToolNode |
| 4 — LLM failure | Any exception in `llm_with_tools.invoke()` | try/except → fallback AIMessage | agent_node |
| 5 — Duplicate write | `action_id` already in `audit_logs` | `is_duplicate_action()` → skip | write_guard |
| 6 — Approval rejected | `approved=False` from interrupt | `log_rejection()` + ToolMessage | approve_node |

---

*Written Day 39. Covers Phase 4 (Days 28–38). Next: Project 2 deployment on Azure AI Foundry (Days 41–50).*
