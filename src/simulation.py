import random

class Player:
    def __init__(self, name, role='crew'):
        self.name = name
        self.role = role  # 'impostor' or 'crew'
        self.status = 'alive'

def generate_initial_room_assignment(players, num_rooms):
    while True:
        room_assignment = {}
        for player in players:
            room_number = random.randint(0, num_rooms - 1)
            room_assignment[player.name] = room_number
        if not impostor_has_kill_opportunity(room_assignment, players):
            return room_assignment

def impostor_has_kill_opportunity(room_assignment, players):
    # Build rooms mapping from room numbers to list of players
    rooms = {}
    for player_name, room_number in room_assignment.items():
        if room_number not in rooms:
            rooms[room_number] = []
        player = next(p for p in players if p.name == player_name)
        if player.status == 'alive':
            rooms[room_number].append(player)
    # Find the impostor
    impostor = next(p for p in players if p.role == 'impostor' and p.status == 'alive')
    impostor_room_number = room_assignment[impostor.name]
    # Find rooms with exactly one crew member
    for room_number, room_players in rooms.items():
        if room_number == impostor_room_number:
            continue  # Skip the impostor's room
        if len(room_players) == 1:
            player_in_room = room_players[0]
            if player_in_room.role == 'crew' and player_in_room.status == 'alive':
                return True  # Kill opportunity exists
    return False

def simulate_game_with_constraints(players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio):
    kill_cooldown_time = 30  # in seconds
    last_kill_time = -kill_cooldown_time  # So the impostor can kill at time 0
    kill_opportunities = 0

    # Generate initial assignment where impostor cannot kill immediately
    room_assignment = generate_initial_room_assignment(players, num_rooms)
    # Record the last reassignment interval for each player (initial assignment at interval 0)
    last_reassignment_interval = {player.name: 0 for player in players}

    # Record assignments and kill opportunities per interval
    assignments_per_interval = []
    kill_opportunity_per_interval = []

    # Number of intervals
    num_intervals = simulation_time // assignment_interval

    # Simulate interval by interval
    current_time = 0
    for interval in range(num_intervals):
        # Reassign one eligible player
        eligible_players = [player for player in players if player.status == 'alive' and (interval - last_reassignment_interval[player.name]) >= X]
        if eligible_players:
            player_to_reassign = random.choice(eligible_players)
            current_room = room_assignment[player_to_reassign.name]
            possible_rooms = list(range(num_rooms))
            possible_rooms.remove(current_room)
            if possible_rooms:
                new_room = random.choice(possible_rooms)
                room_assignment[player_to_reassign.name] = new_room
                last_reassignment_interval[player_to_reassign.name] = interval

        # Record the room assignment for this interval
        assignments_per_interval.append(room_assignment.copy())

        # Check if impostor has a kill opportunity during this interval
        has_kill_opportunity = False
        for second in range(assignment_interval):
            current_time += 1
            if current_time - last_kill_time >= kill_cooldown_time and not has_kill_opportunity:
                if impostor_has_kill_opportunity(room_assignment, players):
                    kill_opportunities += 1
                    last_kill_time = current_time
                    has_kill_opportunity = True
            # Termination condition based on difficulty ratio
            if kill_opportunities >= difficulty_ratio * (len(players) - 2):  # Subtract impostor and one crew member
                break
        kill_opportunity_per_interval.append(has_kill_opportunity)
        if kill_opportunities >= difficulty_ratio * (len(players) - 2):
            break
    return assignments_per_interval, kill_opportunity_per_interval, kill_opportunities

def run_simulation(num_players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio):
    # Create players
    players = [Player(name=f"Player_{i+1}") for i in range(num_players)]
    # Assign roles
    players[0].role = 'impostor'  # First player is the impostor

    # Simulate the game
    assignments_per_interval, kill_opportunity_per_interval, total_kill_opportunities = simulate_game_with_constraints(
        players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio
    )

    # Calculate Difficulty metric
    num_crew = num_players - 1  # Subtract impostor
    difficulty = total_kill_opportunities / (num_crew - 1)  # Number of crew minus one

    result = {
        'assignments_per_interval': assignments_per_interval,
        'kill_opportunity_per_interval': kill_opportunity_per_interval,
        'total_kill_opportunities': total_kill_opportunities,
        'difficulty': difficulty
    }
    return result

def get_difficulty_ratio(level):
    difficulty_levels = {
        'easy': 5,
        'medium': 3,
        'hard': 1
    }
    return difficulty_levels.get(level, 3)  # Default to medium if not found

def main():
    num_players = 6  # Adjust as needed
    num_rooms = 3    # Adjust as needed
    simulation_time = 600  # Total game time in seconds (e.g., 10 minutes)
    assignment_interval = 10  # Room assignments change every 10 seconds

    # Iterate through difficulty levels
    difficulty_levels = ['easy', 'medium', 'hard']
    for difficulty_level in difficulty_levels:
        difficulty_ratio = get_difficulty_ratio(difficulty_level)
        max_X = simulation_time // assignment_interval  # Maximum value of X (number of intervals)
        print(f"\n=== Difficulty Level: {difficulty_level.capitalize()} ===")
        # Iterate over X starting from max_X down to 1
        for X in range(max_X, 0, -1):
            # Run the simulation
            result = run_simulation(
                num_players=num_players,
                num_rooms=num_rooms,
                simulation_time=simulation_time,
                assignment_interval=assignment_interval,
                X=X,
                difficulty_ratio=difficulty_ratio
            )
            total_kill_opportunities = result['total_kill_opportunities']
            required_kill_opportunities = difficulty_ratio * (num_players - 2)  # Subtract impostor and one crew member

            # Check if termination condition met
            if total_kill_opportunities >= required_kill_opportunities:
                print(f"\nSuccessful game room assignment found with X = {X}")
                print(f"Total Kill Opportunities: {total_kill_opportunities}")
                print(f"Difficulty Metric: {result['difficulty']:.2f}")
                print("\nAssignments and Kill Opportunities per Interval:")
                for idx, (assignment, kill_opportunity) in enumerate(zip(result['assignments_per_interval'], result['kill_opportunity_per_interval'])):
                    print(f"Interval {idx}: Assignment = {assignment}, Kill Opportunity = {kill_opportunity}")
                break  # Exit the X loop when a successful assignment is found
        else:
            print(f"No suitable assignment found for difficulty level {difficulty_level}")

if __name__ == "__main__":
    main()
