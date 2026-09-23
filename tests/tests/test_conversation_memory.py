"""Tests for Phase 5.9 — Conversation Memory & Query Rewriter."""

import pytest
from backend.app.schemas.memory import MessageRole
from backend.rag.memory.conversation_memory import ConversationMemory
from backend.rag.memory.query_rewriter import QueryRewriter


def test_conversation_memory_create_and_add():
    memory = ConversationMemory(max_window=10)
    session = memory.create_session("sess-001")
    assert session.session_id == "sess-001"
    assert len(session.messages) == 0

    memory.add_message("sess-001", MessageRole.USER, "What was Q3 revenue?")
    memory.add_message("sess-001", MessageRole.ASSISTANT, "Q3 revenue was $4.2M.")

    history = memory.get_history("sess-001")
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[1].role == MessageRole.ASSISTANT


def test_conversation_memory_sliding_window():
    memory = ConversationMemory(max_window=4)
    sid = "sess-window"
    for i in range(6):
        memory.add_message(sid, MessageRole.USER, f"Message {i}")

    history = memory.get_history(sid)
    assert len(history) == 4
    assert history[-1].content == "Message 5"


def test_conversation_memory_formatted_history():
    memory = ConversationMemory()
    memory.add_message("s1", MessageRole.USER, "Hello")
    memory.add_message("s1", MessageRole.ASSISTANT, "Hi there!")

    formatted = memory.get_formatted_history("s1")
    assert "User: Hello" in formatted
    assert "Assistant: Hi there!" in formatted


def test_conversation_memory_clear_and_delete():
    memory = ConversationMemory()
    memory.add_message("s2", MessageRole.USER, "Test")
    memory.clear_session("s2")
    assert memory.get_history("s2") == []

    memory.delete_session("s2")
    assert memory.get_session("s2") is None


def test_conversation_memory_get_or_create():
    memory = ConversationMemory()
    session = memory.get_or_create_session("new-session")
    assert session.session_id == "new-session"
    # Getting again returns same session
    session2 = memory.get_or_create_session("new-session")
    assert session2.session_id == "new-session"


def test_query_rewriter_followup_detection():
    rewriter = QueryRewriter()
    assert rewriter.is_followup("it")
    assert rewriter.is_followup("What about that?")
    assert rewriter.is_followup("Tell me more")
    assert not rewriter.is_followup("What was the total revenue for Q3 2026 in the North region?")


def test_query_rewriter_context_injection():
    from backend.app.schemas.memory import Message
    rewriter = QueryRewriter()
    history = [
        Message(role=MessageRole.USER, content="What was Q3 revenue for North region?"),
        Message(role=MessageRole.ASSISTANT, content="North region revenue was $1.8M."),
    ]
    original = "What about South?"
    rewritten = rewriter.rewrite(original, history)
    assert "Context:" in rewritten
    assert "South" in rewritten


def test_query_rewriter_no_change_for_explicit_query():
    rewriter = QueryRewriter()
    explicit = "What is the annual revenue breakdown by product category?"
    result = rewriter.rewrite(explicit, [])
    assert result == explicit
