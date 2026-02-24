import { useMemo, useState } from "react";
import ReviewPage from "./pages/ReviewPage";
import ScoresPage from "./pages/ScoresPage";
import StandardsPage from "./pages/StandardsPage";
import ExpertPage from "./pages/ExpertPage";

const severityOrder = {
  critical: 0,
  major: 1,
  minor: 2,
  nitpick: 3
};

function extractPrId(url) {
  if (!url) return null;
  const match = url.match(/pullrequest\/(\d+)/i);
  if (match) return parseInt(match[1], 10);
  const numeric = url.trim().match(/\d+$/);
  if (numeric) return parseInt(numeric[0], 10);
  return null;
}

function extractRepo(url) {
  if (!url) return null;
  const match = url.match(/_git\/([^/]+)/i);
  if (match) return match[1];
  return null;
}

function sortBySeverity(list) {
  return [...list].sort((a, b) => {
    const sa = (a.severity || "").toLowerCase();
    const sb = (b.severity || "").toLowerCase();
    const wa = Object.prototype.hasOwnProperty.call(severityOrder, sa)
      ? severityOrder[sa]
      : 99;
    const wb = Object.prototype.hasOwnProperty.call(severityOrder, sb)
      ? severityOrder[sb]
      : 99;
    if (wa !== wb) return wa - wb;
    const ca = Number(a.confidence ?? 0);
    const cb = Number(b.confidence ?? 0);
    return cb - ca;
  });
}

function formatScore(value) {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return value.toFixed(1);
}

