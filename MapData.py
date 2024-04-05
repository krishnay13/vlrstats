class Map:
    def __init__(self, map_name):
        self.map_name = map_name
        self.teams = []
        self.score = []

    def add_team(self, team):
        self.teams.append(team)

    def __repr__(self):
        return f"MapStats(map_name={self.map_name}, teams={self.teams})"
