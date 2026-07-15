import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = BACKEND_URL?.endsWith("/api") ? BACKEND_URL : `${BACKEND_URL}/api`;

/**
 * NRA Tournament Results Bulletin — web view + Excel + print/PDF.
 * Layout mirrors docs/sample-reports and docs/NRA_BULLETIN_SPEC.md.
 */
const MatchBulletin = ({ matchId }) => {
  const [events, setEvents] = useState([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [bulletin, setBulletin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const authHeaders = () => {
    const token = localStorage.getItem("token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const eventKey = (e) =>
    `${e.event_scope}|${e.caliber || ""}|${e.match_type_instance || ""}|${e.match_no}`;

  const loadEvents = useCallback(async () => {
    try {
      setError(null);
      const res = await axios.get(
        `${API}/match-report/${matchId}/bulletin/events`,
        { headers: authHeaders() }
      );
      const list = res.data.events || [];
      setEvents(list);
      if (list.length > 0) {
        setSelectedKey(eventKey(list[0]));
      }
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || "Failed to load bulletin events"
      );
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const selectedEvent = events.find((e) => eventKey(e) === selectedKey);

  const loadBulletin = useCallback(async () => {
    if (!selectedEvent) {
      setBulletin(null);
      return;
    }
    try {
      setError(null);
      const params = {
        event_scope: selectedEvent.event_scope,
        match_no: selectedEvent.match_no,
      };
      if (selectedEvent.caliber) params.caliber = selectedEvent.caliber;
      if (selectedEvent.match_type_instance) {
        params.match_type_instance = selectedEvent.match_type_instance;
      }
      const res = await axios.get(
        `${API}/match-report/${matchId}/bulletin`,
        { headers: authHeaders(), params }
      );
      setBulletin(res.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to load bulletin");
      setBulletin(null);
    }
  }, [matchId, selectedEvent]);

  useEffect(() => {
    loadBulletin();
  }, [loadBulletin]);

  const downloadExcel = async () => {
    if (!selectedEvent) return;
    try {
      const params = new URLSearchParams({
        event_scope: selectedEvent.event_scope,
        match_no: String(selectedEvent.match_no),
      });
      if (selectedEvent.caliber) params.set("caliber", selectedEvent.caliber);
      if (selectedEvent.match_type_instance) {
        params.set("match_type_instance", selectedEvent.match_type_instance);
      }
      const res = await axios.get(
        `${API}/match-report/${matchId}/bulletin/excel?${params}`,
        { headers: authHeaders(), responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `bulletin_${(selectedEvent.event_title || "event").replace(/\s+/g, "_")}.xlsx`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Excel export failed");
    }
  };

  const printPdf = () => {
    window.print();
  };

  if (loading) {
    return <div className="text-center p-6 text-gray-500">Loading bulletin…</div>;
  }

  return (
    <div className="bulletin-root">
      <div className="no-print mb-4 flex flex-col md:flex-row md:items-end gap-3 justify-between">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bulletin event
          </label>
          <select
            className="w-full md:w-2/3 border rounded px-3 py-2"
            value={selectedKey}
            onChange={(e) => setSelectedKey(e.target.value)}
          >
            {events.map((e) => (
              <option key={eventKey(e)} value={eventKey(e)}>
                #{e.match_no} — {e.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Format matches NRA Tournament Results Bulletin samples (place awards,
            special categories, class × civilian / police-service).
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={downloadExcel}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm"
          >
            Export Excel
          </button>
          <button
            type="button"
            onClick={printPdf}
            className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded text-sm"
          >
            Print / PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="no-print bg-red-50 text-red-700 p-3 rounded mb-4">{error}</div>
      )}

      {!bulletin && !error && (
        <div className="text-gray-500 p-4">Select an event to view the bulletin.</div>
      )}

      {bulletin && (
        <div className="bulletin-sheet bg-white shadow rounded p-6 md:p-10 font-serif text-sm text-black">
          <div className="bulletin-header text-center mb-6">
            <div className="bulletin-title text-lg font-bold tracking-wide uppercase">
              {bulletin.header.bulletin_title}
            </div>
            <div className="font-semibold mt-1">{bulletin.header.tournament_title}</div>
            <div className="mt-1">{bulletin.header.location}</div>
            <div className="font-bold mt-4 text-base">
              MATCH NO. {bulletin.header.match_no} -- {bulletin.header.event_title}
            </div>
          </div>

          <section className="bulletin-section mb-6">
            <h3 className="section-title font-bold border-b-2 border-black pb-1 mb-2">
              OPEN -- PLACE AWARDS ({bulletin.competitor_count} COMPETITORS)
            </h3>
            <BulletinTable
              rows={bulletin.open_place_awards}
              showPlace
              empty="No scores for this event."
              highlightAwards
            />
          </section>

          <section className="bulletin-section mb-6">
            <h3 className="section-title font-bold border-b-2 border-black pb-1 mb-2">
              SPECIAL CATEGORY AWARDS
            </h3>
            {bulletin.special_category_awards?.length ? (
              <table className="w-full bulletin-table">
                <tbody>
                  {bulletin.special_category_awards.map((r, i) => (
                    <tr key={i} className="award-row special-award">
                      <td className="w-16 pr-2 text-right tabular-nums">
                        {r.competitor_number ?? ""}
                      </td>
                      <td className="pr-2">{r.name_display}</td>
                      <td className="pr-2 tabular-nums whitespace-nowrap font-medium">
                        {r.score_display}
                      </td>
                      <td className="text-right font-medium">{r.award_label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-500 italic">
                No special-category winners (set division / special categories on
                shooters).
              </p>
            )}
          </section>

          {bulletin.class_sections?.map((sec) => (
            <section key={sec.title} className="bulletin-section mb-6">
              <h3 className="section-title font-bold border-b-2 border-black pb-1 mb-2">
                {sec.title} ({sec.competitor_count} COMPETITORS)
              </h3>
              <BulletinTable rows={sec.rows} showPlace highlightAwards />
            </section>
          ))}

          <div className="bulletin-footer text-center text-xs text-gray-500 mt-8 pt-4 border-t border-gray-200">
            <span className="no-print">
              Tip: Print / PDF → “Save as PDF”. Margins set for clean handouts.{" "}
            </span>
            <span>
              {bulletin.header.location}
              {bulletin.header.event_title
                ? ` · ${bulletin.header.event_title}`
                : ""}
            </span>
          </div>
        </div>
      )}

      <style>{`
        .bulletin-table { border-collapse: collapse; width: 100%; }
        .bulletin-table td { padding: 3px 6px; vertical-align: top; }
        .bulletin-table tr.award-row td { background: #fff8e1; }
        .bulletin-table tr.special-award td { background: #e8f5e9; }
        .tabular-nums { font-variant-numeric: tabular-nums; }

        @media print {
          @page {
            size: letter portrait;
            margin: 0.55in 0.6in 0.55in 0.6in;
          }
          html, body {
            background: white !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          body * { visibility: hidden; }
          .bulletin-root, .bulletin-root * { visibility: visible; }
          .bulletin-root {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            margin: 0;
            padding: 0;
          }
          .no-print { display: none !important; }
          .bulletin-sheet {
            box-shadow: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            font-size: 10.5pt;
            color: #000 !important;
          }
          .bulletin-title { font-size: 14pt; letter-spacing: 0.04em; }
          .section-title {
            font-size: 11pt;
            page-break-after: avoid;
            break-after: avoid;
          }
          .bulletin-section {
            page-break-inside: avoid;
            break-inside: avoid;
          }
          .bulletin-table tr { page-break-inside: avoid; }
          .bulletin-table tr.award-row td,
          .bulletin-table tr.special-award td {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .bulletin-footer {
            font-size: 8pt;
            color: #444 !important;
            margin-top: 1.2rem;
          }
        }
      `}</style>
    </div>
  );
};

function BulletinTable({ rows, showPlace, empty, highlightAwards }) {
  if (!rows || rows.length === 0) {
    return <p className="text-gray-500 italic">{empty || "None."}</p>;
  }
  return (
    <table className="w-full bulletin-table">
      <tbody>
        {rows.map((r, i) => {
          const award = r.award_label || "";
          const isAward =
            highlightAwards &&
            award &&
            (/Winner|First|Second|Third|Fourth|High /.test(award));
          return (
            <tr key={i} className={isAward ? "award-row" : undefined}>
              {showPlace && (
                <td className="w-8 pr-2 text-right tabular-nums">{r.place ?? ""}</td>
              )}
              <td className="w-16 pr-2 text-right tabular-nums">
                {r.competitor_number ?? ""}
              </td>
              <td className="pr-2">{r.name_display}</td>
              <td className="pr-2 tabular-nums whitespace-nowrap font-medium">
                {r.score_display}
              </td>
              <td className="text-right text-gray-800">{award}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default MatchBulletin;
