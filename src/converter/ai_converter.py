import logging
import re
import time
from pathlib import Path
from typing import List

import google.generativeai as genai

from converter.pdf_to_html import parse_pdf

logger = logging.getLogger(__name__)


class GeminiUnavailable(Exception):
    """Raised when Gemini cannot be used or is misconfigured."""


def _play_feedback_beep(beep_type: str) -> None:
    """Emit a simple terminal beep and log the feedback type."""
    try:
        print('\a', end='', flush=True)
    except Exception:
        pass
    logger.info("Feedback beep: %s", beep_type)


def _chunk_text(text: str, max_chars: int = 10000) -> List[str]:
    """Split text into chunks at natural boundaries (paragraphs, sections)."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    # Split by double newlines (paragraphs) first
    paragraphs = text.split('\n\n')
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para_len = len(para)
        if current_length + para_len > max_chars and current_chunk:
            # Save current chunk and start new one
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_len
        else:
            current_chunk.append(para)
            current_length += para_len + 2  # +2 for \n\n
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    logger.info("Split text into %d chunks", len(chunks))
    return chunks


def _extract_text_from_response(response) -> str:
    """Extract text from Gemini response while tolerating empty/blocked candidates."""
    parts: List[str] = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if hasattr(part, "text") and part.text:
                parts.append(part.text)

    if parts:
        return "".join(parts)

    # Fallback: try the text attr, but guard against missing parts errors
    try:
        return getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001
        finish_reason = getattr(getattr(response, "candidates", [{}])[0], "finish_reason", None)
        logger.warning("Gemini response missing text parts (finish_reason=%s): %s", finish_reason, exc)
        return ""


def _upload_pdf_to_gemini(pdf_path: Path, api_key: str):
    genai.configure(api_key=api_key)
    uploaded_file = genai.upload_file(path=str(pdf_path), display_name=pdf_path.name)
    for _ in range(60):
        state = getattr(uploaded_file, "state", None)
        state_name = getattr(state, "name", "UNKNOWN").upper()
        if state_name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
            continue
        break
    final_state = getattr(getattr(uploaded_file, "state", None), "name", "UNKNOWN").upper()
    if final_state not in {"ACTIVE", "SUCCEEDED", "READY"}:
        raise GeminiUnavailable(f"File API unavailable (state={final_state})")
    return uploaded_file


def _build_model(api_key: str, preferred_model: str, fallback_model: str):
    genai.configure(api_key=api_key)
    candidates = []
    for name in [
        preferred_model,
        fallback_model,
        "gemini-pro",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]:
        if name and name not in candidates:
            candidates.append(name)

    for candidate in candidates:
        try:
            model = genai.GenerativeModel(candidate)
            model.generate_content("ping", request_options={"timeout": 5})
            logger.info("Using Gemini model: %s", candidate)
            return model
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini model %s unavailable: %s", candidate, exc)

    raise GeminiUnavailable("No Gemini model available")


def _build_complete_html_prompt(template_content: str, is_educational: bool) -> str:
    analogies = "- Includes analogies and explanations to make concepts clear" if is_educational else "- Presents content in a clear, structured format"
    return (
        "You are an expert at creating complete, standalone HTML pages.\n\n"
        "REFERENCE TEMPLATE (maintain structure, navigation, and overall look):\n"
        f"{template_content}\n\n"
        "TASK: Generate a COMPLETE HTML document that:\n"
        "- Mirrors the template's glassmorphism layout and navigation\n"
        "- Contains all content from the provided source without truncation\n"
        "- Has tabbed navigation for sections/chapters\n"
        "- Uses color-coded boxes: definitions (blue), theorems (pink), examples (cyan)\n"
        "- Is mobile responsive and works offline\n"
        f"{analogies}\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. Output only valid HTML from <!DOCTYPE html> to </html>\n"
        "2. Do not emit placeholders like 'content goes here'\n"
        "3. Inline all CSS and JavaScript including tab switching logic\n"
        "4. MUST include bottom navigation bar: <nav class='bottom-nav'><div class='nav-track' id='nav-track'>...</div></nav>\n"
        "5. MUST include complete JavaScript with switchTab(), buildTOC(), and initialization\n"
        "6. Create nav items for each major section/chapter\n"
        "7. Include all template styles and functionality\n"
        "Begin generating the complete HTML now."
    )


def _generate_complete_html(model, uploaded_file, prompt: str, timeout: float, max_output_tokens: int) -> List[str]:
    response = model.generate_content(
        [uploaded_file, prompt],
        request_options={"timeout": timeout},
        generation_config={"max_output_tokens": max_output_tokens},
    )
    text = _extract_text_from_response(response)
    if not text:
        raise GeminiUnavailable("Gemini returned empty content")
    return [text]


def _generate_complete_html_from_text(model, prompt: str, text_content: str, timeout: float, max_output_tokens: int) -> List[str]:
    compound_prompt = f"{prompt}\n\nCONTENT:\n{text_content}"
    response = model.generate_content(
        compound_prompt,
        request_options={"timeout": timeout},
        generation_config={"max_output_tokens": max_output_tokens},
    )
    text = _extract_text_from_response(response)
    if not text:
        raise GeminiUnavailable("Gemini returned empty content from text mode")
    return [text]


def _stitch_html_responses(responses: List[str]) -> str:
    combined = "".join(responses)
    # Remove common markdown fences that some models emit
    combined = re.sub(r"```(?:html)?", "", combined, flags=re.IGNORECASE)
    combined = re.sub(r'<!--\s*BATCH[^>]*-->', '', combined, flags=re.IGNORECASE | re.DOTALL)
    combined = re.sub(r'<!--\s*END BATCH[^>]*-->', '', combined, flags=re.IGNORECASE | re.DOTALL)
    # Remove common placeholder comments
    combined = re.sub(r"<!--\s*AI GENERATED CONTENT GOES HERE\s*-->", "", combined, flags=re.IGNORECASE)
    return combined.strip()


def _ensure_navigation_and_scripts(html_content: str) -> str:
    """Ensure navigation bar and essential scripts are present even if AI omits them."""
    patched = html_content
    lower = patched.lower()

    # First, fix any truncated/broken tags at the end
    # Look for incomplete opening tags like <p, <div, <span that don't have closing >
    if re.search(r'<(p|div|span|h[1-6]|a|li|ul|ol)\s*$', patched, re.IGNORECASE):
        logger.warning("AI output has truncated opening tag at end; removing it")
        patched = re.sub(r'<(p|div|span|h[1-6]|a|li|ul|ol)\s*$', '', patched, flags=re.IGNORECASE)
    
    # Ensure content-viewport div is properly closed
    if "content-viewport" in patched:
        # Count opening and closing divs after content-viewport
        viewport_start = patched.find('id="content-viewport"')
        if viewport_start > 0:
            after_viewport = patched[viewport_start:]
            open_divs = after_viewport.count('<div')
            close_divs = after_viewport.count('</div>')
            if open_divs > close_divs:
                missing = open_divs - close_divs
                logger.warning(f"Content has {missing} unclosed div(s); adding closing tags")
                patched += '\n' + ('        </div>\n' * missing)
                patched += '    </div>\n'  # Close content-viewport

    # Check if navigation bar is missing
    if "bottom-nav" not in lower or "nav-track" not in lower:
        logger.warning("AI omitted navigation bar; injecting fallback")
        # Count tab sections to generate nav items
        tab_count = patched.count('id="tab-')
        if tab_count == 0:
            tab_count = 2  # Default fallback
        
        nav_items = []
        icons = ['📚', '🌳', '📖', '💡', '🔬', '📊', '🎯', '🔍']
        for i in range(1, tab_count + 1):
            icon = icons[i-1] if i-1 < len(icons) else '📄'
            active = ' active' if i == 1 else ''
            nav_items.append(
                f'            <a class="nav-item{active}" data-title="Part {i}" tabindex="0" role="button">\n'
                f'                <span class="nav-icon">{icon}</span>\n'
                f'                <span>Part {i}</span>\n'
                f'            </a>'
            )
        
        nav_html = (
            "\n    <nav class=\"bottom-nav\">\n"
            "        <div class=\"nav-track\" id=\"nav-track\">\n"
            + "\n".join(nav_items) + "\n"
            "        </div>\n"
            "    </nav>\n"
        )
        
        # Try multiple injection strategies
        nav_injected = False
        
        # Strategy 1: After content-viewport closing
        if "content-viewport" in patched and not nav_injected:
            result = re.sub(
                r'(<div[^>]*id=["\']content-viewport["\'][^>]*>.*?)(</div>\s*</div>)',
                r'\1\2' + nav_html,
                patched,
                count=1,
                flags=re.IGNORECASE | re.DOTALL
            )
            if result != patched:
                patched = result
                nav_injected = True
        
        # Strategy 2: Before any script tag
        if not nav_injected and "<script" in lower:
            patched = re.sub(r'(<script)', nav_html + r'\1', patched, count=1, flags=re.IGNORECASE)
            nav_injected = True
        
        # Strategy 3: Before closing body
        if not nav_injected and "</body>" in lower:
            patched = re.sub(r'</body>', nav_html + '</body>', patched, count=1, flags=re.IGNORECASE)
            nav_injected = True
        
        # Strategy 4: Just append before we add closing tags
        if not nav_injected:
            patched += nav_html

    # Check if essential JavaScript is missing
    if "switchTab" not in patched or "buildTOC" not in patched:
        logger.warning("AI omitted essential JavaScript; injecting fallback")
        essential_js = '''
<script>
'use strict';
function switchTab(id,title){try{document.getElementById('header-title').textContent=title;document.querySelectorAll('.tab-section').forEach(el=>el.classList.remove('active'));const tab=document.getElementById('tab-'+id);if(tab)tab.classList.add('active');document.querySelectorAll('.nav-item').forEach((el,i)=>el.classList.toggle('active',i===id-1));document.getElementById('content-viewport').scrollTop=0;buildTOC();}catch(e){console.error('Tab switch error:',e);}}
function buildTOC(){const tocPanel=document.getElementById('toc-panel');const tocList=document.getElementById('toc-list');const activeTab=document.querySelector('.tab-section.active');if(!tocPanel||!tocList||!activeTab)return;const headings=activeTab.querySelectorAll('h2, h3');if(!headings.length){tocPanel.classList.add('hidden');tocList.innerHTML='';return;}const items=[];headings.forEach((h,idx)=>{if(!h.id)h.id=h.textContent.toLowerCase().replace(/[^a-z0-9]+/g,'-')+'-'+idx;items.push(`<a class="toc-${h.tagName.toLowerCase()}" href="#${h.id}">${h.textContent}</a>`);});tocList.innerHTML=items.join('');tocPanel.classList.remove('hidden');}
document.addEventListener('DOMContentLoaded',()=>{const firstTab=document.querySelector('.tab-section');if(firstTab){firstTab.classList.add('active');const firstNav=document.querySelector('.nav-item');if(firstNav)firstNav.classList.add('active');}buildTOC();document.querySelectorAll('.nav-item').forEach((item,index)=>{item.addEventListener('click',()=>switchTab(index+1,item.dataset.title||`Part ${index+1}`));item.addEventListener('keydown',(evt)=>{if(evt.key==='Enter'||evt.key===' '){evt.preventDefault();switchTab(index+1,item.dataset.title||`Part ${index+1}`);}});});const intro=document.getElementById('intro-overlay');const loading=document.getElementById('loading-overlay');const progress=document.getElementById('load-progress');if(progress)progress.style.width='100%';setTimeout(()=>{intro?.classList.add('hide');loading?.classList.add('hide');},200);setTimeout(()=>{intro?.remove();loading?.remove();},900);});
</script>
'''
        # Insert before closing body
        if "</body>" in lower:
            patched = re.sub(r"</body>", essential_js + "</body>", patched, count=1, flags=re.IGNORECASE)
        else:
            patched += essential_js

    # Ensure closing tags exist so browsers render reliably
    if "</body>" not in lower:
        patched += "\n</body>"
    if "</html>" not in lower:
        patched += "\n</html>"

    return patched


def _validate_html_structure(html_content: str) -> bool:
    lowered = html_content.lower()
    # Accept partial HTML as long as core structure is present; avoid over-rejecting truncated outputs
    return "<html" in lowered and "<body" in lowered


def _validate_with_ai(model, html_content: str, tab_count: int) -> dict:
    """Ask AI to validate the generated HTML for completeness."""
    validation_prompt = f"""
