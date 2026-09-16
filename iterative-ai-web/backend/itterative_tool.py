"""
Backend LangGraph workflow for IteraAI.

Same writer -> reviewer iterative loop as before, with the tools -> writer
loop-back bug fixed (see README). This version is kept simple on purpose:
one function builds the graph, one function runs it and returns the final
state. No streaming — the API returns the finished result in one response.
"""

import os
from typing import TypedDict, Annotated

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from dotenv import load_dotenv

load_dotenv()

MAX_ATTEMPTS = 3

WRITER_SYSTEM_PROMPT = (
    "You are an expert LinkedIn content writer. Your job is to write "
    "engaging, professional LinkedIn posts about the given topic. "
    "If the topic requires up-to-date information, statistics, or "
    "current trends, use the web search tool to gather fresh context "
    "before writing. If you have already received feedback on a "
    "previous draft, carefully address every point in the new draft. "
    "Rules for good LinkedIn posts: strong hook in the first line, "
    "1 clear takeaway, easy to skim (short paragraphs), around "
    "150–200 words, ends with a question or call-to-action to invite "
    "engagement. Do not use hashtags."
)

REVIEWER_SYSTEM_PROMPT = (
    "You are a strict LinkedIn content reviewer. You judge whether a "
    "post is publish-ready. Evaluate against these criteria:\n"
    "1. Strong hook in the first line\n"
    "2. One clear, valuable takeaway\n"
    "3. Easy to skim — uses short paragraphs\n"
    "4. Roughly 150-200 words\n"
    "5. Ends with an engaging question or CTA\n"
    "6. Professional but human tone (not corporate-robotic)\n"
    "7. No hashtags\n\n"
    "Respond in exactly this format:\n"
    "VERDICT: APPROVED or REJECTED\n"
    "FEEDBACK: <one short paragraph explaining why>\n\n"
    "Be strict but fair. Approve only if the post genuinely meets all "
    "criteria. Reject if even one criterion is clearly missing."
)


class State(TypedDict):
    topic: str
    messages: Annotated[list, add_messages]
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int


class ConfigError(Exception):
    """Raised when required API keys are missing."""


def _require_keys():
    missing = [
        k for k in ("MISTRAL_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY")
        if not os.getenv(k)
    ]
    if missing:
        raise ConfigError(
            "Missing required API key(s): " + ", ".join(missing) +
            ". Add them to backend/.env (local) or your host's environment variables (deployed)."
        )


def build_app():
    """Builds and compiles the LangGraph workflow. Call once at server startup."""
    _require_keys()

    search_tool = TavilySearch(max_results=3)
    tools = [search_tool]

    writer_llm = ChatMistralAI(model="mistral-small-latest", temperature=0.7)
    writer_llm_with_tools = writer_llm.bind_tools(tools)
 
    reviewer_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)

    def writer_node(state: State) -> dict:
        msgs = state["messages"]
        continuing_after_tool = bool(msgs) and isinstance(msgs[-1], ToolMessage)

        if continuing_after_tool:
            # Resuming after a Tavily search — finish the draft using the
            # search results already in the message history. This does NOT
            # count as a new attempt.
            response = writer_llm_with_tools.invoke(
                [("system", WRITER_SYSTEM_PROMPT)] + list(msgs)
            )
            return {"messages": [response]}

        attempt = state.get("attempt", 0) + 1
        topic = state["topic"]
        previous_feedback = state["review_feedback"]

        if attempt == 1:
            user_message = (
                f"Write a LinkedIn post on this topic: {topic}. "
                f"If you need current info, search the web first."
            )
        else:
            user_message = (
                f"Your previous draft on '{topic}' was rejected. "
                f"Here is the reviewer's feedback:\n\n{previous_feedback}\n\n"
                f"Write a new, improved draft that fixes every issue mentioned. "
                f"Do not repeat the same mistake."
            )
        messages = [("system", WRITER_SYSTEM_PROMPT), ("human", user_message)]
        response = writer_llm_with_tools.invoke(messages)

        return {
            "messages": [("human", user_message), response],
            "attempt": attempt,
        }

    tool_node = ToolNode(tools)

    def extract_draft_node(state: State) -> dict:
        last_message = state["messages"][-1]
        return {"draft": last_message.content}

    def reviewer_node(state: State) -> dict:
        draft = state["draft"]
        prompt = f"Review this LinkedIn post draft:\n{draft}\nGive your review."
        response = reviewer_llm.invoke(
            [("system", REVIEWER_SYSTEM_PROMPT), ("human", prompt)]
        )
        review_text = response.content.strip()

        is_approved = "APPROVED" in review_text.upper().split("FEEDBACK")[0]

        if "FEEDBACK:" in review_text:
            feedback = review_text.split("FEEDBACK:", 1)[1].strip()
        else:
            feedback = review_text

        return {"review_feedback": feedback, "is_approved": is_approved}

    def should_use_tool(state: State):
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return "extract_draft"

    def should_stop_looping(state: State):
        if state["is_approved"]:
            return END
        if state["attempt"] >= MAX_ATTEMPTS:
            return END
        return "writer"

    builder = StateGraph(State)
    builder.add_node("writer", writer_node)
    builder.add_node("tools", tool_node)
    builder.add_node("extract_draft", extract_draft_node)
    builder.add_node("reviewer", reviewer_node)

    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", should_use_tool)
    builder.add_edge("tools", "writer")  # loop back after search (fixed bug)
    builder.add_edge("extract_draft", "reviewer")
    builder.add_conditional_edges("reviewer", should_stop_looping)

    return builder.compile()


def initial_state(topic: str) -> State:
    return {
        "topic": topic,
        "messages": [],
        "draft": "",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
    }


# ==========================================
# CLI mode — same as before, for standalone testing
# ==========================================
if __name__ == "__main__":
    print("=" * 55)
    print("Welcome to the LinkedIn Post Generator")
    print("=" * 55)

    topic_input = input("\nWhat topic do you want a LinkedIn post about?\n> ").strip()

    if not topic_input:
        print("\nNo topic given. Exiting.")
    else:
        graph_app = build_app()
        final_state = graph_app.invoke(initial_state(topic_input))

        print("\n" + "=" * 55)
        print("FINAL LINKEDIN POST")
        print("=" * 55)
        print(final_state["draft"])
        print(f"\nTotal attempts: {final_state['attempt']}")
        print(f"Approved: {final_state['is_approved']}")
