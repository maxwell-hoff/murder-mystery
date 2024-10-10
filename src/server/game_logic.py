import random

def assign_roles(player_names):
    """
    Assign roles to players. One impostor, rest are crew.
    Args:
        player_names (list): List of player names.
    Returns:
        dict: A dictionary mapping player names to their roles.
    """
    roles = ['impostor'] + ['crew'] * (len(player_names) - 1)
    random.shuffle(roles)
    return dict(zip(player_names, roles))