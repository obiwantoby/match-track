import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MatchReport = () => {
  const { matchId } = useParams();
  const [match, setMatch] = useState(null);
  const [scores, setScores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMatchData = async () => {
      try {
        setLoading(true);
        const matchResponse = await axios.get(`${API}/matches/${matchId}`);
        setMatch(matchResponse.data);
        
        const scoresResponse = await axios.get(`${API}/scores/match/${matchId}`);
        setScores(scoresResponse.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching match data:', err);
        setError('Failed to load match data. Please try again later.');
        setLoading(false);
      }
    };

    fetchMatchData();
  }, [matchId]);

  if (loading) return <div className="text-center py-8">Loading match data...</div>;
  if (error) return <div className="text-center py-8 text-red-600">{error}</div>;
  if (!match) return <div className="text-center py-8">Match not found</div>;

  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-4">Match Report</h1>
      
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-2">{match.name}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <p><span className="font-medium">Date:</span> {new Date(match.date).toLocaleDateString()}</p>
            <p><span className="font-medium">Location:</span> {match.location}</p>
          </div>
          <div>
            <p><span className="font-medium">Type:</span> {match.type}</p>
            <p><span className="font-medium">Status:</span> {match.status}</p>
          </div>
        </div>
        
        {match.description && (
          <div className="mt-4">
            <h3 className="font-medium">Description:</h3>
            <p>{match.description}</p>
          </div>
        )}
        
        {match.status === 'upcoming' && (
          <div className="mt-4">
            <Link 
              to={`/scores/add/${matchId}`}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Add Score
            </Link>
          </div>
        )}
      </div>
      
      {scores.length > 0 ? (
        <div className="scorecard-container bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Scores</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-2 text-left">Shooter</th>
                  <th className="px-4 py-2 text-center">SF1</th>
                  <th className="px-4 py-2 text-center">SF2</th>
                  <th className="px-4 py-2 text-center subtotal">SFNMC</th>
                  <th className="px-4 py-2 text-center">TF1</th>
                  <th className="px-4 py-2 text-center">TF2</th>
                  <th className="px-4 py-2 text-center subtotal">TFNMC</th>
                  <th className="px-4 py-2 text-center">RF1</th>
                  <th className="px-4 py-2 text-center">RF2</th>
                  <th className="px-4 py-2 text-center subtotal">RFNMC</th>
                  <th className="px-4 py-2 text-center">Total</th>
                  <th className="px-4 py-2 text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scores.map((score) => (
                  <tr key={score._id} className="border-t">
                    <td className="px-4 py-2">{score.shooter_name}</td>
                    <td className="px-4 py-2 text-center">{score.SF1}</td>
                    <td className="px-4 py-2 text-center">{score.SF2}</td>
                    <td className="px-4 py-2 text-center subtotal">{score.SFNMC}</td>
                    <td className="px-4 py-2 text-center">{score.TF1}</td>
                    <td className="px-4 py-2 text-center">{score.TF2}</td>
                    <td className="px-4 py-2 text-center subtotal">{score.TFNMC}</td>
                    <td className="px-4 py-2 text-center">{score.RF1}</td>
                    <td className="px-4 py-2 text-center">{score.RF2}</td>
                    <td className="px-4 py-2 text-center subtotal">{score.RFNMC}</td>
                    <td className="px-4 py-2 text-center font-bold">{score.total}</td>
                    <td className="px-4 py-2 text-center">
                      <Link 
                        to={`/scores/edit/${score._id}`}
                        className="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600 mr-2"
                      >
                        Edit
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white shadow-md rounded-lg p-6 text-center">
          <p>No scores have been recorded for this match yet.</p>
          <Link 
            to={`/scores/add/${matchId}`}
            className="inline-block mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Add Score
          </Link>
        </div>
      )}
    </div>
  );
};

export default MatchReport;
