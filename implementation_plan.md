# AI Architecture Refactor - Implementation Plan

## Goal

Refactor the AI system to work like manual browser workflow:
1. Upload PDF directly to Gemini (instead of extracting text first)
2. AI generates **complete standalone HTML** (not just content sections)
3. Backend saves AI output as-is (no template injection for AI mode)
4. Handle large files with multi-part responses and stitch together
5. Fallback to template injection mode if AI fails

## User Review Required

> [!IMPORTANT]
> **Structure Consistency**: AI generates complete HTML but maintains template structure
> - AI receives smart_template.html as reference to maintain basic structure
> - Output should have similar glassmorphism design and navigation
> - Benefits: Consistent look across AI and non-AI modes

> [!WARNING]
> **Smart API Fallback Strategy**
> - **Primary**: Use Gemini File API for direct PDF upload
> - **Fallback 1**: If File API unavailable → Extract text from PDF
> - **Fallback 2**: If text is large → Parse in manageable chunks with batch schema
> - **User Feedback**: Distinctive beeps when falling back to text extraction or normal mode

## Proposed Changes

### Core Component: AI Converter

#### [MODIFY] [ai_converter.py](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py)

**Major changes:**

1. **Remove chunking logic** 
   - Delete: [_chunk_text()](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#51-70), [_chunk_by_words()](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#72-83), [_merge_chunks()](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#93-126)
   - Reason: AI handles entire PDF directly

2. **Remove quota optimization**
   - Delete: [_check_token_quota()](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#128-159), [_estimate_tokens()](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#85-91)
   - Simplify: Just try API call, handle errors

3. **Add File API integration**
   - New: `_upload_pdf_to_gemini(pdf_path, api_key)` - Upload PDF file
   - New: `_build_complete_html_prompt(template_content)` - Build prompt with template reference
   - New: `_generate_complete_html(model, uploaded_file, prompt)` - Get complete HTML from AI

4. **Add multi-part response handling**
   - New: `_stitch_html_responses(responses)` - Combine partial HTML outputs
   - Logic: If response truncated → continue generation → combine

5. **Add HTML validation**
   - New: `_validate_html_structure(html_content)` - Check HTML is well-formed
   - Validation: Has `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` tags
   - **Navigation Check**: Verify bottom navigation for chapters/pages exists

6. **Add content type detection**
   - New: `_detect_content_type(text)` - Detect if content is educational
   - Use heuristics: keywords like "theorem", "definition", "chapter", etc.
   - Pass to AI prompt to conditionally add analogies/explanations

7. **Add user feedback system**
   - New: `_play_feedback_beep(beep_type)` - Audio feedback for user
   - Beep types: 'fallback_text', 'fallback_normal', 'success', 'error'
   - Uses system beep or browser notification API

8. **Implement smart fallback chain**
   - Try File API first
   - Fallback to text extraction + chunking if needed
   - Each fallback plays distinctive beep

9. **Simplify main function**
   - New signature: [generate_ai_notes(pdf_path, output_path, template_path, api_key, ...)](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py#239-299)
   - Implements full fallback chain with user feedback

**New flow with fallback:**
```python
def generate_ai_notes(pdf_path, output_path, template_path, api_key, ...):
    # 1. Read template file
    template_content = read_file(template_path)
    
    # 2. Try File API first
    try:
        uploaded_file = upload_pdf_to_gemini(pdf_path, api_key)
        use_file_api = True
    except Exception as e:
        logger.warning(f"File API unavailable: {e}")
        play_feedback_beep('fallback_text')
        # Fallback: Extract text from PDF
        text_content = parse_pdf(pdf_path)
        use_file_api = False
    
    # 3. Detect content type
    content_type = detect_content_type(text_content if not use_file_api else "")
    is_educational = content_type == 'educational'
    
    # 4. Build prompt
    prompt = build_complete_html_prompt(
        template_content, 
        is_educational=is_educational
    )
    
    # 5. Generate HTML with batch schema
    if use_file_api:
        html_batches = generate_with_file_api(uploaded_file, prompt)
    else:
        # Chunk text if large
        html_batches = generate_with_text_chunks(text_content, prompt)
    
    # 6. Stitch batches using schema markers
    complete_html = stitch_batches(html_batches)
    
    # 7. Validate HTML structure + navigation
    if not validate_html_structure(complete_html):
        raise ValueError("AI generated invalid HTML")
    
    # 8. Save to file
    output_path.write_text(complete_html)
    play_feedback_beep('success')
```

---

### Routes Integration

#### [MODIFY] [routes.py](file:///home/qassim/Downloads/calculus/src/routes.py)

**Changes in upload handler:**

```python
# Before:
text_content = parse_pdf(filepath)  # Extract text
generate_ai_notes(text_content=text_content, ...)  # Pass text

# After:
# No text extraction needed!
generate_ai_notes(pdf_path=filepath, ...)  # Pass PDF file directly
```

**Simplified error handling:**
```python
if use_ai_requested and app.config['GEMINI_ENABLED']:
    try:
        generate_ai_notes(pdf_path=filepath, ...)  # Direct PDF
    except Exception as e:
        logger.warning(f"AI generation failed: {e}")
        # Fallback to template injection
        text_content = parse_pdf(filepath)  # NOW extract text
        generate_smart_notes(text_content=text_content, ...)
```

---

### Configuration

#### [MODIFY] [config.py](file:///home/qassim/Downloads/calculus/src/config.py)

**Simplified settings:**

Remove:
- `GEMINI_MAX_CHARS` (not needed - AI handles full PDF)
- `GEMINI_MAX_CHUNK_WORDS` (no chunking)

Keep:
- `GEMINI_API_KEY`
- `GEMINI_PREFERRED_MODEL`
- `GEMINI_FALLBACK_MODEL`  
- `GEMINI_TIMEOUT_SECONDS` (may need to increase for large files)

Add:
- `GEMINI_MAX_OUTPUT_TOKENS` (e.g., 8192 for handling large HTML)

---

## Verification Plan

### Automated Tests

#### Test 1: Small PDF Upload
```python
def test_ai_upload_small_pdf():
    # Upload 1-page PDF
    # Verify complete HTML output
    # Check has <!DOCTYPE>, <html>, <head>, <body>
```

#### Test 2: Large PDF Multi-Part
```python
def test_ai_upload_large_pdf():
    # Upload 20-page PDF
    # Should trigger multi-part generation
    # Verify responses stitched correctly
```

#### Test 3: Fallback on AI Failure
```python
def test_ai_fallback():
    # Invalid API key or quota exceeded
    # Should fall back to template injection
    # Output uses smart_template.html
```

#### Test 4: HTML Validation
```python
def test_html_validation():
    # AI returns invalid HTML
    # Should raise error
    # Should trigger fallback
```

### Manual Verification

1. **Browser test**: Upload sample PDF via web interface
2. **AI mode**: Enable AI mode → verify complete HTML generated
3. **Normal mode**: Disable AI → verify template injection works
4. **Large file**: Upload 10+ page PDF → verify no truncation
5. **Visual check**: Open generated HTML → verify looks good

---

## Technical Details

### Gemini File API Usage

```python
import google.generativeai as genai

# Upload file
uploaded_file = genai.upload_file(
    path=str(pdf_path),
    display_name=pdf_path.name
)

# Wait for processing
while uploaded_file.state.name == "PROCESSING":
    time.sleep(1)
    uploaded_file = genai.get_file(uploaded_file.name)

# Use in generation
response = model.generate_content([
    uploaded_file,
    "Generate HTML based on this PDF..."
])

# Cleanup
genai.delete_file(uploaded_file.name)
```

### Prompt Structure

```
You are an expert at creating beautiful, interactive HTML pages for various content types.

I will provide you with:
1. A PDF file (or extracted text) containing content
2. A reference HTML template showing the desired style
3. Content type indicator (educational or general)

TASK: Generate a COMPLETE, STANDALONE HTML file that:
- Contains ALL content from the PDF **WITHOUT TRUNCATION**
- Maintains the basic structure of the reference template
- Uses the same glassmorphism design as the reference template
- Includes interactive animations and transitions
- Has tabbed navigation for chapters/sections
- Color-codes special elements: definitions (blue), theorems (pink), examples (cyan)
{conditional_analogies}
- Is mobile-responsive and works offline

REFERENCE TEMPLATE (maintain this structure):
{paste entire smart_template.html here}

CRITICAL REQUIREMENTS:
1. Output ONLY complete HTML code (from <!DOCTYPE> to </html>)
2. Do NOT use placeholders or comments like "content goes here"
3. **BATCH GENERATION**: If content is large, use this format:
   - Start with: "<!-- BATCH 1 of N -->"
   - Include opening tags: <!DOCTYPE>, <html>, <head>, etc.
   - End batch with: "<!-- END BATCH 1 - Type 'continue' for next batch -->"
   - Next batches continue the HTML structure
   - Final batch includes closing tags: </body>, </html>
4. Include ALL CSS inline in <style> tags (no external files)
5. Include ALL JavaScript inline in <script> tags
6. Ensure navigation tabs/buttons for all sections exist
7. Do NOT truncate content - include everything

Content Type: {content_type}

Begin generating the complete HTML now:
```

**Note**: `{conditional_analogies}` is replaced with:
- If educational: "- Includes analogies and explanations to make concepts clear"
- If general: "- Presents content in clear, structured format"

### Batch Response Schema

Based on user's manual workflow, we'll use a clear batch marker system:

```python
def _stitch_batches(responses: List[str]) -> str:
    """Combine batched HTML responses using schema markers."""
    
    if len(responses) == 1:
        # Single response - remove batch markers if present
        return remove_batch_markers(responses[0])
    
    complete_html = ""
    
    for idx, response in enumerate(responses):
        # Extract content between batch markers
        # Pattern: <!-- BATCH N of M --> ... <!-- END BATCH N -->
        
        if idx == 0:
            # First batch: Keep everything up to END BATCH marker
            content = extract_until_marker(response, "<!-- END BATCH")
            complete_html = content
        elif idx == len(responses) - 1:
            # Last batch: Skip opening tags, keep content and closing tags
            content = extract_from_marker(response, "<!-- BATCH")
            content = skip_duplicate_opening_tags(content)
            complete_html += content
        else:
            # Middle batches: Extract only content div sections
            content = extract_batch_content(response)
            complete_html += content
    
    # Remove all batch markers from final HTML
    complete_html = remove_batch_markers(complete_html)
    
    return complete_html

def _extract_batch_content(response: str) -> str:
    """Extract content between BATCH and END BATCH markers."""
    import re
    # Find content after <!-- BATCH --> and before <!-- END BATCH -->
    match = re.search(r'<!-- BATCH.*?-->(.*)<!-- END BATCH', response, re.DOTALL)
    return match.group(1) if match else response
```

---

## Migration Path

### Phase 1: Implement New AI Converter ✅
- Refactor [ai_converter.py](file:///home/qassim/Downloads/calculus/src/converter/ai_converter.py)
- Add File API integration
- Implement multi-part handling

### Phase 2: Update Routes ✅
- Modify [routes.py](file:///home/qassim/Downloads/calculus/src/routes.py) to use new flow
- Keep fallback logic intact

### Phase 3: Testing ✅
- Unit tests for new functions
- Integration tests with real PDFs
- Fallback verification

### Phase 4: Documentation ✅
- Update README
- Document new AI behavior
- Add File API usage examples

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| File upload quota limits | Fallback to template injection |
| AI generates invalid HTML | Validate structure before saving |
| Large file processing timeout | Increase timeout, handle multi-part |
| Different output quality | Test extensively before deployment |

---

## Open Questions

None - all requirements clarified by user.

---

**Ready to proceed with implementation?**
