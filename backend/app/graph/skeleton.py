"""Story 0.6 — the two-node skeleton graph. Disposable de-risking scaffold,
deliberately not the real interview graph (that is `build.py`, from Phase 1).

Its only job is to prove the one structural property the entire conduct loop
rests on: that a node can pause on `interrupt()`, resume from a Postgres
checkpoint, and that the work done *before* the pause is not repeated.

    On resume LangGraph re-runs the ENTIRE interrupting node from the top,
    not from the `interrupt()` line.

So `await_reply` holds nothing but `interrupt()` and its return. Everything
expensive or state-mutating lives in `ask_something`, which is a separate node
and therefore already checkpointed as complete before the pause happens. That
separation is the whole point of this file; it is what stops the Interviewer
burning a duplicate LLM call and double-incrementing the turn counter on every
single candidate answer in Phase 3.

Kept in its own module rather than added to `build.py` so it can be deleted
outright once Phase 1 wires the real graph, without disturbing anything.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.llm import get_llm

# Short and cheap on purpose: the free tier is 40 RPM and this call exists to
# be counted, not to produce anything worth reading.
SKELETON_PROMPT = (
    "Ask a product manager one short opening interview question."
    " Reply with the question only, in one sentence."
)


class SkeletonState(TypedDict):
    messages: Annotated[list, add_messages]
    turn_count: int


async def ask_something(state: SkeletonState) -> dict:
    """One LLM call, one appended message, one increment.

    Every line here is exactly what must NOT be in an interrupting node. It is
    safe in this one because `ask_something` completes and is checkpointed
    before `await_reply` ever pauses, so a resume replays `await_reply` alone.
    `tests/test_interrupt.py` asserts that against `app.llm`'s call log.
    """
    llm = get_llm("fast")
    response = await llm.ainvoke(SKELETON_PROMPT, max_tokens=120)
    return {"messages": [response], "turn_count": state["turn_count"] + 1}


def await_reply(state: SkeletonState) -> dict:
    """`interrupt()` and its return. Nothing else, ever.

    Reading `messages` to build the payload is the one thing allowed above the
    call: it is a pure read that re-evaluates to the same value on resume. A
    counter, a write, or an LLM call in its place would silently run twice.
    """
    reply = interrupt({"question": state["messages"][-1].content})
    return {"messages": [("human", reply)]}


def build_skeleton_graph(checkpointer: BaseCheckpointSaver) -> Any:
    """ask_something -> await_reply -> END, with the checkpointer attached.

    `checkpointer` must be the `AsyncPostgresSaver`, never `MemorySaver` —
    story 0.7 restarts the API process between the pause and the resume, and
    an in-memory saver would pass every test here and fail that one.
    """
    graph = StateGraph(SkeletonState)
    graph.add_node("ask_something", ask_something)
    graph.add_node("await_reply", await_reply)
    graph.set_entry_point("ask_something")
    graph.add_edge("ask_something", "await_reply")
    graph.add_edge("await_reply", END)
    return graph.compile(checkpointer=checkpointer)
