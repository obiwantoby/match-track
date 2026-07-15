import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../App";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = BACKEND_URL?.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`;

const EMPTY_SHOOTER = {
  name: "",
  nra_number: "",
  cmp_number: "",
  rating: "",
  competitor_number: "",
  division: "Civilian",
  special_categories: [],
};

const SAMPLE_CSV = `name,nra_number,cmp_number,rating,competitor_number,division,special_categories
Jorgenson, Travis,SEED00001,CMP001,HM,101,Civilian,Veteran
Emmert-Traciak, Lisa,SEED00002,CMP002,HM,102,Service,Women
Dean, Roy,SEED00003,CMP003,MA,103,Civilian,Grand Senior
Toler, Alan,SEED00004,CMP004,MA,104,Civilian,Senior
`;

const RATING_OPTIONS = (
  <>
    <option value="">Select Rating</option>
    <option value="HM">HM - High Master</option>
    <option value="MA">MA - Master</option>
    <option value="EX">EX - Expert</option>
    <option value="SS">SS - Sharpshooter</option>
    <option value="MK">MK - Marksman</option>
    <option value="UNC">UNC - Unclassified</option>
  </>
);

const SPECIAL_OPTIONS = ["Grand Senior", "Senior", "Women", "Veteran"];

function toFormShooter(s) {
  return {
    name: s.name || "",
    nra_number: s.nra_number || "",
    cmp_number: s.cmp_number || "",
    rating: s.rating || "",
    competitor_number:
      s.competitor_number === 0 || s.competitor_number
        ? String(s.competitor_number)
        : "",
    division: s.division || "Civilian",
    special_categories: Array.isArray(s.special_categories)
      ? [...s.special_categories]
      : [],
  };
}

function toPayload(form) {
  const cats = form.special_categories || [];
  return {
    name: form.name.trim(),
    nra_number: form.nra_number.trim() || null,
    cmp_number: form.cmp_number.trim() || null,
    rating: form.rating || null,
    competitor_number: form.competitor_number
      ? parseInt(form.competitor_number, 10)
      : null,
    division: form.division || "Civilian",
    special_categories: cats,
  };
}

function toggleSpecial(list, value) {
  const has = list.includes(value);
  if (has) return list.filter((x) => x !== value);
  // Women may combine with one other; non-Women are exclusive of each other
  if (value === "Women") return [...list, "Women"];
  const withoutExclusive = list.filter((x) => x === "Women");
  return [...withoutExclusive, value];
}

