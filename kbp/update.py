import time
from core.views import (
    load_scores,
    load_picks,
    compute_kbp_scores,
    compute_margins,
    update_scores,
    create_update_list,

)

if __name__ == "__main__":
    scores = load_scores()
    picks = load_picks()
    
    while True:
        # LOGIC HERE
        game_list = create_update_list(scores)
        print(game_list)

        scores = update_scores(scores)
        scores.to_csv('kbp/data/scores_cache.csv', index=False)
        margins = compute_margins(scores)
        margins.to_csv('kbp/data/margins_cache.csv', index=False)
        kbp_scores = compute_kbp_scores(picks, margins)

        kbp_scores.to_csv('kbp/data/kbp.csv', index=False)

        # WAIT 1 Minute then update
        time.sleep(60)