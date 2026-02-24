import React from "react";

function ScoresPage({
  meta,
  hasResults,
  review,
  counts,
  complianceScore,
  formatScore,
  scoreReasons
}) {
  return (
    <section className="panel panel-results">
      <div className="section-header">
        <h2>Scores overview</h2>
        <span className="meta">{meta}</span>
      </div>
      {!hasResults && (
        <p className="empty-state">
          Run a review from the Review page to see scores.
        </p>
      )}
      {hasResults && (
        <div className="results-scroll">
          <div className="scores">
            <div className="scores-grid">
              <div className="score-chip overall">
                <strong>Overall</strong>
                <span>{formatScore(review.scores.overall_score)}</span>
                <span className="score-scale">/ 10</span>
              </div>
              <div className="score-chip">
                <strong>Performance</strong>
                <span>{formatScore(review.scores.performance)}</span>
              </div>
              <div className="score-chip">
                <strong>Scalability</strong>
                <span>{formatScore(review.scores.scalability)}</span>
              </div>
              <div className="score-chip">
                <strong>Security</strong>
                <span>{formatScore(review.scores.security)}</span>
              </div>
              <div className="score-chip">
                <strong>Maintainability</strong>
                <span>{formatScore(review.scores.maintainability)}</span>
              </div>
              <div className="score-chip">
                <strong>Readability</strong>
                <span>{formatScore(review.scores.readability)}</span>
              </div>
            </div>
          </div>

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

          {scoreReasons && (
            <div className="score-explanations">
              <div className="score-explanation">
                <h3>Overall</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.overall.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.overall.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className="score-explanation">
                <h3>Performance</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.performance.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.performance.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className="score-explanation">
                <h3>Scalability</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.scalability.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.scalability.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className="score-explanation">
                <h3>Security</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.security.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.security.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className="score-explanation">
                <h3>Maintainability</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.maintainability.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.maintainability.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className="score-explanation">
                <h3>Readability</h3>
                <div className="score-list">
                  <div>
                    <strong>Pros</strong>
                    <ul>
                      {scoreReasons.readability.pros.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <strong>Cons</strong>
                    <ul>
                      {scoreReasons.readability.cons.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default ScoresPage;
