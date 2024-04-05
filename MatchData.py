class Match:
    def __init__(self, match_id):
        self.match_id = match_id
        self.maps = []

    def add_map(self, map_stats):
        self.maps.append(map_stats)

    def __repr__(self):
        return f"Match(match_id={self.match_id}, maps={self.maps})"
