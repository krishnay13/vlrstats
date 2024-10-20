// frontend/app/matches/[match_id]/page.js

import Link from 'next/link';

export default async function MatchDetailsPage({ params }) {
  const { match_id } = params;

  try {
    // Use absolute URL for fetch
    const res = await fetch(`http://localhost:3000/api/matches/${match_id}`, { cache: 'no-store' });

    if (!res.ok) {
      if (res.status === 404) {
        return (
          <div>
            <h1>Match not found.</h1>
            <Link href="/matches" className="link">
              Back to Matches
            </Link>
          </div>
        );
      }
      throw new Error('Failed to fetch match details.');
    }

    const data = await res.json();
    const { match, maps, playerStats } = data;

    return (
      <div>
        <h1>
          {match.team1_name} vs {match.team2_name}
        </h1>
        <p>
          Score: {match.team1_score} - {match.team2_score}
        </p>

        <h2>Maps</h2>
        {maps.map((map) => (
          <div key={map.map_id}>
            <h3>
              {map.map_name}: {map.team1_score} - {map.team2_score}
            </h3>

            <h4>Player Stats</h4>
            <table>
              <thead>
                <tr>
                  <th>Player Name</th>
                  <th>Kills</th>
                  <th>Deaths</th>
                  <th>Assists</th>
                  <th>ACS</th>
                  <th>Rating</th>
                </tr>
              </thead>
              <tbody>
                {map.playerStats.map((stat) => (
                  <tr key={stat.stat_id}>
                    <td>{stat.player_name}</td>
                    <td>{stat.kills}</td>
                    <td>{stat.deaths}</td>
                    <td>{stat.assists}</td>
                    <td>{stat.acs}</td>
                    <td>{stat.rating}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        <h2>Player Stats (Match Totals)</h2>
        <table>
          <thead>
            <tr>
              <th>Player Name</th>
              <th>Kills</th>
              <th>Deaths</th>
              <th>Assists</th>
              <th>ACS</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            {playerStats.map((stat) => (
              <tr key={stat.stat_id}>
                <td>{stat.player_name}</td>
                <td>{stat.kills}</td>
                <td>{stat.deaths}</td>
                <td>{stat.assists}</td>
                <td>{stat.acs}</td>
                <td>{stat.rating}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <Link href="/matches" className="link">
          Back to Matches
        </Link>
      </div>
    );
  } catch (error) {
    console.error(error);
    return <div>Error: {error.message}</div>;
  }
}