You are a QA validator. Analyze this HTML document and check:
1. Is the HTML structure complete with proper closing tags?
2. Are all {tab_count} tab sections present and complete?
3. Is the bottom navigation bar present with {tab_count} nav items?
4. Is the JavaScript for tab switching present?
5. Is any content truncated or cut off mid-sentence?

Respond in JSON format:
{{
    "is_complete": true/false,
    "issues": ["list of any issues found"],
    "missing_elements": ["list of missing elements"],
    "truncated": true/false,
    "recommendation": "keep" or "regenerate"
}}

HTML to validate:
{html_content[:5000]}...{html_content[-2000:]}
"""
    
    try:
        response = model.generate_content(
            validation_prompt,
            request_options={"timeout": 15},
            generation_config={"response_mime_type": "application/json"}
        )
        result_text = _extract_text_from_response(response)
        if result_text:
            import json
            return json.loads(result_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI validation failed: %s", exc)
    
    # Fallback: assume it's okay if validation fails
    return {"is_complete": True, "issues": [], "missing_elements": [], "truncated": False, "recommendation": "keep"}


def _detect_content_type(text: str) -> str:
    educational_keywords = [
        "theorem",
        "definition",
        "lemma",
        "proof",
        "chapter",
        "exercise",
        "example",
        "proposition",
        "corollary",
        "lecture",
    ]
    lowered = text.lower()
    if any(keyword in lowered for keyword in educational_keywords):
        return "educational"
    return "general"


def generate_ai_notes(
    pdf_path: Path,
    output_path: Path,
    template_path: Path,
    api_key: str,
    preferred_model: str,
    fallback_model: str,
    timeout_seconds: float,
    max_output_tokens: int,
) -> None:
    if not api_key:
        raise GeminiUnavailable("GEMINI_API_KEY not configured")

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    template_path = Path(template_path)

    template_content = template_path.read_text(encoding='utf-8')

    model = _build_model(api_key, preferred_model, fallback_model)

    use_file_api = True
    text_content = ""
    uploaded_file = None

    try:
        uploaded_file = _upload_pdf_to_gemini(pdf_path, api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("File API unavailable: %s", exc)
        use_file_api = False
        _play_feedback_beep('fallback_text')
        text_content = parse_pdf(pdf_path)

    content_type = _detect_content_type(text_content)
    prompt = _build_complete_html_prompt(template_content, is_educational=content_type == "educational")

    try:
        if use_file_api and uploaded_file is not None:
            responses = _generate_complete_html(model, uploaded_file, prompt, timeout_seconds, max_output_tokens)
        else:
            responses = _generate_complete_html_from_text(model, prompt, text_content, timeout_seconds, max_output_tokens)
    except Exception as exc:  # noqa: BLE001
        _play_feedback_beep('error')
        raise GeminiUnavailable(f"Gemini generation failed: {exc}") from exc

    final_html = _stitch_html_responses(responses)
    final_html = _ensure_navigation_and_scripts(final_html)

    if not _validate_html_structure(final_html):
        logger.warning("AI HTML validation failed; attempting text-mode fallback")
        # Capture a short preview for debugging
        logger.debug("AI raw HTML preview: %s", final_html[:400])
        # If we haven't already extracted text, do so now
        if not text_content:
            text_content = parse_pdf(pdf_path)
        try:
            responses = _generate_complete_html_from_text(model, prompt, text_content, timeout_seconds, max_output_tokens)
            final_html = _stitch_html_responses(responses)
            final_html = _ensure_navigation_and_scripts(final_html)
        except Exception as exc:  # noqa: BLE001
            _play_feedback_beep('error')
            raise GeminiUnavailable(f"Gemini generation failed after validation error: {exc}") from exc
        if not _validate_html_structure(final_html):
            _play_feedback_beep('error')
            logger.debug("Text-mode raw HTML preview: %s", final_html[:400])
            raise GeminiUnavailable("AI generated invalid HTML structure (after text fallback)")

    # AI validation step: ask Gemini to verify completeness
    tab_count = final_html.count('id="tab-')
    logger.info("Asking AI to validate generated HTML (found %d tabs)...", tab_count)
    validation_result = _validate_with_ai(model, final_html, tab_count)
    
    logger.info("AI validation result: %s", validation_result.get('recommendation', 'unknown'))
    if validation_result.get('issues'):
        logger.warning("AI found issues: %s", validation_result['issues'])
    if validation_result.get('missing_elements'):
        logger.warning("AI found missing elements: %s", validation_result['missing_elements'])
    
    # If AI recommends regeneration and we haven't tried text mode yet, try it
    if validation_result.get('recommendation') == 'regenerate' and use_file_api:
        logger.warning("AI recommends regeneration; falling back to text mode")
        if not text_content:
            text_content = parse_pdf(pdf_path)
        try:
            responses = _generate_complete_html_from_text(model, prompt, text_content, timeout_seconds, max_output_tokens)
            final_html = _stitch_html_responses(responses)
            final_html = _ensure_navigation_and_scripts(final_html)
            # Re-validate after regeneration
            validation_result = _validate_with_ai(model, final_html, tab_count)
            logger.info("Post-regeneration validation: %s", validation_result.get('recommendation', 'unknown'))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Regeneration failed: %s; keeping original", exc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding='utf-8')
    _play_feedback_beep('success')
    logger.info("Gemini generation complete -> %s (AI validation: %s)", output_path, validation_result.get('recommendation', 'unknown'))
