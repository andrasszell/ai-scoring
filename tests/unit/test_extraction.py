from evidence_collection.extraction import (
    candidate_paragraphs,
    content_hash,
    html_to_text,
    keyword_hits,
)


def test_keyword_hits_requires_word_boundaries():
    # "llm" must not match inside "installments"; no real AI content here.
    assert keyword_hits("Payable in quarterly installments with a balloon payment.") == []
    assert keyword_hits("Our enrollment and retainment figures improved.") == []
    # Whole-word usage is detected.
    assert "llm" in keyword_hits("The product is powered by an LLM.")
    assert "large language model" in keyword_hits("We deployed a large language model in production.")


def test_html_to_text_strips_scripts():
    text = html_to_text("<html><body><p>We use machine learning.</p><script>x=1</script></body></html>")
    assert "machine learning" in text
    assert "x=1" not in text


def test_candidate_paragraphs_only_returns_ai_paragraphs():
    text = (
        "This paragraph is about ordinary financial reporting and revenue recognition policies only.\n\n"
        "We invested heavily in artificial intelligence and machine learning across our product lines this year."
    )
    rows = candidate_paragraphs(text)
    assert len(rows) == 1
    assert "artificial intelligence" in rows[0]["keywords"]


def test_content_hash_is_stable_and_distinct():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")
