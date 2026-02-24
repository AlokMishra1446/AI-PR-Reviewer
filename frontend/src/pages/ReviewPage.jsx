import React from "react";

function highlightFocusedText(text) {
  if (!text) return null;
  const parts = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const plain = text.slice(lastIndex, match.index);
      parts.push({ type: "text", value: plain });
    }
    parts.push({ type: "mark", value: match[0] });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }
  const renderWithBreaks = (value, keyPrefix) => {
    const lines = value.split("\n");
    return lines.flatMap((line, idx) => {
      const elements = [line];
      if (idx < lines.length - 1) {
        elements.push(<br key={`${keyPrefix}-br-${idx}`} />);
      }
      return elements;
    });
  };
  return parts.map((part, idx) => {
    if (part.type === "text") {
      return (
        <React.Fragment key={`t-${idx}`}>
          {renderWithBreaks(part.value, `t-${idx}`)}
        </React.Fragment>
      );
    }
    const value = part.value;
    if (value.startsWith("**")) {
      const inner = value.slice(2, -2);
      return (
        <span key={`k-${idx}`} className="focus-highlight">
          {inner}
        </span>
      );
    }
    if (value.startsWith("`")) {
      const inner = value.slice(1, -1);
      return (
        <span key={`c-${idx}`} className="focus-code">
          {inner}
        </span>
      );
    }
    return value;
  });
}

function ReviewPage({
  prUrl,
  extraPrompt,
  setPrUrl,
  setExtraPrompt,
  status,
  isLoading,
  hasResults,
  complianceScore,
  counts,
  review,
  onRunReview,
  onClear,
  formatScore
}) {
  return (
    <section className="panel">
      <h2>Run review</h2>
      <div className="field">
        <label htmlFor="pr-url">PR link</label>
        <input
          id="pr-url"
          type="text"
          placeholder="https://dev.azure.com/.../_git/.../pullrequest/211733"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
          disabled={isLoading}
        />
        <p className="hint">
          Paste an Azure DevOps pull request URL. The ID and repository are detected
          automatically.
        </p>
      </div>
      <div className="field">
        <label htmlFor="extra-prompt">Optional focus prompt</label>
        <textarea
          id="extra-prompt"
          placeholder="E.g. Focus on flaky tests, async HTTP calls, and DB validations."
          value={extraPrompt}
          onChange={(e) => setExtraPrompt(e.target.value)}
          disabled={isLoading}
        />
        <p className="hint">
          Ask the reviewer to focus on specific aspects. A dedicated answer appears in
          the results.
        </p>
      </div>
      <div className="button-row">
        <button
          className="btn primary"
          type="button"
          onClick={onRunReview}
          disabled={isLoading}
        >
          {isLoading ? "Running..." : "Run review"}
        </button>
        <button
          className="btn secondary"
          type="button"
          onClick={onClear}
          disabled={isLoading}
        >
          Clear
        </button>
      </div>
      <div className="status">
        <span>{status}</span>
      </div>

      {hasResults && (
        <>
          <div className="summary-pills">
            {complianceScore !== null && (
              <div className="pill good">
                <strong>{formatScore(complianceScore)}</strong>
                <span>rule compliance</span>
              </div>
            )}
            <div className="pill neutral">
              <strong>{counts.total}</strong>
              <span>total suggestions</span>
            </div>
          </div>

          {review?.extra_prompt_response && (
            <div className="custom-section">
              <h3>Focused answer</h3>
              <p>{highlightFocusedText(review.extra_prompt_response)}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default ReviewPage;
