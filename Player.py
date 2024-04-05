class Player:
    def __init__(self, name, team, rating, acs, kills, deaths, assists, kd_diff, kast, adr, hs_percentage, first_kills, first_deaths, first_diff):
        self.name = name
        self.team = team
        self.rating = rating
        self.acs = acs
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
        self.kd_diff = kd_diff
        self.kast = kast
        self.adr = adr
        self.hs_percentage = hs_percentage
        self.first_kills = first_kills
        self.first_deaths = first_deaths
        self.first_diff = first_diff

    def __repr__(self):
        return f"Player(name={self.name}, team={self.team}, rating={self.rating}, acs={self.acs}, kills={self.kills}, deaths={self.deaths}, assists={self.assists}, kd_diff={self.kd_diff}, kast={self.kast}, adr={self.adr}, hs_percentage={self.hs_percentage}, first_kills={self.first_kills}, first_deaths={self.first_deaths}, first_diff={self.first_diff})"