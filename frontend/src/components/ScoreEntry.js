import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import axios from "axios";
import { useParams, useNavigate, Link, useSearchParams } from "react-router-dom";
import getAPIUrl from "./API_FIX";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = getAPIUrl(BACKEND_URL);

/**
 * Score entry keyboard strategy (deliberate, do not change lightly):
 *
 * 1. Field order is linear in sheet order:
 *    for each match-type × caliber × stage: [Score] then [X]
 * 2. Tab / Shift+Tab: browser default within that order (explicit tabIndex).
 * 3. Enter: move to the next score field (same as Tab forward). Never submits.
 * 4. Focus: select-all so overwrite is one keystroke.
 * 5. Submit only via the "Save All Scores" button (type=submit).
 *
 * Empty score/X stays null (skipped stage), not 0 — do not coerce "" to 0.
 */
const ScoreEntry = () => {
  const { matchId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const formRootRef = useRef(null);

  const [match, setMatch] = useState(null);
  const [matchConfig, setMatchConfig] = useState(null);
  const [allShooters, setAllShooters] = useState([]);
  const [rosterIds, setRosterIds] = useState([]);
  const [showAllShooters, setShowAllShooters] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
    shooter_id: searchParams.get("shooter") || "",
    match_id: matchId,
    scores: [],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          setError("Authentication required. Please log in again.");
          setLoading(false);
          return;
        }

        const config = {
          headers: { Authorization: `Bearer ${token}` },
        };

        const [matchResponse, configResponse, shootersResponse, rosterResponse] =
          await Promise.all([
            axios.get(`${API}/matches/${matchId}`, config),
            axios.get(`${API}/match-config/${matchId}`, config),
            axios.get(`${API}/shooters`, config),
            axios.get(`${API}/matches/${matchId}/roster`, config).catch(() => null),
          ]);

        setMatch(matchResponse.data);
        setMatchConfig(configResponse.data);
        setAllShooters(shootersResponse.data || []);

        const members = rosterResponse?.data?.members || [];
        const ids = members.map((m) => m.shooter.id);
        setRosterIds(ids);
        // If roster is empty, show full directory by default
        setShowAllShooters(ids.length === 0);

        setLoading(false);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load required data. Please try again.");
        setLoading(false);
      }
    };

    fetchData();
  }, [matchId]);

  // Build empty stage rows from match config
  const buildEmptyScores = useCallback((config) => {
    const initialScores = [];
    config.match_types.forEach((matchType) => {
      matchType.calibers.forEach((caliber) => {
        const stages = matchType.entry_stages.map((stageName) => ({
          name: stageName,
          score: null,
          x_count: null,
        }));
        initialScores.push({
          match_type_instance: matchType.instance_name,
          caliber: caliber,
          stages: stages,
        });
      });
    });
    return initialScores;
  }, []);

  // Initialize score forms when shooter is selected
  useEffect(() => {
    if (!matchConfig || !formData.shooter_id || matchConfig.match_types.length === 0) {
      return;
    }

    let cancelled = false;

    const fetchExistingScores = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        const config = {
          headers: { Authorization: `Bearer ${token}` },
        };

        const scoreResponse = await axios.get(
          `${API}/scores?shooter_id=${formData.shooter_id}&match_id=${matchId}`,
          config
        );
        if (cancelled) return;

        const existingScores = scoreResponse.data;
        const existingScoreMap = {};
        existingScores.forEach((score) => {
          const key = `${score.match_type_instance}-${score.caliber}`;
          existingScoreMap[key] = score;
        });

        const initialScores = [];
        matchConfig.match_types.forEach((matchType) => {
          matchType.calibers.forEach((caliber) => {
            const key = `${matchType.instance_name}-${caliber}`;
            if (existingScoreMap[key]) {
              initialScores.push({
                match_type_instance: matchType.instance_name,
                caliber: caliber,
                stages: existingScoreMap[key].stages,
              });
            } else {
              const stages = matchType.entry_stages.map((stageName) => ({
                name: stageName,
                score: null,
                x_count: null,
              }));
              initialScores.push({
                match_type_instance: matchType.instance_name,
                caliber: caliber,
                stages: stages,
              });
            }
          });
        });

        setFormData((prev) => ({
          ...prev,
          scores: initialScores,
        }));
      } catch (err) {
        console.error("Error fetching existing scores:", err);
        if (cancelled) return;
        setFormData((prev) => ({
          ...prev,
          scores: buildEmptyScores(matchConfig),
        }));
      }
    };

    fetchExistingScores();
    return () => {
      cancelled = true;
    };
    // Only re-run when shooter or config identity changes — not when scores mutate
  }, [formData.shooter_id, matchConfig, matchId, buildEmptyScores]);

  const shootersForSelect = useMemo(() => {
    if (showAllShooters || rosterIds.length === 0) {
      return allShooters;
    }
    const set = new Set(rosterIds);
    const rostered = allShooters.filter((s) => set.has(s.id));
    // If current selection is outside roster, still include them so the select stays valid
    if (
      formData.shooter_id &&
      !set.has(formData.shooter_id) &&
      !rostered.some((s) => s.id === formData.shooter_id)
    ) {
      const extra = allShooters.find((s) => s.id === formData.shooter_id);
      if (extra) return [extra, ...rostered];
    }
    return rostered;
  }, [allShooters, rosterIds, showAllShooters, formData.shooter_id]);

  const handleShooterChange = (e) => {
    setFormData({
      shooter_id: e.target.value,
      match_id: matchId,
      scores: [],
    });
    setError(null);
  };

  const handleStageChange = (scoreIndex, stageIndex, field, value) => {
    setFormData((prev) => {
      const updatedScores = prev.scores.map((s, i) => {
        if (i !== scoreIndex) return s;
        const stages = s.stages.map((st, j) => {
          if (j !== stageIndex) return st;
          if (value === "") {
            return { ...st, [field]: null };
          }
          const parsed = parseInt(value, 10);
          if (Number.isNaN(parsed)) {
            return { ...st, [field]: null };
          }
          return { ...st, [field]: parsed };
        });
        return { ...s, stages };
      });
      return { ...prev, scores: updatedScores };
    });
  };

  /** Collect score inputs in DOM order under the form root. */
  const getScoreInputs = () => {
    if (!formRootRef.current) return [];
    return Array.from(
      formRootRef.current.querySelectorAll('input[data-score-nav="1"]')
    );
  };

  const focusInputAt = (index) => {
    const inputs = getScoreInputs();
    if (index < 0 || index >= inputs.length) return;
    const el = inputs[index];
    el.focus();
    // Select contents for quick overwrite (score sheet workflow)
    if (typeof el.select === "function") {
      el.select();
    }
  };

  const handleScoreKeyDown = (e) => {
    // Enter advances like Tab; never submit the form from a field
    if (e.key === "Enter") {
      e.preventDefault();
      const inputs = getScoreInputs();
      const idx = inputs.indexOf(e.target);
      if (idx >= 0 && idx < inputs.length - 1) {
        focusInputAt(idx + 1);
      }
      return;
    }

    // Escape clears the current field (sets null) without leaving
    if (e.key === "Escape") {
      e.preventDefault();
      e.target.value = "";
      e.target.dispatchEvent(new Event("input", { bubbles: true }));
      // onChange may not fire from programmatic value set — call path via dataset
      const scoreIndex = parseInt(e.target.dataset.scoreIndex, 10);
      const stageIndex = parseInt(e.target.dataset.stageIndex, 10);
      const field = e.target.dataset.field;
      if (!Number.isNaN(scoreIndex) && !Number.isNaN(stageIndex) && field) {
        handleStageChange(scoreIndex, stageIndex, field, "");
      }
    }
  };

  const handleScoreFocus = (e) => {
    if (typeof e.target.select === "function") {
      e.target.select();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.shooter_id || formData.scores.length === 0) {
      setError("Please select a shooter and enter scores");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Authentication required. Please log in again.");
        setSaving(false);
        return;
      }

      const config = {
        headers: { Authorization: `Bearer ${token}` },
      };

      // Submit each score entry independently; keep original POST semantics
      const submissionPromises = formData.scores.map((scoreEntry) => {
        return axios.post(
          `${API}/scores`,
          {
            shooter_id: formData.shooter_id,
            match_id: matchId,
            match_type_instance: scoreEntry.match_type_instance,
            caliber: scoreEntry.caliber,
            stages: scoreEntry.stages,
          },
          config
        );
      });

      await Promise.all(submissionPromises);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/matches/${matchId}`);
      }, 1500);
    } catch (err) {
      console.error("Error submitting scores:", err);
      setError(
        err.response?.data?.detail || "Failed to save scores. Please try again."
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-4 text-center">Loading form data...</div>
    );
  }
  if (error && !match) {
    return (
      <div className="container mx-auto p-4 text-center text-red-500">{error}</div>
    );
  }
  if (!match || !matchConfig) {
    return (
      <div className="container mx-auto p-4 text-center">Match data not found</div>
    );
  }

  if (success) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-green-100 text-green-700 p-6 rounded-lg shadow-md text-center">
          <h2 className="text-xl font-bold mb-2">Scores Saved Successfully!</h2>
          <p>Redirecting to match details...</p>
        </div>
      </div>
    );
  }

  // Group scores by match type for display (preserve formData.scores order)
  const scoresByType = {};
  if (formData.scores.length > 0) {
    formData.scores.forEach((score) => {
      const matchTypeObj = matchConfig.match_types.find(
        (mt) => mt.instance_name === score.match_type_instance
      );
      if (!matchTypeObj) return;

      const key = matchTypeObj.type;
      if (!scoresByType[key]) {
        scoresByType[key] = [];
      }
      scoresByType[key].push({
        ...score,
        matchTypeObj,
      });
    });
  }

  const calculateSubtotals = (score, matchTypeObj) => {
    const subtotals = {};

    if (
      matchTypeObj.subtotal_mappings &&
      Object.keys(matchTypeObj.subtotal_mappings).length > 0
    ) {
      for (const [subtotalName, sourceStages] of Object.entries(
        matchTypeObj.subtotal_mappings
      )) {
        let subtotalScore = 0;
        let subtotalXCount = 0;

        score.stages.forEach((stage) => {
          if (sourceStages.includes(stage.name)) {
            if (stage.score !== null) {
              subtotalScore += stage.score;
            }
            if (stage.x_count !== null) {
              subtotalXCount += stage.x_count;
            }
          }
        });

        subtotals[subtotalName] = {
          score: subtotalScore,
          x_count: subtotalXCount,
        };
      }
    }

    return subtotals;
  };

  const calculateTotals = (score) => {
    const allNull = score.stages.every((stage) => stage.score === null);

    if (allNull) {
      return {
        totalScore: null,
        totalXCount: null,
        allStagesTotalNull: true,
      };
    }

    return {
      totalScore: score.stages.reduce(
        (sum, stage) => (stage.score !== null ? sum + stage.score : sum),
        0
      ),
      totalXCount: score.stages.reduce(
        (sum, stage) => (stage.x_count !== null ? sum + stage.x_count : sum),
        0
      ),
      allStagesTotalNull: false,
    };
  };

  // Sequential tabIndex starting after shooter select (tabIndex 1)
  let navIndex = 2;

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Add Scores</h1>
          <p className="text-gray-600">
            Match: {match.name} ({new Date(match.date).toLocaleDateString()})
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Keyboard: Tab / Enter moves Score → X → next stage. Esc clears field.
            Save only via the button.
          </p>
        </div>
        <Link
          to={`/matches/${matchId}`}
          className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
        >
          Back to Match
        </Link>
      </div>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4" role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow" ref={formRootRef}>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="mb-6">
            <label
              htmlFor="shooter_id"
              className="block text-lg font-medium text-gray-700 mb-2"
            >
              Shooter
            </label>
            <div className="flex flex-col md:flex-row md:items-center gap-3">
              <select
                id="shooter_id"
                value={formData.shooter_id}
                onChange={handleShooterChange}
                tabIndex={1}
                className="w-full md:w-1/2 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">-- Select Shooter --</option>
                {shootersForSelect.map((shooter) => (
                  <option key={shooter.id} value={shooter.id}>
                    {shooter.name}
                  </option>
                ))}
              </select>
              {rosterIds.length > 0 && (
                <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={showAllShooters}
                    onChange={(e) => setShowAllShooters(e.target.checked)}
                    tabIndex={-1}
                  />
                  Show full directory
                </label>
              )}
            </div>
            {rosterIds.length > 0 && !showAllShooters && (
              <p className="text-xs text-gray-500 mt-1">
                Showing match roster only ({rosterIds.length}). Toggle “Show full
                directory” to pick someone else.
              </p>
            )}
          </div>

          {formData.shooter_id && Object.keys(scoresByType).length > 0 && (
            <div className="space-y-8">
              {Object.entries(scoresByType).map(([matchType, scores]) => (
                <div key={matchType} className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-100 p-4 border-b">
                    <h3 className="text-lg font-semibold">{matchType} Scores</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Enter scores for all calibers in this match type
                    </p>
                  </div>

                  <div className="p-4">
                    <div className="border-b mb-4">
                      <div className="flex overflow-x-auto">
                        {scores.map((score, idx) => (
                          <button
                            key={idx}
                            type="button"
                            tabIndex={-1}
                            onClick={() => {
                              document
                                .getElementById(
                                  `score-${matchType}-${score.caliber}`
                                )
                                ?.scrollIntoView({
                                  behavior: "smooth",
                                  block: "start",
                                });
                            }}
                            className="px-4 py-2 font-medium text-sm whitespace-nowrap text-gray-600 hover:text-gray-900"
                          >
                            {score.caliber}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-8">
                      {scores.map((score) => {
                        const scoreIndex = formData.scores.findIndex(
                          (s) =>
                            s.match_type_instance === score.match_type_instance &&
                            s.caliber === score.caliber
                        );

                        if (scoreIndex === -1) return null;

                        const matchTypeObj = score.matchTypeObj;
                        const maxScore = matchTypeObj ? matchTypeObj.max_score : 0;

                        const { totalScore, totalXCount, allStagesTotalNull } =
                          calculateTotals(formData.scores[scoreIndex]);
                        const subtotals = calculateSubtotals(
                          formData.scores[scoreIndex],
                          matchTypeObj
                        );

                        return (
                          <div
                            key={`${score.match_type_instance}-${score.caliber}`}
                            id={`score-${matchType}-${score.caliber}`}
                            className="border rounded-lg p-4"
                          >
                            <h4 className="text-lg font-medium mb-3">
                              {score.match_type_instance} - {score.caliber}
                            </h4>

                            <div className="mb-6">
                              <h5 className="font-medium mb-3 text-gray-700">
                                Entry Stages
                              </h5>
                              {/*
                                Single-column stack keeps visual order === tab order
                                (Score then X for each stage). Avoid multi-column
                                stage grids which scramble keyboard path.
                              */}
                              <div className="space-y-3 max-w-xl">
                                {formData.scores[scoreIndex].stages.map(
                                  (stage, stageIdx) => {
                                    const scoreTab = navIndex++;
                                    const xTab = navIndex++;
                                    return (
                                      <div
                                        key={stageIdx}
                                        className="border p-3 rounded hover:shadow-md transition-shadow grid grid-cols-[4rem_1fr_1fr] gap-3 items-end"
                                      >
                                        <div className="font-medium text-sm pb-2">
                                          {stage.name}
                                        </div>
                                        <div>
                                          <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Score
                                          </label>
                                          <input
                                            type="number"
                                            inputMode="numeric"
                                            min="0"
                                            max="100"
                                            data-score-nav="1"
                                            data-score-index={scoreIndex}
                                            data-stage-index={stageIdx}
                                            data-field="score"
                                            tabIndex={scoreTab}
                                            value={
                                              stage.score === null ? "" : stage.score
                                            }
                                            onChange={(e) =>
                                              handleStageChange(
                                                scoreIndex,
                                                stageIdx,
                                                "score",
                                                e.target.value
                                              )
                                            }
                                            onKeyDown={handleScoreKeyDown}
                                            onFocus={handleScoreFocus}
                                            className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          />
                                        </div>
                                        <div>
                                          <label className="block text-sm font-medium text-gray-700 mb-1">
                                            X Count
                                          </label>
                                          <input
                                            type="number"
                                            inputMode="numeric"
                                            min="0"
                                            max="10"
                                            data-score-nav="1"
                                            data-score-index={scoreIndex}
                                            data-stage-index={stageIdx}
                                            data-field="x_count"
                                            tabIndex={xTab}
                                            value={
                                              stage.x_count === null
                                                ? ""
                                                : stage.x_count
                                            }
                                            onChange={(e) =>
                                              handleStageChange(
                                                scoreIndex,
                                                stageIdx,
                                                "x_count",
                                                e.target.value
                                              )
                                            }
                                            onKeyDown={handleScoreKeyDown}
                                            onFocus={handleScoreFocus}
                                            className="w-full px-3 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          />
                                        </div>
                                      </div>
                                    );
                                  }
                                )}
                              </div>
                            </div>

                            {Object.keys(subtotals).length > 0 && (
                              <div className="mb-6">
                                <h5 className="font-medium mb-3 text-gray-700">
                                  Subtotals (Automatically Calculated)
                                </h5>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                  {Object.entries(subtotals).map(
                                    ([subtotalName, values]) => (
                                      <div
                                        key={subtotalName}
                                        className="border p-3 rounded bg-gray-50"
                                      >
                                        <h5 className="font-medium mb-2">
                                          {subtotalName}
                                        </h5>
                                        <div className="grid grid-cols-2 gap-3">
                                          <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                              Score
                                            </label>
                                            <div className="w-full px-3 py-1 border rounded bg-gray-100 font-medium">
                                              {values.score}
                                            </div>
                                          </div>
                                          <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                              X Count
                                            </label>
                                            <div className="w-full px-3 py-1 border rounded bg-gray-100 font-medium">
                                              {values.x_count}
                                            </div>
                                          </div>
                                        </div>
                                        {matchTypeObj.subtotal_mappings[
                                          subtotalName
                                        ] && (
                                          <div className="mt-2 text-xs text-gray-500">
                                            Sum of:{" "}
                                            {matchTypeObj.subtotal_mappings[
                                              subtotalName
                                            ].join(", ")}
                                          </div>
                                        )}
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}

                            <div className="mt-4 bg-gray-50 p-3 rounded">
                              <h5 className="font-medium mb-2">Total</h5>
                              <div className="flex justify-between items-center">
                                {totalScore === null || allStagesTotalNull ? (
                                  <div>
                                    <span className="text-lg font-semibold">-</span>
                                    <span className="ml-4 text-gray-600">
                                      X Count: -
                                    </span>
                                  </div>
                                ) : (
                                  <>
                                    <div>
                                      <span className="text-lg font-semibold">
                                        {totalScore}
                                      </span>
                                      <span className="text-gray-600">
                                        {" "}
                                        / {maxScore}
                                      </span>
                                      <span className="ml-4 text-gray-600">
                                        X Count: {totalXCount}
                                      </span>
                                    </div>
                                    <div className="text-sm text-gray-500">
                                      {maxScore > 0
                                        ? Math.round((totalScore / maxScore) * 100)
                                        : 0}
                                      %
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}

              <div className="flex justify-end mt-8">
                <button
                  type="submit"
                  disabled={saving}
                  tabIndex={navIndex}
                  className={`bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 ${
                    saving ? "opacity-70 cursor-not-allowed" : ""
                  }`}
                >
                  {saving ? "Saving..." : "Save All Scores"}
                </button>
              </div>
            </div>
          )}

          {formData.shooter_id && Object.keys(scoresByType).length === 0 && (
            <div className="text-center p-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">
                No match types configured for this match. Please update the match
                configuration.
              </p>
            </div>
          )}

          {!formData.shooter_id && (
            <div className="text-center p-8 bg-gray-50 rounded-lg">
              <p className="text-gray-500">
                Please select a shooter to enter scores.
              </p>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default ScoreEntry;
