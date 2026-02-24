import React, { useState, useEffect, useRef } from "react";

function highlightIssueText(text) {
  if (!text) return null;
  const keywords =
    /(SQL injection|vulnerabilit(?:y|ies)|security|authentication|authorization|race condition|deadlock|performance|test case|test coverage|bug|exception|null reference)/gi;
  const parts = [];
  let lastIndex = 0;
  let match;
  while ((match = keywords.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "hit", value: match[0] });
    lastIndex = keywords.lastIndex;
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
        <React.Fragment key={`p-${idx}`}>
          {renderWithBreaks(part.value, `p-${idx}`)}
        </React.Fragment>
      );
    }
    return (
      <span key={`h-${idx}`} className="issue-highlight">
        {part.value}
      </span>
    );
  });
}

function buildIssueCommentText(pullRequestId, issue, kind, category) {
  const file = issue.file || "(file unknown)";
  const line = issue.line_number || 1;
  const description = issue.description || "";
  const suggestedFix =
    issue.suggested_fix ||
    issue.fixed_code_example ||
    description ||
    "See the description above for the recommended change.";
  return `${kind} – ${category}
PR: ${pullRequestId}
File: ${file}:${line}

${description}

Suggested fix:
${suggestedFix}`;
}

async function sendComment(pullRequestId, repository, issue, kind, category, content) {
  const file = issue.file;
  const line = issue.line_number || 1;
  if (!file) {
    throw new Error("Issue does not include a file path; cannot comment.");
  }
  const resp = await fetch("/comment/pr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pull_request_id: pullRequestId,
      repository,
      file,
      line_number: line,
      content
    })
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || "Failed to send comment.");
  }
}

export function IssueCard({
  pullRequestId,
  repository,
  issue,
  kind,
  category,
  badgeLabel,
  index
}) {
  const [draft, setDraft] = useState(
    buildIssueCommentText(pullRequestId, issue, kind, category)
  );
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const textareaRef = useRef(null);

  const severity = (issue.severity || "").toLowerCase();
  const file = issue.file || "unknown file";
  const line = issue.line_number || 1;

  useEffect(() => {
    if (!textareaRef.current) return;
    const el = textareaRef.current;
    el.style.height = "0px";
    const height = Math.min(el.scrollHeight, 260);
    el.style.height = `${height}px`;
  }, [draft]);

  const onSend = async () => {
    try {
      setSending(true);
      await sendComment(pullRequestId, repository, issue, kind, category, draft);
      setSent(true);
      setSending(false);
    } catch (err) {
      console.error(err);
      alert("Failed to send comment. Check console for details.");
      setSending(false);
    }
  };

  return (
    <article
      className={`issue-card${severity ? ` severity-${severity}` : ""}`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="issue-main">
        <div className="badge-row">
          <span className="badge type">{badgeLabel}</span>
          {severity && (
            <span className={`badge severity-${severity}`}>{severity}</span>
          )}
        </div>
        <div className="file-tag">
          <span>{file}</span> · line {line}
        </div>
        <p className="issue-desc">
          {highlightIssueText(issue.description || "")}
        </p>
        {"fixed_code_example" in issue && issue.fixed_code_example && (
          <pre className="code-block">
            {highlightIssueText(issue.fixed_code_example)}
          </pre>
        )}
        {"suggested_fix" in issue && issue.suggested_fix && (
          <pre className="code-block">
            {highlightIssueText(issue.suggested_fix)}
          </pre>
        )}
      </div>
      <div className="issue-meta">
        <span>
          {issue.severity && <>Severity: {issue.severity} · </>}
          {typeof issue.confidence === "number" && (
            <>Confidence: {issue.confidence}</>
          )}
        </span>
      </div>
      <div className="issue-actions">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={8}
        />
        <button
          type="button"
          className="btn primary"
          onClick={onSend}
          disabled={sending || sent}
        >
          {sent ? "Sent" : sending ? "Sending..." : "Send comment"}
        </button>
      </div>
    </article>
  );
}

function StandardsPage({
  meta,
  hasResults,
  counts,
  isLoading,
  pullRequestId,
  repository,
  items
}) {
  return (
    <section className="panel panel-results">
      <div className="section-header">
        <h2>Coding standards</h2>
        <span className="meta">{meta}</span>
      </div>
      {!hasResults && (
        <p className="empty-state">
          Run a review from the Review page to see coding-standard suggestions.
        </p>
      )}
      {hasResults && (
        <>
          <div className="counts-row">
            <div className="pill neutral">
              <strong>{counts.rules}</strong>
              <span>coding standards</span>
            </div>
            <div className="pill neutral">
              <strong>{counts.total}</strong>
              <span>total suggestions</span>
            </div>
          </div>
          <div className="results-scroll">
            {isLoading && (
              <div className="loading-overlay">
                <div className="spinner" />
                <span>Running review...</span>
              </div>
            )}
            {!items.length && !isLoading && (
              <p className="empty-state">No coding-standard issues found.</p>
            )}
            {!!items.length && (
              <div className="issues-list">
                {items.map((issue, idx) => (
                  <IssueCard
                    key={`${issue.file}-${issue.line_number}-${idx}`}
                    pullRequestId={pullRequestId}
                    repository={repository}
                    issue={issue}
                    kind="Rule violation"
                    category="Coding standards"
                    badgeLabel="Coding standards"
                    index={idx}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default StandardsPage;
