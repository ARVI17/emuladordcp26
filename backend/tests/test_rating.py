from app.services.rating import calculate_rating, minimum_rating_sum

def test_rating_strategies():
    ratings = [80] * 10 + [89]
    assert calculate_rating(ratings, "floor_average") == 80
    assert calculate_rating(ratings, "round_half_up") == 81
    assert calculate_rating(ratings, "ceiling") == 81

def test_minimum_sums_are_strategy_specific():
    assert minimum_rating_sum(11, 82, "floor_average") == 902
    assert minimum_rating_sum(11, 82, "ceiling") == 892
