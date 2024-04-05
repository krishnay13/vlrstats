class Team:
    def __init__(self, team_name):
        self.team_name = team_name
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def __repr__(self):
        return f"Team(team_name={self.team_name}, players={self.players})"