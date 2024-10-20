// frontend/app/players/page.js

import Link from 'next/link';

export default async function PlayersPage() {
  try {
    // Use absolute URL for fetch
    const res = await fetch('http://localhost:3000/api/players', { cache: 'no-store' });

    if (!res.ok) {
      throw new Error('Failed to fetch players.');
    }

    const players = await res.json();

    return (
      <div>
        <h1>Players</h1>
        <table>
          <thead>
            <tr>
              <th>Player ID</th>
              <th>Player Name</th>
              <th>Team</th>
              <th>Role</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player) => (
              <tr key={player.player_id}>
                <td>{player.player_id}</td>
                <td>{player.player_name}</td>
                <td>{player.team_name}</td>
                <td>{player.role}</td>
                <td>
                  <Link href={`/players/${player.player_id}`} className="link">
                    View Stats
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
