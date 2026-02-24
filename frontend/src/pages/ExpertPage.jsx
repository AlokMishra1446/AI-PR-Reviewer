import React from "react";
import { IssueCard } from "./StandardsPage";

const expertGroups = [
  { label: "Bugs", key: "bugs" },
  { label: "Performance", key: "performance_issues" },
  { label: "Security", key: "security_issues" },
  { label: "Refactor", key: "refactor_suggestions" },
  { label: "Tests", key: "test_cases_to_add" }
];

function ExpertPage({
  meta,
  hasResults,
  counts,
  isLoading,
  pullRequestId,
  repository,
  expert
}) {
  return (
    <section className="panel panel-results">
      <div className="section-header">
        <h2>Expert review</h2>
        <span className="meta">{meta}</span>
      </div>
      {!hasResults && (
        <p className="empty-state">
          Run a review from the Review page to see expert suggestions.
        </p>
      )}
      {hasResults && (
        <>
          <div className="counts-row">
            <div className="pill neutral">
              <strong>{counts.bugs}</strong>
              <span>bugs</span>
            </div>
            <div className="pill neutral">
              <strong>{counts.perf}</strong>
              <span>performance</span>
            </div>
            <div className="pill neutral">
              <strong>{counts.sec}</strong>
              <span>security</span>
            </div>
            <div className="pill neutral">
              <strong>{counts.refactor}</strong>
              <span>refactor</span>
            </div>
            <div className="pill neutral">
              <strong>{counts.tests}</strong>
              <span>tests</span>
            </div>
          </div>
          <div className="results-scroll">
            {isLoading && (
              <div className="loading-overlay">
                <div className="spinner" />
                <span>Running review...</span>
              </div>
            )}
            {!expert && !isLoading && (
              <p className="empty-state">No expert issues found.</p>
            )}
            {expert && (
              <div className="issues-list">
                {expertGroups.map((group) => {
                  const list = expert[group.key] || [];
                  if (!list.length) return null;
                  return (
                    <div key={group.key} className="group-block">
                      <div className="section-header">
                        <h3>{group.label}</h3>
                        <span>
                          {list.length} suggestion{list.length > 1 ? "s" : ""}
                        </span>
                      </div>
                      {list.map((issue, idx) => (
                        <IssueCard
                          key={`${group.key}-${issue.file}-${issue.line_number}-${idx}`}
                          pullRequestId={pullRequestId}
                          repository={repository}
                          issue={issue}
                          kind="Issue"
                          category={group.label}
                          badgeLabel={`Expert · ${group.label.toLowerCase()}`}
                          index={idx}
                        />
                      ))}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export default ExpertPage;
