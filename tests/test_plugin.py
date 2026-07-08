"""Tests for the Hermes plugin integration."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "plugin"))


def test_plugin_imports():
    """Verify plugin module is importable."""
    # Import without executing register()
    from plugin import __init__ as plugin_mod
    assert plugin_mod is not None


def test_plugin_has_register():
    """Verify plugin exposes register function."""
    from plugin.__init__ import register
    assert callable(register)


def test_plugin_has_on_pre_llm_call():
    """Verify the hook function exists."""
    from plugin.__init__ import _on_pre_llm_call
    assert callable(_on_pre_llm_call)


def test_plugin_disabled():
    """Verify plugin returns None when SKILL_RETRIEVER_DISABLE is set."""
    import os
    from plugin.__init__ import _on_pre_llm_call

    os.environ["SKILL_RETRIEVER_DISABLE"] = "1"
    result = _on_pre_llm_call(user_message="test query")
    assert result is None
    del os.environ["SKILL_RETRIEVER_DISABLE"]


def test_plugin_short_message():
    """Verify plugin skips messages under 10 chars."""
    from plugin.__init__ import _on_pre_llm_call

    result = _on_pre_llm_call(user_message="hi")
    assert result is None


def test_plugin_empty_message():
    """Verify plugin skips empty messages."""
    from plugin.__init__ import _on_pre_llm_call

    result = _on_pre_llm_call(user_message="")
    assert result is None


def test_plugin_whitespace_message():
    """Verify plugin skips whitespace-only messages."""
    from plugin.__init__ import _on_pre_llm_call

    result = _on_pre_llm_call(user_message="   ")
    assert result is None


def test_plugin_register_mock():
    """Verify register correctly calls ctx.register_hook."""
    class MockCtx:
        def __init__(self):
            self.hooks = []

        def register_hook(self, name, func):
            self.hooks.append((name, func))

    from plugin.__init__ import register

    ctx = MockCtx()
    register(ctx)
    assert len(ctx.hooks) == 1
    assert ctx.hooks[0][0] == "pre_llm_call"
