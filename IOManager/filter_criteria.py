from collections import namedtuple

# The three choices from Filter Records so it means any of them can be none to skip that filter
FilterCriteria = namedtuple("FilterCriteria", ["outcome", "min_score", "max_score"])