function App() {
  const [prUrl, setPrUrl] = useState("");
  const [extraPrompt, setExtraPrompt] = useState("");
  const [status, setStatus] = useState("Ready.");
  const [meta, setMeta] = useState("No review run yet.");
  const [activePage, setActivePage] = useState("review");
  const [isLoading, setIsLoading] = useState(false);
  const [currentRepo, setCurrentRepo] = useState(null);
  const [review, setReview] = useState(null);

  const counts = useMemo(() => {
    if (!review) {
      return {
        total: 0,
        rules: 0,
        bugs: 0,
        perf: 0,
        sec: 0,
        refactor: 0,
        tests: 0
      };
    }
    const ruleViolations = review.rule_result?.rule_violations ?? [];
    const expert = review.expert_result;
    const bugs = expert?.bugs ?? [];
    const perf = expert?.performance_issues ?? [];
    const sec = expert?.security_issues ?? [];
    const refactor = expert?.refactor_suggestions ?? [];
    const tests = expert?.test_cases_to_add ?? [];
    const total =
      ruleViolations.length +
      bugs.length +
      perf.length +
      sec.length +
      refactor.length +
      tests.length;
    return {
      total,
      rules: ruleViolations.length,
      bugs: bugs.length,
      perf: perf.length,
      sec: sec.length,
      refactor: refactor.length,
      tests: tests.length
    };
  }, [review]);

  const complianceScore = useMemo(() => {
    if (!review) return null;
    const ruleResult = review.rule_result;
    if (typeof ruleResult.compliance_score === "number") {
      return ruleResult.compliance_score;
    }
    return review.scores?.rule_compliance ?? null;
  }, [review]);

  const scoreReasons = useMemo(() => {
    if (!review) return null;
    const expert = review.expert_result || {};
    const ruleResult = review.rule_result || {};
    const perfIssues = expert.performance_issues || [];
    const secIssues = expert.security_issues || [];
    const refactorIssues = expert.refactor_suggestions || [];
    const bugIssues = (expert.bugs || []).length;
    const testsIssues = (expert.test_cases_to_add || []).length;
    const ruleViolations = (ruleResult.rule_violations || []).length;

    const buildSummary = (issues, label) => {
      if (!issues || issues.length === 0) {
        return {
          pros: [`No major ${label} issues detected in this review.`],
          cons: [
            `Minor ${label} improvements may still exist; review suggestions if present.`
          ]
        };
      }
      const first = issues[0]?.description || "";
      const extraCount = issues.length - 1;
      return {
        pros: [
          `Detected ${issues.length} ${label} issue${issues.length > 1 ? "s" : ""} so the score reflects real risks.`
        ],
        cons: [
          first,
          ...(extraCount > 0
            ? [`+${extraCount} more ${label} issue${extraCount > 1 ? "s" : ""}.`]
            : [])
        ]
      };
    };

    const performance = buildSummary(perfIssues, "performance");
    const security = buildSummary(secIssues, "security");
    const maintainability = buildSummary(refactorIssues, "maintainability");

    const readability = {
      pros:
        refactorIssues.length === 0
          ? [
              "Structure and naming look consistent.",
              "Readability is generally good."
            ]
          : [
              "Code is readable overall.",
              "Some refactors are recommended to simplify complex sections."
            ],
      cons: [
        refactorIssues[0]?.description ||
          "Review refactor suggestions to improve readability and structure."
      ]
    };

    const overallConsParts = [];
    if (bugIssues)
      overallConsParts.push(
        `${bugIssues} potential bug${bugIssues > 1 ? "s" : ""} reported by expert review.`
      );
    if (perfIssues.length)
      overallConsParts.push(
        `${perfIssues.length} performance issue(s) that can impact responsiveness or throughput.`
      );
    if (secIssues.length)
      overallConsParts.push(
        `${secIssues.length} security issue(s) that may expose vulnerabilities.`
      );
    if (refactorIssues.length)
      overallConsParts.push(
        `${refactorIssues.length} refactor suggestion(s) indicating maintainability concerns.`
      );
    if (testsIssues)
      overallConsParts.push(
        `${testsIssues} missing or weak test case(s) affecting test coverage.`
      );
    if (ruleViolations)
      overallConsParts.push(
        `${ruleViolations} coding-standard rule violation(s) detected by automated checks.`
      );

    return {
      overall: {
        pros: [
          "Most dimensions score reasonably.",
          "See individual scores to identify strongest areas."
        ],
        cons:
          overallConsParts.length > 0
            ? overallConsParts
            : ["No major issues detected across rules and expert checks."]
      },
      performance,
      scalability: {
        pros:
          expert.scores &&
          typeof expert.scores.scalability === "number" &&
          expert.scores.scalability >= 7
            ? [
                "Design looks scalable for expected load and usage patterns.",
                "No major scalability bottlenecks were identified."
              ]
            : [
                "Scalability is acceptable for current load.",
                "Some areas could be optimized further."
              ],
        cons: [
          refactorIssues[0]?.description ||
            "Consider reviewing shared components and data flows to improve scalability."
        ]
      },
      security,
      maintainability,
      readability
    };
  }, [review]);

  const hasResults = !!review;

  const runReview = async () => {
    const prId = extractPrId(prUrl);
    const repo = extractRepo(prUrl);
    if (!prId) {
      alert("Could not extract pull request ID from the URL.");
      return;
    }
    setCurrentRepo(repo);
    setIsLoading(true);
    setStatus(`Running review for PR ${prId}...`);
    setMeta("Running review...");
    try {
      const resp = await fetch("/review/pr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pull_request_id: prId,
          repository: repo,
          extra_prompt: extraPrompt.trim() || null
        })
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || "Review failed.");
      }
      const data = await resp.json();
      setReview({
        ...data,
        rule_result: {
          rule_violations: sortBySeverity(data.rule_result?.rule_violations ?? []),
          compliance_score: data.rule_result?.compliance_score
        },
        expert_result: {
          ...data.expert_result,
          bugs: sortBySeverity(data.expert_result?.bugs ?? []),
          performance_issues: sortBySeverity(
            data.expert_result?.performance_issues ?? []
          ),
          security_issues: sortBySeverity(data.expert_result?.security_issues ?? []),
          refactor_suggestions: sortBySeverity(
            data.expert_result?.refactor_suggestions ?? []
          ),
          test_cases_to_add: sortBySeverity(
            data.expert_result?.test_cases_to_add ?? []
          ),
          architectural_concerns: sortBySeverity(
            data.expert_result?.architectural_concerns ?? []
          )
        }
      });
      setStatus(`Review complete for PR ${prId}.`);
      setMeta(`PR ${prId} · Scores and suggestions loaded.`);
    } catch (err) {
      console.error(err);
      setReview(null);
      setStatus(`Error: ${err?.message ?? "Review failed."}`);
      setMeta("Review failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const clearAll = () => {
    setPrUrl("");
    setExtraPrompt("");
    setReview(null);
    setStatus("Ready.");
    setMeta("No review run yet.");
  };

  return (
    <div className="app-root">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">PR</div>
          <div className="logo-text">
            <span className="logo-title">AI PR Reviewer</span>
            <span className="logo-subtitle">Azure DevOps · OpenAI</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            type="button"
            className={activePage === "review" ? "nav-item active" : "nav-item"}
            onClick={() => setActivePage("review")}
          >
            Review
          </button>
          <button
            type="button"
            className={activePage === "scores" ? "nav-item active" : "nav-item"}
            onClick={() => setActivePage("scores")}
          >
            Scores
          </button>
          <button
            type="button"
            className={activePage === "standards" ? "nav-item active" : "nav-item"}
            onClick={() => setActivePage("standards")}
          >
            Coding standards
          </button>
          <button
            type="button"
            className={activePage === "expert" ? "nav-item active" : "nav-item"}
            onClick={() => setActivePage("expert")}
          >
            Expert review
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">{status}</div>
          {hasResults && (
            <div className="sidebar-summary">
              <span>PR #{review.pull_request_id}</span>
              <span>{counts.total} suggestions</span>
            </div>
          )}
        </div>
      </aside>

      <main className="app-main">
        <header className="title-row">
          <div>
            <h1>AI PR Reviewer</h1>
            <p className="tagline">
              Review Azure DevOps pull requests with
              <strong> coding standards</strong> and
              <strong> expert analysis</strong> before posting comments.
            </p>
          </div>
          <div className="badge-pill">
            <span>{currentRepo || "Workspace"}</span>
          </div>
        </header>

        {activePage === "review" && (
          <ReviewPage
            prUrl={prUrl}
            extraPrompt={extraPrompt}
            setPrUrl={setPrUrl}
            setExtraPrompt={setExtraPrompt}
            status={status}
            isLoading={isLoading}
            hasResults={hasResults}
            complianceScore={complianceScore}
            counts={counts}
            review={review}
            onRunReview={runReview}
            onClear={clearAll}
            formatScore={formatScore}
          />
        )}

        {activePage === "scores" && (
          <ScoresPage
            meta={meta}
            hasResults={hasResults}
            review={review}
            counts={counts}
            complianceScore={complianceScore}
            formatScore={formatScore}
            scoreReasons={scoreReasons}
          />
        )}

        {activePage === "standards" && (
          <StandardsPage
            meta={meta}
            hasResults={hasResults}
            counts={counts}
            isLoading={isLoading}
            pullRequestId={review ? review.pull_request_id : null}
            repository={currentRepo}
            items={review ? review.rule_result.rule_violations : []}
          />
        )}

        {activePage === "expert" && (
          <ExpertPage
            meta={meta}
            hasResults={hasResults}
            counts={counts}
            isLoading={isLoading}
            pullRequestId={review ? review.pull_request_id : null}
            repository={currentRepo}
            expert={review ? review.expert_result : null}
          />
        )}

        {isLoading && (
          <div className="global-loading">
            <div className="global-loading-card">
              <div className="spinner spinner-large" />
              <p className="global-loading-title">Analyzing your pull request…</p>
              <p className="global-loading-text">
                Fetching files, running coding rules, and generating expert suggestions.
              </p>
              <div className="global-loading-bar">
                <div className="global-loading-bar-fill" />
              </div>
              <ul className="global-loading-hints">
                <li>Large pull requests can take a bit longer.</li>
                <li>You can switch between tabs while the review runs.</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
export default App;
