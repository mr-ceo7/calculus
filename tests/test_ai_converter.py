import pytest

from converter.ai_converter import (
    _detect_content_type,
    _ensure_navigation_and_scripts,
    _stitch_html_responses,
    _validate_html_structure,
)


def test_detect_content_type_educational_keywords():
    text = "This Chapter introduces a theorem, definition, and example."
    assert _detect_content_type(text) == "educational"


def test_detect_content_type_general_text():
    text = "This is a product brochure with features and pricing."
    assert _detect_content_type(text) == "general"


def test_stitch_html_responses_removes_batch_markers():
    responses = [
        "<!-- BATCH 1 of 2 --><!DOCTYPE html><html><body>Part 1<!-- END BATCH 1 -->",
        "<!-- BATCH 2 of 2 -->More content</body></html><!-- END BATCH 2 -->",
    ]
    stitched = _stitch_html_responses(responses)
    assert "BATCH" not in stitched
    assert "<!DOCTYPE html>" in stitched
    assert stitched.strip().startswith("<!DOCTYPE html>")


def test_validate_html_structure_accepts_basic_page():
    html = """<!DOCTYPE html><html><head><title>T</title></head><body><nav>Tabs</nav></body></html>"""
    assert _validate_html_structure(html)


def test_validate_html_structure_rejects_missing_tags():
    html = "<div>No html wrapper</div>"
    assert _validate_html_structure(html) is False


def test_ensure_navigation_adds_missing_elements():
    partial_html = "<html><body><div id='content-viewport'><div id='tab-1' class='tab-section'>Hi</div><div id='tab-2' class='tab-section'>Bye</div></div>"
    patched = _ensure_navigation_and_scripts(partial_html)
    assert "bottom-nav" in patched.lower()
    assert "nav-track" in patched.lower()
    assert "switchTab" in patched
    assert "buildTOC" in patched
    assert "</body>" in patched.lower()
    assert "</html>" in patched.lower()


def test_ensure_navigation_handles_truncated_html():
    # Simulate AI output cut off mid-tag
    truncated_html = (
        "<html><body><div id='content-viewport'>"
        "<div id='tab-1' class='tab-section'>Content 1</div>"
        "<div id='tab-2' class='tab-section'>Content 2</div>"
        "<div id='tab-3' class='tab-section'><p>Partial text<p"
    )
    patched = _ensure_navigation_and_scripts(truncated_html)
    # Should fix truncated tag
    assert not patched.endswith("<p")
    # Should add navigation
    assert "bottom-nav" in patched.lower()
    assert "nav-track" in patched.lower()
    # Should have 3 nav items for 3 tabs
    assert patched.count("nav-item") >= 3
    # Should close properly
    assert "</body>" in patched.lower()
    assert "</html>" in patched.lower()
