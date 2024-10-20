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

def simulate_game_with_constraints(players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill):
    kill_opportunities = 0
    kill_opportunity_duration = 0  # Duration that kill opportunity has persisted
    kill_opportunity_counted = False  # Whether kill opportunity has been counted for current continuous period

    # Generate initial assignment where impostor cannot kill immediately
    room_assignment = generate_initial_room_assignment(players, num_rooms)
    # Record the last reassignment interval for each player (initial assignment at interval 0)
    last_reassignment_interval = {player.name: 0 for player in players}

    # Record assignments and kill opportunities per interval
    assignments_per_interval = []
    kill_opportunity_per_interval = []
    has_kill_opportunity_per_interval = []
    kill_opportunity_duration_per_interval = []

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

        # Track if a kill opportunity is counted during this interval
        kill_opportunity_in_interval = False
        has_kill_opportunity = False  # To record if there's any kill opportunity in this interval

        # Simulate each second within the interval
        for second in range(assignment_interval):
            current_time += 1
            # Check if impostor has a kill opportunity
            current_has_kill_opportunity = impostor_has_kill_opportunity(room_assignment, players)

            if current_has_kill_opportunity:
                has_kill_opportunity = True  # There is a kill opportunity at some point in this interval
                kill_opportunity_duration += 1
                if kill_opportunity_duration >= min_time_per_kill and not kill_opportunity_counted:
                    # Kill opportunity has persisted for at least 30 seconds continuously
                    kill_opportunities += 1
                    kill_opportunity_counted = True
                    kill_opportunity_in_interval = True
            else:
                kill_opportunity_duration = 0
                kill_opportunity_counted = False  # Reset when kill opportunity is lost

            # Check termination condition
            if kill_opportunities >= difficulty_ratio * (len(players) - 2):
                break  # Exit the second loop

        kill_opportunity_per_interval.append(kill_opportunity_in_interval)
        has_kill_opportunity_per_interval.append(has_kill_opportunity)
        kill_opportunity_duration_per_interval.append(kill_opportunity_duration)

        # Check termination condition after each interval
        if kill_opportunities >= difficulty_ratio * (len(players) - 2):
            break  # Exit the interval loop

    return assignments_per_interval, kill_opportunity_per_interval, has_kill_opportunity_per_interval, kill_opportunity_duration_per_interval, kill_opportunities, players

def run_simulation(num_players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill):
    # Create players
    players = [Player(name=f"Player_{i+1}") for i in range(num_players)]
    # Assign roles
    players[0].role = 'impostor'  # First player is the impostor

    # Simulate the game
    assignments_per_interval, kill_opportunity_per_interval, has_kill_opportunity_per_interval, kill_opportunity_duration_per_interval, total_kill_opportunities, players = simulate_game_with_constraints(
        players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill
    )

    # Calculate Difficulty metric
    num_crew = num_players - 1  # Subtract impostor
    difficulty = total_kill_opportunities / (num_crew - 1)  # Number of crew minus one

    result = {
        'assignments_per_interval': assignments_per_interval,
        'kill_opportunity_per_interval': kill_opportunity_per_interval,
        'has_kill_opportunity_per_interval': has_kill_opportunity_per_interval,
        'kill_opportunity_duration_per_interval': kill_opportunity_duration_per_interval,
        'total_kill_opportunities': total_kill_opportunities,
        'difficulty': difficulty,
        'players': players
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
    min_time_per_kill = 30  # Minimum time impostor must wait between kills

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
                difficulty_ratio=difficulty_ratio,
                min_time_per_kill=min_time_per_kill
            )
            total_kill_opportunities = result['total_kill_opportunities']
            required_kill_opportunities = difficulty_ratio * (num_players - 2)  # Subtract impostor and one crew member

            # Check if termination condition met
            if total_kill_opportunities >= required_kill_opportunities:
                print(f"\nSuccessful game room assignment found with X = {X}")
                print(f"Total Kill Opportunities: {total_kill_opportunities}")
                print(f"Difficulty Metric: {result['difficulty']:.2f}")

                # Print the roles of each player
                print("\nPlayer Roles:")
                for player in result['players']:
                    print(f"{player.name}: {player.role}")

                print("\nAssignments and Kill Opportunities per Interval:")
                for idx, (assignment, kill_opportunity, has_kill_opportunity, duration) in enumerate(zip(
                    result['assignments_per_interval'],
                    result['kill_opportunity_per_interval'],
                    result['has_kill_opportunity_per_interval'],
                    result['kill_opportunity_duration_per_interval']
                )):
                    # Build a string to display roles with assignments
                    assignment_with_roles = {}
                    for player_name, room_number in assignment.items():
                        assignment_with_roles[player_name] = room_number

                    print(f"Interval {idx}: {assignment_with_roles}, kill opp: {has_kill_opportunity}, kill opporuntiy {min_time_per_kill} sec: {kill_opportunity}, duration: {(simulation_time // max_X) * idx} ")
                break  # Exit the X loop when a successful assignment is found
        else:
            print(f"No suitable assignment found for difficulty level {difficulty_level}")

if __name__ == "__main__":
    main()