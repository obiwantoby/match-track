import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = BACKEND_URL?.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`;

/**
 * Match-day roster management.
 *
 * Layering:
 * - Shooter = global person (never deleted from here)
 * - League  = evolving club/series roster (optional link)
 * - Match   = day-of snapshot; can have guests not on the league
 *
 * Sync from league is additive only. Promote grows the league over time.
 */
const MatchRoster = ({ matchId, onRosterChange }) => {
  const { isAdmin } = useAuth();
  const [match, setMatch] = useState(null);
  const [league, setLeague] = useState(null);
  const [leagues, setLeagues] = useState([]);
  const [roster, setRoster] = useState(null);
  const [allShooters, setAllShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [linkLeagueId, setLinkLeagueId] = useState("");
  const [syncing, setSyncing] = useState(false);

  const showSuccess = (msg) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(""), 3500);
  };

  const load = useCallback(async () => {
    try {
      const [matchRes, rosterRes, shootersRes, leaguesRes] = await Promise.all([
        axios.get(`${API}/matches/${matchId}`),
        axios.get(`${API}/matches/${matchId}/roster`),
        axios.get(`${API}/shooters`),
        axios.get(`${API}/leagues`).catch(() => ({ data: [] })),
      ]);

      setMatch(matchRes.data);
      setRoster(rosterRes.data);
      setAllShooters(shootersRes.data || []);
      setLeagues(leaguesRes.data || []);
      setLinkLeagueId(matchRes.data.league_id || "");

      if (matchRes.data.league_id) {
        try {
          const lr = await axios.get(
            `${API}/leagues/${matchRes.data.league_id}`
          );
          setLeague(lr.data);
        } catch {
          setLeague(null);
        }
      } else {
        setLeague(null);
      }

      setError(null);
      if (onRosterChange) onRosterChange(rosterRes.data);
    } catch (err) {
      console.error("Failed to load match roster:", err);
      setError(err.response?.data?.detail || "Failed to load match roster.");
    } finally {
      setLoading(false);
    }
  }, [matchId, onRosterChange]);

  useEffect(() => {
    load();
  }, [load]);

  const rosterIdSet = new Set(
    (roster?.members || []).map((m) => m.shooter.id)
  );

  const availableToAdd = allShooters.filter((s) => !rosterIdSet.has(s.id));

  const leagueIdSet = new Set(league?.roster_shooter_ids || []);

  const toggleSelected = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleAddSelected = async () => {
    if (selectedIds.length === 0 && !newName.trim()) {
      setError("Select at least one existing shooter or enter a new name.");
      return;
    }
    setAdding(true);
    setError(null);
    try {
      const body = {
        shooter_ids: selectedIds,
        new_shooters: newName.trim() ? [{ name: newName.trim() }] : [],
      };
      const res = await axios.post(`${API}/matches/${matchId}/roster`, body);
      setRoster(res.data);
      setSelectedIds([]);
      setNewName("");
      const shootersRes = await axios.get(`${API}/shooters`);
      setAllShooters(shootersRes.data || []);
      showSuccess("Roster updated");
      if (onRosterChange) onRosterChange(res.data);
    } catch (err) {
      console.error("Add to roster failed:", err);
      setError(err.response?.data?.detail || "Failed to update roster.");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (member) => {
    const sid = member.shooter.id;
    const name = member.shooter.name;
    let deleteScores = false;

    if (member.has_scores) {
      const ok = window.confirm(
        `"${name}" has ${member.score_count} score(s) in this match.\n\n` +
          "OK = remove from roster AND delete their scores for THIS match only.\n" +
          "Cancel = leave them on the roster.\n\n" +
          "Global profile and league roster are never deleted from here."
      );
      if (!ok) return;
      deleteScores = true;
    } else {
      const ok = window.confirm(
        `Remove "${name}" from this match roster?\n\nProfile and league stay unchanged.`
      );
      if (!ok) return;
    }

    setBusyId(sid);
    setError(null);
    try {
      await axios.delete(
        `${API}/matches/${matchId}/roster/${sid}?delete_scores=${deleteScores}`
      );
      await load();
      showSuccess(
        deleteScores
          ? `Removed ${name} and their scores from this match`
          : `Removed ${name} from match roster`
      );
    } catch (err) {
      console.error("Remove from roster failed:", err);
      setError(err.response?.data?.detail || "Failed to remove from roster.");
    } finally {
      setBusyId(null);
    }
  };

  const handleAddScoredToRoster = async (member) => {
    setBusyId(member.shooter.id);
    setError(null);
    try {
      const res = await axios.post(`${API}/matches/${matchId}/roster`, {
        shooter_ids: [member.shooter.id],
        new_shooters: [],
      });
      setRoster(res.data);
      showSuccess(`Added ${member.shooter.name} to formal roster`);
      if (onRosterChange) onRosterChange(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add to roster.");
    } finally {
      setBusyId(null);
    }
  };

  const handleSyncFromLeague = async () => {
    setSyncing(true);
    setError(null);
    try {
      const res = await axios.post(
        `${API}/matches/${matchId}/roster/sync-from-league`
      );
      setRoster(res.data);
      showSuccess("Pulled new league members onto this match (additive)");
      if (onRosterChange) onRosterChange(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Sync from league failed.");
    } finally {
      setSyncing(false);
    }
  };

  const handlePromote = async (member) => {
    setBusyId(member.shooter.id);
    setError(null);
    try {
      await axios.post(
        `${API}/matches/${matchId}/roster/${member.shooter.id}/promote-to-league`
      );
      // Refresh league membership for badge display
      if (match?.league_id) {
        const lr = await axios.get(`${API}/leagues/${match.league_id}`);
        setLeague(lr.data);
      }
      showSuccess(
        `Added ${member.shooter.name} to the league for future matches`
      );
    } catch (err) {
      setError(err.response?.data?.detail || "Promote to league failed.");
    } finally {
      setBusyId(null);
    }
  };

  const handleLinkLeague = async () => {
    setSyncing(true);
    setError(null);
    try {
      const res = await axios.put(`${API}/matches/${matchId}/league`, {
        league_id: linkLeagueId || null,
        pull_roster: Boolean(linkLeagueId),
      });
      setMatch(res.data);
      if (res.data.league_id) {
        const lr = await axios.get(`${API}/leagues/${res.data.league_id}`);
        setLeague(lr.data);
      } else {
        setLeague(null);
      }
      await load();
      showSuccess(
        linkLeagueId
          ? "Linked league and pulled members onto match roster"
          : "Unlinked league (match roster kept)"
      );
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update league link.");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <p className="text-gray-500 p-4">Loading roster...</p>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded" role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </div>
      )}
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded" role="status">
          {success}
        </div>
      )}

      {/* League link panel */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-1">League link</h2>
        <p className="text-sm text-gray-600 mb-4">
          Optional. Link this match to a league so you can seed and grow a shared
          season roster. The match roster stays a day-of snapshot.
        </p>
        {league ? (
          <p className="text-sm mb-3">
            Linked to{" "}
            <Link
              to="/leagues"
              className="font-medium text-blue-600 hover:underline"
            >
              {league.name}
            </Link>
            {league.season ? ` (${league.season})` : ""} ·{" "}
            {(league.roster_shooter_ids || []).length} on league roster
          </p>
        ) : (
          <p className="text-sm text-gray-500 mb-3">Not linked to a league.</p>
        )}

        {isAdmin() && (
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">League</label>
              <select
                value={linkLeagueId}
                onChange={(e) => setLinkLeagueId(e.target.value)}
                className="px-3 py-2 border rounded min-w-[14rem]"
              >
                <option value="">— None —</option>
                {leagues.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                    {l.season ? ` (${l.season})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              disabled={syncing}
              onClick={handleLinkLeague}
              className="bg-gray-800 text-white px-3 py-2 rounded text-sm hover:bg-gray-900 disabled:opacity-70"
            >
              {syncing ? "Saving..." : "Save link"}
            </button>
            {match?.league_id && (
              <button
                type="button"
                disabled={syncing}
                onClick={handleSyncFromLeague}
                className="bg-indigo-600 text-white px-3 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-70"
                title="Add league members who are not yet on this match (never removes anyone)"
              >
                {syncing ? "Syncing..." : "Pull new from league"}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-1">Match Roster</h2>
        <p className="text-sm text-gray-600 mb-4">
          Who is competing in <strong>this match</strong>. Score entry prefers
          this list when it is non-empty. Removing someone here never deletes
          their global profile or league membership.
        </p>

        {(roster?.members || []).length === 0 ? (
          <p className="text-gray-500 text-sm mb-4">
            No formal roster yet. Link a league and pull members, add shooters
            below, or enter scores for anyone from the full directory.
          </p>
        ) : (
          <div className="overflow-x-auto mb-4">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">NRA</th>
                  <th className="px-4 py-2 text-left">Rating</th>
                  <th className="px-4 py-2 text-left">Scores</th>
                  <th className="px-4 py-2 text-left">League</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {roster.members.map((m) => {
                  const onLeague = leagueIdSet.has(m.shooter.id);
                  return (
                    <tr key={m.shooter.id}>
                      <td className="px-4 py-2 font-medium">
                        <Link
                          to={`/shooters/${m.shooter.id}`}
                          className="text-blue-600 hover:underline"
                        >
                          {m.shooter.name}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-gray-600">
                        {m.shooter.nra_number || "—"}
                      </td>
                      <td className="px-4 py-2 text-gray-600">
                        {m.shooter.rating || "—"}
                      </td>
                      <td className="px-4 py-2">
                        {m.has_scores ? (
                          <span className="text-green-700">{m.score_count}</span>
                        ) : (
                          <span className="text-gray-400">0</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        {!match?.league_id ? (
                          <span className="text-gray-400">—</span>
                        ) : onLeague ? (
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                            League
                          </span>
                        ) : (
                          <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                            Match guest
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right space-x-3">
                        {isAdmin() && (
                          <>
                            <Link
                              to={`/scores/add/${matchId}?shooter=${m.shooter.id}`}
                              className="text-green-600 hover:text-green-800"
                            >
                              Scores
                            </Link>
                            {match?.league_id && !onLeague && (
                              <button
                                type="button"
                                disabled={busyId === m.shooter.id}
                                onClick={() => handlePromote(m)}
                                className="text-indigo-600 hover:text-indigo-800 disabled:opacity-50"
                                title="Add this person to the league for future matches"
                              >
                                Promote to league
                              </button>
                            )}
                            <button
                              type="button"
                              disabled={busyId === m.shooter.id}
                              onClick={() => handleRemove(m)}
                              className="text-red-600 hover:text-red-800 disabled:opacity-50"
                            >
                              {busyId === m.shooter.id ? "..." : "Remove"}
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {(roster?.scored_but_not_on_roster || []).length > 0 && (
          <div className="mb-6 border border-amber-200 bg-amber-50 rounded p-4">
            <h3 className="font-medium text-amber-900 mb-2">
              Scored but not on formal roster
            </h3>
            <ul className="space-y-2">
              {roster.scored_but_not_on_roster.map((m) => (
                <li
                  key={m.shooter.id}
                  className="flex flex-wrap items-center justify-between gap-2 text-sm"
                >
                  <span>
                    {m.shooter.name}{" "}
                    <span className="text-gray-500">
                      ({m.score_count} score
                      {m.score_count === 1 ? "" : "s"})
                    </span>
                  </span>
                  {isAdmin() && (
                    <span className="space-x-3">
                      <button
                        type="button"
                        disabled={busyId === m.shooter.id}
                        onClick={() => handleAddScoredToRoster(m)}
                        className="text-indigo-700 hover:underline disabled:opacity-50"
                      >
                        Add to roster
                      </button>
                      {match?.league_id && (
                        <button
                          type="button"
                          disabled={busyId === m.shooter.id}
                          onClick={() => handlePromote(m)}
                          className="text-blue-700 hover:underline disabled:opacity-50"
                        >
                          Promote to league
                        </button>
                      )}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {isAdmin() && (
          <div className="border-t pt-4 space-y-4">
            <h3 className="font-medium">Add to this match</h3>

            <div>
              <label className="block text-sm text-gray-700 mb-1">
                Create new shooter on this roster
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Full name"
                className="w-full md:w-1/2 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {availableToAdd.length > 0 && (
              <div>
                <label className="block text-sm text-gray-700 mb-2">
                  Or pick from directory ({availableToAdd.length} available)
                </label>
                <div className="max-h-48 overflow-y-auto border rounded p-2 space-y-1">
                  {availableToAdd.map((s) => (
                    <label
                      key={s.id}
                      className="flex items-center gap-2 text-sm px-2 py-1 hover:bg-gray-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(s.id)}
                        onChange={() => toggleSelected(s.id)}
                      />
                      <span>{s.name}</span>
                      {s.nra_number && (
                        <span className="text-gray-400">NRA {s.nra_number}</span>
                      )}
                    </label>
                  ))}
                </div>
              </div>
            )}

            <button
              type="button"
              onClick={handleAddSelected}
              disabled={adding}
              className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 ${
                adding ? "opacity-70 cursor-not-allowed" : ""
              }`}
            >
              {adding ? "Adding..." : "Add to Roster"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchRoster;
