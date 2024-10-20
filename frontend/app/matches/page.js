// frontend/app/matches/page.js

import Link from 'next/link';

export default async function MatchesPage() {
  try {
    // Use absolute URL for fetch
    const res = await fetch('http://localhost:3000/api/matches', { cache: 'no-store' });

    if (!res.ok) {
      throw new Error('Failed to fetch matches.');
    }

    const matches = await res.json();

    return (
      <div>
        <h1>Matches</h1>
        <table>
          <thead>
            <tr>
              <th>Match ID</th>
              <th>Team 1</th>
              <th>Team 2</th>
              <th>Score</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((match) => (
              <tr key={match.match_id}>
                <td>{match.match_id}</td>
                <td>{match.team1_name}</td>
                <td>{match.team2_name}</td>
                <td>
                  {match.team1_score} - {match.team2_score}
                </td>
                <td>
                  <Link href={`/matches/${match.match_id}`} className="link">
                    View Details
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  } catch (error) {
    console.error(error);
    return <div>Error: {error.message}</div>;
  }
}