const ShootersList = () => {
  const [shooters, setShooters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [importResult, setImportResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newShooter, setNewShooter] = useState(EMPTY_SHOOTER);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_SHOOTER);
  const [savingEdit, setSavingEdit] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const fileInputRef = useRef(null);
  const { isAdmin } = useAuth();

  const showSuccess = (message) => {
    setSuccess(message);
    setTimeout(() => setSuccess(""), 4000);
  };

  const fetchShooters = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/shooters`);
      setShooters(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching shooters:", err);
      setError(
        err.response?.data?.detail || "Failed to load shooters. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShooters();
  }, [fetchShooters]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewShooter((prev) => ({ ...prev, [name]: value }));
  };

  const handleAddShooter = async (e) => {
    e.preventDefault();

    if (!newShooter.name.trim()) {
      setError("Shooter name is required");
      return;
    }

    setCreating(true);
    setError(null);
    setImportResult(null);

    try {
      const response = await axios.post(`${API}/shooters`, toPayload(newShooter));
      setShooters((prev) =>
        [...prev, response.data].sort((a, b) =>
          (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" })
        )
      );
      setNewShooter(EMPTY_SHOOTER);
      showSuccess(`Shooter ${response.data.name} created`);
    } catch (err) {
      console.error("Error adding shooter:", err);
      setError(
        err.response?.data?.detail || "Failed to add shooter. Please try again."
      );
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (shooter) => {
    setEditingId(shooter.id);
    setEditForm(toFormShooter(shooter));
    setError(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(EMPTY_SHOOTER);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingId) return;
    if (!editForm.name.trim()) {
      setError("Shooter name is required");
      return;
    }

    setSavingEdit(true);
    setError(null);
    try {
      const response = await axios.put(
        `${API}/shooters/${editingId}`,
        toPayload(editForm)
      );
      setShooters((prev) =>
        prev
          .map((s) => (s.id === editingId ? response.data : s))
          .sort((a, b) =>
            (a.name || "").localeCompare(b.name || "", undefined, {
              sensitivity: "base",
            })
          )
      );
      showSuccess(`Updated ${response.data.name}`);
      cancelEdit();
    } catch (err) {
      console.error("Error updating shooter:", err);
      setError(
        err.response?.data?.detail || "Failed to update shooter. Please try again."
      );
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (shooter) => {
    if (deletingId) return;

    const ok = window.confirm(
      `Delete shooter "${shooter.name}"?\n\n` +
        "If they have scores, you will be asked to confirm a forced delete."
    );
    if (!ok) return;

    setDeletingId(shooter.id);
    setError(null);

    try {
      await axios.delete(`${API}/shooters/${shooter.id}`);
      setShooters((prev) => prev.filter((s) => s.id !== shooter.id));
      if (editingId === shooter.id) cancelEdit();
      showSuccess(`Deleted ${shooter.name}`);
    } catch (err) {
      const detail = err.response?.data?.detail || "";
      // Soft-fail path: shooter has scores — ask for force
      if (err.response?.status === 400 && String(detail).toLowerCase().includes("score")) {
        const forceOk = window.confirm(
          `${detail}\n\nForce delete "${shooter.name}" AND all of their scores across every match? This cannot be undone.`
        );
        if (!forceOk) {
          setDeletingId(null);
          return;
        }
        try {
          await axios.delete(`${API}/shooters/${shooter.id}?force=true`);
          setShooters((prev) => prev.filter((s) => s.id !== shooter.id));
          if (editingId === shooter.id) cancelEdit();
          showSuccess(`Force-deleted ${shooter.name} and their scores`);
        } catch (forceErr) {
          console.error("Force delete failed:", forceErr);
          setError(
            forceErr.response?.data?.detail ||
              "Failed to force-delete shooter. Please try again."
          );
        }
      } else {
        console.error("Error deleting shooter:", err);
        setError(detail || "Failed to delete shooter. Please try again.");
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a .csv file");
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError(null);
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API}/shooters/bulk-csv`, formData);
      setImportResult(response.data);
      const { created, skipped, errors } = response.data;
      showSuccess(
        `CSV import finished: ${created} created, ${skipped} skipped, ${errors} errors`
      );
      if (created > 0) {
        await fetchShooters();
      }
    } catch (err) {
      console.error("Error uploading shooter CSV:", err);
      setError(
        err.response?.data?.detail ||
          "Failed to import shooters from CSV. Please check the file format."
      );
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const downloadSampleCsv = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "shooters_template.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="container mx-auto p-4 text-center">Loading shooters...</div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-2">Shooters</h1>
      <p className="text-gray-600 mb-6">
        Global competitor directory. Profiles are managed by admins (shooters do not
        log in). For a specific match day roster, open that match → Roster.
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
        <>
          <div className="mb-6 bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-1">Add New Shooter</h2>
            <p className="text-sm text-gray-500 mb-4">
              Special categories (Grand Senior, Senior, Women, Veteran) drive High-* awards
              on Results Bulletins. Women may combine with one other category.
            </p>
            <form onSubmit={handleAddShooter} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Shooter Name
                  </label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    value={newShooter.name}
                    onChange={handleInputChange}
                    placeholder="Enter shooter name"
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label
                    htmlFor="nra_number"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    NRA Number (Optional)
                  </label>
                  <input
                    id="nra_number"
                    name="nra_number"
                    type="text"
                    value={newShooter.nra_number}
                    onChange={handleInputChange}
                    placeholder="Enter NRA number"
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="cmp_number"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    CMP Number (Optional)
                  </label>
                  <input
                    id="cmp_number"
                    name="cmp_number"
                    type="text"
                    value={newShooter.cmp_number}
                    onChange={handleInputChange}
                    placeholder="Enter CMP number"
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="rating"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Class (Optional)
                  </label>
                  <select
                    id="rating"
                    name="rating"
                    value={newShooter.rating}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {RATING_OPTIONS}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Competitor #
                  </label>
                  <input
                    name="competitor_number"
                    type="number"
                    min="1"
                    value={newShooter.competitor_number}
                    onChange={handleInputChange}
                    placeholder="e.g. 132"
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Division
                  </label>
                  <select
                    name="division"
                    value={newShooter.division}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="Civilian">Civilian</option>
                    <option value="Police">Police</option>
                    <option value="Service">Service</option>
                  </select>
                </div>
              </div>
              <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
                <label className="block text-sm font-semibold text-purple-900 mb-2">
                  Special categories (for High Senior / Woman / GS / Veteran awards)
                </label>
                <div className="flex flex-wrap gap-4 text-sm">
                  {SPECIAL_OPTIONS.map((opt) => (
                    <label
                      key={opt}
                      className="inline-flex items-center gap-2 bg-white border border-purple-100 px-3 py-2 rounded shadow-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={(newShooter.special_categories || []).includes(opt)}
                        onChange={() =>
                          setNewShooter((prev) => ({
                            ...prev,
                            special_categories: toggleSpecial(
                              prev.special_categories || [],
                              opt
                            ),
                          }))
                        }
                      />
                      <span className="font-medium text-gray-800">{opt}</span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-purple-800 mt-2">
                  Pick at most one of Grand Senior / Senior / Veteran. Women may also be
                  selected with one of those.
                </p>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={creating}
                  className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 ${
                    creating ? "opacity-70 cursor-not-allowed" : ""
                  }`}
                >
                  {creating ? "Adding..." : "Add Shooter"}
                </button>
              </div>
            </form>
          </div>

          <div className="mb-6 bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-2">Bulk Import from CSV</h2>
            <p className="text-sm text-gray-600 mb-4">
              Required: <code className="bg-gray-100 px-1 rounded">name</code>.
              Optional: nra_number, cmp_number, rating, competitor_number, division
              (Civilian/Police/Service), special_categories
              (e.g. <code className="bg-gray-100 px-1 rounded">Grand Senior|Women</code>
              or Senior, Veteran).
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={handleCsvUpload}
                className="hidden"
                id="shooter-csv-upload"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className={`bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 ${
                  uploading ? "opacity-70 cursor-not-allowed" : ""
                }`}
              >
                {uploading ? "Uploading..." : "Upload CSV"}
              </button>
              <button
                type="button"
                onClick={downloadSampleCsv}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
              >
                Download Template
              </button>
            </div>

            {importResult && (
              <div className="mt-4 border rounded overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700">
                  Import results — {importResult.created} created,{" "}
                  {importResult.skipped} skipped, {importResult.errors} errors
                </div>
                <div className="max-h-64 overflow-y-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-white sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left">Row</th>
                        <th className="px-4 py-2 text-left">Name</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Detail</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {importResult.results.map((row) => (
                        <tr key={`${row.row}-${row.name || ""}`}>
                          <td className="px-4 py-2">{row.row}</td>
                          <td className="px-4 py-2">{row.name || "—"}</td>
                          <td className="px-4 py-2">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                row.status === "created"
                                  ? "bg-green-100 text-green-800"
                                  : row.status === "skipped"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {row.status}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-600">{row.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Edit panel */}
      {isAdmin() && editingId && (
        <div className="mb-6 bg-amber-50 border border-amber-200 p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Edit Shooter</h2>
          <form onSubmit={handleSaveEdit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, name: e.target.value }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  NRA Number
                </label>
                <input
                  type="text"
                  value={editForm.nra_number}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, nra_number: e.target.value }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CMP Number
                </label>
                <input
                  type="text"
                  value={editForm.cmp_number}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, cmp_number: e.target.value }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Class
                </label>
                <select
                  value={editForm.rating}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, rating: e.target.value }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {RATING_OPTIONS}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Competitor #
                </label>
                <input
                  type="number"
                  min="1"
                  value={editForm.competitor_number}
                  onChange={(e) =>
                    setEditForm((p) => ({
                      ...p,
                      competitor_number: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Division
                </label>
                <select
                  value={editForm.division}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, division: e.target.value }))
                  }
                  className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Civilian">Civilian</option>
                  <option value="Police">Police</option>
                  <option value="Service">Service</option>
                </select>
              </div>
            </div>
            <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
              <label className="block text-sm font-semibold text-purple-900 mb-2">
                Special categories
              </label>
              <div className="flex flex-wrap gap-4 text-sm">
                {SPECIAL_OPTIONS.map((opt) => (
                  <label
                    key={opt}
                    className="inline-flex items-center gap-2 bg-white border border-purple-100 px-3 py-2 rounded shadow-sm cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={(editForm.special_categories || []).includes(opt)}
                      onChange={() =>
                        setEditForm((p) => ({
                          ...p,
                          special_categories: toggleSpecial(
                            p.special_categories || [],
                            opt
                          ),
                        }))
                      }
                    />
                    <span className="font-medium text-gray-800">{opt}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={cancelEdit}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingEdit}
                className={`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 ${
                  savingEdit ? "opacity-70 cursor-not-allowed" : ""
                }`}
              >
                {savingEdit ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                #
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Class
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Division
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Special categories
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                NRA
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shooters.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-6 py-4 text-center text-gray-500">
                  No shooters found
                </td>
              </tr>
            ) : (
              shooters.map((shooter) => (
                <tr
                  key={shooter.id}
                  className={editingId === shooter.id ? "bg-amber-50" : ""}
                >
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    {shooter.competitor_number ?? "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {shooter.name}
                    </div>
                    {shooter.cmp_number && (
                      <div className="text-xs text-gray-400">CMP {shooter.cmp_number}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    {shooter.rating || "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    {shooter.division || "Civilian"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(shooter.special_categories || []).length === 0 ? (
                        <span className="text-xs text-gray-400">—</span>
                      ) : (
                        (shooter.special_categories || []).map((c) => (
                          <span
                            key={c}
                            className="inline-block text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded"
                          >
                            {c}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {shooter.nra_number || "—"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium space-x-3">
                    <Link
                      to={`/shooters/${shooter.id}`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </Link>
                    {isAdmin() && (
                      <>
                        <button
                          type="button"
                          onClick={() => startEdit(shooter)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(shooter)}
                          disabled={deletingId === shooter.id}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                        >
                          {deletingId === shooter.id ? "Deleting..." : "Delete"}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ShootersList;
