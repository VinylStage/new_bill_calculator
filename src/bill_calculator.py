
# -*- coding: utf-8 -*-

def solve_knapsack(items_df, max_limit):
    """
    Solves the 0/1 knapsack problem to find the best sum of amounts.
    Returns the best sum and the list of included item IDs.
    """
    dp = {0: []}  # Key: sum, Value: list of item IDs

    for _, row in items_df.iterrows():
        amount = int(row['Amount'])
        item_id = int(row['Item'])
        
        new_dp = {}
        for current_sum, included_items in dp.items():
            new_sum = current_sum + amount
            if new_sum <= max_limit:
                if new_sum not in dp or len(included_items) + 1 < len(dp.get(new_sum, [])):
                    new_dp[new_sum] = included_items + [item_id]
        
        dp.update(new_dp)

    if not dp:
        return 0, []

    best_sum = max(dp.keys())
    best_combination_items = dp[best_sum]

    return best_sum, best_combination_items
