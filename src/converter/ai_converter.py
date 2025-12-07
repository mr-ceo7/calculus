import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Free tier limits (approximate)
FREE_TIER_TOKENS_PER_DAY = 1_000_000
FREE_TIER_RPM = 60  # Requests per minute
MIN_TOKENS_BUFFER = 50_000  # Reserve 50k tokens for safety


class GeminiUnavailable(Exception):
    """Raised when Gemini cannot be used or is misconfigured."""


def _sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content from AI to ensure it follows strict formatting rules.
    Remove dangerous tags and ensure only allowed HTML is present.
    """
    # Remove script tags and content
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags and content
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove onclick, onload and other event handlers
    html_content = re.sub(r'\s+on\w+\s*=\s*["\']?[^"\'>\s]*["\']?', '', html_content, flags=re.IGNORECASE)
    
    # Remove harmful attributes (javascript: protocol, data: protocol)
    html_content = re.sub(r'(href|src|action)\s*=\s*["\']?(?:javascript:|data:)[^"\'>\s]*["\']?', '', html_content, flags=re.IGNORECASE)
    
    # Remove any unallowed HTML tags, keep only: p, h1-h6, ul, ol, li, div, span, br, strong, em, code
    allowed_tags = r'</?(?:p|h[1-6]|ul|ol|li|div|span|br|strong|em|code|section)(?:\s[^>]*)?>|\</(?:p|h[1-6]|ul|ol|li|div|span|strong|em|code|section)>'
    
    # Find all tags
    all_tags = re.findall(r'<[^>]+>', html_content)
    
    # Remove disallowed tags
    for tag in all_tags:
        if not re.match(allowed_tags, tag):
            html_content = html_content.replace(tag, '')
    
    return html_content.strip()


def _chunk_text(full_text: str, max_chunk_words: int, max_chars: int) -> List[str]:
    """Split text into logical chunks by chapters or by word count."""
    # Trim overly large inputs early
    trimmed = full_text[:max_chars]
    # Prefer logical chapters/units if present
    chapter_pattern = re.compile(r'^\s*(Chapter|Unit|Module)\s+\d+', re.IGNORECASE | re.MULTILINE)
    matches = list(chapter_pattern.finditer(trimmed))

    if not matches:
        return _chunk_by_words(trimmed, max_chunk_words)

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(trimmed)
        chunk = trimmed[start:end].strip()
        if chunk:
            chunks.extend(_chunk_by_words(chunk, max_chunk_words))
    return chunks


def _chunk_by_words(text: str, max_chunk_words: int) -> List[str]:
    words = text.split()
    if len(words) <= max_chunk_words:
        return [' '.join(words)]

    chunks = []
    for i in range(0, len(words), max_chunk_words):
        chunk_words = words[i:i + max_chunk_words]
        if chunk_words:
            chunks.append(' '.join(chunk_words))
    return chunks


def _estimate_tokens(text: str) -> int:
    """
    Rough estimation of tokens using 4 characters per token rule.
    Google's tokenizer typically uses ~0.25 tokens per character.
    """
    return max(1, len(text) // 4)


def _merge_chunks(chunks: List[str], max_merged_size_words: int = 3000) -> List[str]:
    """
    Merge small chunks together to reduce API calls.
    Combines adjacent chunks to minimize token overhead from repeated prompts.
    """
    if not chunks:
        return chunks
    
    merged = []
    current_chunk = ""
    current_words = 0
    
    for chunk in chunks:
        chunk_words = len(chunk.split())
        
        # If adding this chunk would exceed limit and we have content, flush current
        if current_words + chunk_words > max_merged_size_words and current_chunk:
            merged.append(current_chunk.strip())
            current_chunk = chunk
            current_words = chunk_words
        else:
            if current_chunk:
                current_chunk += "\n\n" + chunk
            else:
                current_chunk = chunk
            current_words += chunk_words
    
    # Add any remaining content
    if current_chunk:
        merged.append(current_chunk.strip())
    
    logger.info("Merged %d chunks into %d chunks", len(chunks), len(merged))
    return merged


def _check_token_quota(chunks: List[str], model_name: str) -> bool:
    """
    Check if processing these chunks would exceed free tier quota.
    Returns False if quota would be exceeded, True if safe to proceed.
    """
    # Estimate tokens per chunk: input + output
    # Assume output is roughly 2x input for descriptive content
    total_input_tokens = sum(_estimate_tokens(chunk) for chunk in chunks)
    total_output_tokens = total_input_tokens * 2  # Conservative estimate
    total_tokens = total_input_tokens + total_output_tokens
    
    # Add overhead for prompt template
    prompt_overhead = _estimate_tokens("You are an expert math explainer...") * len(chunks)
    total_tokens += prompt_overhead
    
    available_tokens = FREE_TIER_TOKENS_PER_DAY - MIN_TOKENS_BUFFER
    
    if total_tokens > available_tokens:
        logger.warning(
            "Token quota check: Would use ~%d tokens (estimated) on %s. "
            "Free tier limit: %d tokens. Available: %d tokens. "
            "Falling back to smart format.",
            total_tokens, model_name, FREE_TIER_TOKENS_PER_DAY, available_tokens
        )
        return False
    
    logger.info(
        "Token quota check: OK. Would use ~%d / %d tokens on %s",
        total_tokens, available_tokens, model_name
    )
    return True


def _render_tabs(sections: List[Dict[str, str]]) -> tuple[str, str]:
    import html
    nav_html = ""
    content_html = ""
    for idx, section in enumerate(sections, start=1):
        active = " active" if idx == 1 else ""
        title = section.get('title') or f"Part {idx}"
        
        # Escape title for HTML attributes and inline JS
        safe_title_attr = html.escape(title, quote=True)
        safe_title_js = title.replace("'", "\\'")
        
        # Shorten for display
        short_title = (title.split(':')[0] or title).strip()
        if len(short_title) > 12:
            short_title = f"Part {idx}"
        
        nav_html += f'''
        <div class="nav-item{active}" data-title="{safe_title_attr}" aria-label="{safe_title_attr}" role="button" tabindex="0" onclick="switchTab({idx}, '{safe_title_js}')">
            <span class="nav-icon">●</span>
            <span>{html.escape(short_title)}</span>
        </div>
        '''
        content_html += f'<div id="tab-{idx}" class="tab-section{active}"><section class="glass-panel">'
        content_html += f"<h2>{html.escape(title)}</h2>"
        content_html += section.get('html', '')
        content_html += '</section></div>'
    return nav_html, content_html


def _build_prompt(chunk: str) -> str:
    return (
        "You are an expert math explainer. Create structured, well-formatted HTML content following strict formatting rules.\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "1. Use <div class='definition-box'> for definitions:\n"
        "   <div class='definition-box'><span class='definition-title'>Definition: [Name]</span>Text here</div>\n"
        "2. Use <div class='theorem-box'> for theorems, propositions, lemmas:\n"
        "   <div class='theorem-box'><span class='theorem-title'>Theorem: [Name]</span>Text here</div>\n"
        "3. Use <div class='example-box'> for examples:\n"
        "   <div class='example-box'><div class='example-badge'>Example</div>Text here</div>\n"
        "4. Use <h3> for section headers\n"
        "5. Use <p> for paragraphs\n"
        "6. Use <ul><li> for bullet lists\n"
        "7. Use <ol><li> for numbered lists\n"
        "8. NO inline styling, NO external links, NO <style> tags\n"
        "9. Escape special HTML characters\n\n"
        "INPUT TEXT:\n" + chunk + "\n\n"
        "STRUCTURE REQUIRED:\n"
        "- Overview paragraph\n"
        "- Key definitions (use definition-box)\n"
        "- Main concepts with explanations\n"
        "- Important theorems/properties (use theorem-box)\n"
        "- Worked examples (use example-box)\n"
        "- Key takeaways\n\n"
        "Output ONLY valid HTML content. Be concise and educational."
    )



def _generate_sections(model: genai.GenerativeModel, chunks: List[str], timeout: float) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []
    for idx, chunk in enumerate(chunks, start=1):
        prompt = _build_prompt(chunk)
        try:
            response = model.generate_content(prompt, request_options={"timeout": timeout})
            content_text = getattr(response, 'text', None) or ''.join(
                part.text for cand in getattr(response, 'candidates', []) for part in getattr(cand, 'content', []).parts
                if hasattr(part, 'text')
            )
            html = _sanitize_html(content_text or "<p>AI returned no content.</p>")
            title = f"Part {idx}"
            sections.append({"title": title, "html": html})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini chunk %s failed: %s", idx, exc)
            raise
    return sections


def generate_ai_notes(
    text_content: str,
    output_path: Path,
    template_path: Path,
    api_key: str,
    preferred_model: str,
    fallback_model: str,
    timeout_seconds: float,
    max_chars: int,
    max_chunk_words: int,
) -> None:
    if not api_key:
        raise GeminiUnavailable("GEMINI_API_KEY not configured")

    genai.configure(api_key=api_key)

    model_name = preferred_model
    model = None
    candidates = []
    for name in [preferred_model, fallback_model, 'gemini-pro', 'gemini-1.5-flash-001', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-pro-latest']:
        if name not in candidates:
            candidates.append(name)

    for candidate in candidates:
        try:
            model = genai.GenerativeModel(candidate)
            # lightweight ping: attempt a minimal prompt with timeout to validate availability
            model.generate_content("ping", request_options={"timeout": 5})
            model_name = candidate
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini model %s unavailable: %s", candidate, exc)
            model = None
    if model is None:
        raise GeminiUnavailable("No Gemini model available")

    # Initial chunking
    chunks = _chunk_text(text_content, max_chunk_words=max_chunk_words, max_chars=max_chars)
    logger.info("Initial chunking: %d chunks", len(chunks))
    
    # Merge small chunks to reduce API calls (optimization #1 & #2)
    chunks = _merge_chunks(chunks, max_merged_size_words=3000)
    
    # Check token quota before proceeding (optimization #3)
    if not _check_token_quota(chunks, model_name):
        logger.info("Token quota exceeded. Falling back to smart format.")
        raise GeminiUnavailable("Free tier token quota would be exceeded")
    
    sections = _generate_sections(model, chunks, timeout=timeout_seconds)
    nav_html, content_html = _render_tabs(sections)

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    final_html = template.replace('{{CONTENT}}', content_html).replace('{{NAV}}', nav_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    logger.info("Gemini generation complete using %s -> %s", model_name, output_path)
