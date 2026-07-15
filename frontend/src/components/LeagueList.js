import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = BACKEND_URL?.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`;

/**
 * Leagues hold an evolving club/series roster.
 * Matches can link to a league and snapshot that roster for match day.
 * Shooters themselves always live in the global directory.
 */
const LeagueList = () => {
  const { isAdmin } = useAuth();
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState({ name: "", season: "", description: "" });
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [roster, setRoster] = useState(null);
  const [allShooters, setAllShooters] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);

  const showSuccess = (msg) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(""), 3500);
  };

  const loadLeagues = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/leagues`);
      setLeagues(res.data || []);
      setError(null);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to load leagues");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLeagues();
  }, [loadLeagues]);

  const loadRoster = async (leagueId) => {
    try {
      const [r, s] = await Promise.all([
        axios.get(`${API}/leagues/${leagueId}/roster`),
        axios.get(`${API}/shooters`),
      ]);
      setRoster(r.data);
      setAllShooters(s.data || []);
      setSelectedIds([]);
      setNewName("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load league roster");
    }
  };

  const toggleExpand = async (leagueId) => {
    if (expandedId === leagueId) {
      setExpandedId(null);
      setRoster(null);
      return;
    }
    setExpandedId(leagueId);
    await loadRoster(leagueId);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("League name is required");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await axios.post(`${API}/leagues`, {
        name: form.name.trim(),
        season: form.season.trim() || null,
        description: form.description.trim() || null,
      });
      setForm({ name: "", season: "", description: "" });
      showSuccess("League created");
      await loadLeagues();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create league");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteLeague = async (league) => {
    if (
      !window.confirm(
        `Delete league "${league.name}"?\n\n` +
          "Shooters, matches, and scores are kept. Linked matches are unlinked only."
      )
    ) {
      return;
    }
    try {
      await axios.delete(`${API}/leagues/${league.id}`);
      if (expandedId === league.id) {
        setExpandedId(null);
        setRoster(null);
      }
      showSuccess("League deleted");
      await loadLeagues();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete league");
    }
  };

  const rosterIdSet = new Set((roster?.members || []).map((m) => m.id));
  const available = allShooters.filter((s) => !rosterIdSet.has(s.id));

  const handleAddToRoster = async () => {
    if (!expandedId) return;
    if (selectedIds.length === 0 && !newName.trim()) {
      setError("Select shooters or enter a new name");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/leagues/${expandedId}/roster`, {
        shooter_ids: selectedIds,
        new_shooters: newName.trim() ? [{ name: newName.trim() }] : [],
      });
      setRoster(res.data);
      setSelectedIds([]);
      setNewName("");
      const shootersRes = await axios.get(`${API}/shooters`);
      setAllShooters(shootersRes.data || []);
      await loadLeagues();
      showSuccess("League roster updated");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update league roster");
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveFromRoster = async (shooter) => {
    if (!expandedId) return;
    if (
      !window.confirm(
        `Remove "${shooter.name}" from this league roster?\n\n` +
          "Their profile stays. Existing match rosters and scores are unchanged."
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      await axios.delete(
        `${API}/leagues/${expandedId}/roster/${shooter.id}`
      );
      await loadRoster(expandedId);
      await loadLeagues();
      showSuccess(`Removed ${shooter.name} from league`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to remove from league");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-4 text-center">Loading leagues...</div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-2">Leagues</h1>
      <p className="text-gray-600 mb-6 max-w-3xl">
        A <strong>league</strong> is a club or series with a roster that grows over
        the season. Each <strong>match</strong> keeps its own day-of roster
        (snapshot). Create a match linked to a league to seed that day&apos;s
        roster; pull new league members later or promote match guests up to the
        league.
      </p>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4" role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </div>
      )}
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4" role="status">
          {success}
        </div>
      )}

      {isAdmin() && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-semibold mb-4">Create League</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, name: e.target.value }))
                  }
                  placeholder="e.g. Capital City Pistol League"
                  className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Season (optional)
                </label>
                <input
                  type="text"
                  value={form.season}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, season: e.target.value }))
                  }
                  placeholder="e.g. 2026 Outdoor"
                  className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description (optional)
                </label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, description: e.target.value }))
                  }
                  className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={creating}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-70"
              >
                {creating ? "Creating..." : "Create League"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {leagues.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            No leagues yet. Create one to hold a season roster shared across matches.
          </div>
        ) : (
          leagues.map((league) => (
            <div key={league.id} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold">{league.name}</h3>
                  <p className="text-sm text-gray-500">
                    {league.season || "No season label"} ·{" "}
                    {(league.roster_shooter_ids || []).length} on roster
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => toggleExpand(league.id)}
                    className="bg-gray-100 text-gray-800 px-3 py-1.5 rounded hover:bg-gray-200 text-sm"
                  >
                    {expandedId === league.id ? "Hide roster" : "Manage roster"}
                  </button>
                  {isAdmin() && (
                    <button
                      type="button"
                      onClick={() => handleDeleteLeague(league)}
                      className="text-red-600 hover:text-red-800 text-sm px-2"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {expandedId === league.id && roster && (
                <div className="border-t px-4 py-4 bg-gray-50 space-y-4">
                  <p className="text-sm text-gray-600">
                    Linked matches: {roster.match_count}. Adding here does not
                    change past match rosters until you sync a match.
                  </p>

                  {(roster.members || []).length === 0 ? (
                    <p className="text-sm text-gray-500">League roster is empty.</p>
                  ) : (
                    <table className="min-w-full text-sm bg-white rounded border">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-3 py-2 text-left">Name</th>
                          <th className="px-3 py-2 text-left">NRA</th>
                          <th className="px-3 py-2 text-left">Rating</th>
                          <th className="px-3 py-2 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {roster.members.map((s) => (
                          <tr key={s.id}>
                            <td className="px-3 py-2">
                              <Link
                                to={`/shooters/${s.id}`}
                                className="text-blue-600 hover:underline"
                              >
                                {s.name}
                              </Link>
                            </td>
                            <td className="px-3 py-2 text-gray-600">
                              {s.nra_number || "—"}
                            </td>
                            <td className="px-3 py-2 text-gray-600">
                              {s.rating || "—"}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {isAdmin() && (
                                <button
                                  type="button"
                                  disabled={busy}
                                  onClick={() => handleRemoveFromRoster(s)}
                                  className="text-red-600 hover:underline disabled:opacity-50"
                                >
                                  Remove
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {isAdmin() && (
                    <div className="space-y-3 border-t pt-3">
                      <h4 className="font-medium text-sm">Add to league roster</h4>
                      <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="New shooter full name"
                        className="w-full md:w-1/2 px-3 py-2 border rounded"
                      />
                      {available.length > 0 && (
                        <div className="max-h-40 overflow-y-auto border rounded p-2 bg-white space-y-1">
                          {available.map((s) => (
                            <label
                              key={s.id}
                              className="flex items-center gap-2 text-sm px-1 py-0.5 hover:bg-gray-50 cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                checked={selectedIds.includes(s.id)}
                                onChange={() =>
                                  setSelectedIds((prev) =>
                                    prev.includes(s.id)
                                      ? prev.filter((x) => x !== s.id)
                                      : [...prev, s.id]
                                  )
                                }
                              />
                              {s.name}
                            </label>
                          ))}
                        </div>
                      )}
                      <button
                        type="button"
                        disabled={busy}
                        onClick={handleAddToRoster}
                        className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-70"
                      >
                        {busy ? "Saving..." : "Add to League"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LeagueList;
