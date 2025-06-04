// frontend/app/teams/[team_id]/page.js

import Link from 'next/link';

export default async function TeamDetailsPage({ params }) {
  const { team_id } = params;

  try {
    // Use absolute URL for fetch
    const res = await fetch(`http://localhost:3000/api/teams/${team_id}`, { cache: 'no-store' });

    if (!res.ok) {
      if (res.status === 404) {
        return (
          <div>
            <h1>Team not found.</h1>
            <Link href="/teams" className="link">
              Back to Teams
            </Link>
          </div>
        );
      }
      throw new Error('Failed to fetch team details.');
    }

    const data = await res.json();
    const { team, players } = data;

    return (
      <div>
        <h1>{team.team_name}</h1>

        <h2>Players</h2>
        <table>
          <thead>
            <tr>
              <th>Player ID</th>
              <th>Player Name</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player) => (
              <tr key={player.player_id}>
                <td>{player.player_id}</td>
                <td>{player.player_name}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <Link href="/teams" className="link">
          Back to Teams
        </Link>
      </div>
    );
  } catch (error) {
    console.error(error);
    return <div>Error: {error.message}</div>;
  }
}
