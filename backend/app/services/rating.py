from math import floor

def calculate_rating(ratings: list[int], strategy: str = "floor_average") -> int:
    """Aproximación configurable: EA no publica una fórmula estable para todas las ediciones."""
    if not ratings: return 0
    average = sum(ratings) / len(ratings)
    if strategy == "round_half_up": return int(average + 0.5)
    if strategy == "ceiling": return int(-(-sum(ratings) // len(ratings)))
    return floor(average)

def minimum_rating_sum(size: int, minimum: int, strategy: str = "floor_average") -> int:
    if strategy == "round_half_up": return int((minimum - 0.5) * size + 0.999999)
    if strategy == "ceiling": return (minimum - 1) * size + 1
    return minimum * size
