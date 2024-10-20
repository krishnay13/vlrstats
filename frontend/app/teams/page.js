// frontend/app/teams/page.js

import Link from 'next/link';

export default async function TeamsPage() {
  try {
    // Use absolute URL for fetch
    const res = await fetch('http://localhost:3000/api/teams', { cache: 'no-store' });

    if (!res.ok) {
      throw new Error('Failed to fetch teams.');
    }

    const teams = await res.json();

    return (
      <div>
        <h1>Teams</h1>
        <table>
          <thead>
            <tr>
              <th>Team ID</th>
              <th>Team Name</th>
              <th>Region</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => (
              <tr key={team.team_id}>
                <td>{team.team_id}</td>
                <td>{team.team_name}</td>
                <td>{team.region}</td>
                <td>
                  <Link href={`/teams/${team.team_id}`} className="link">
                    View Players
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
