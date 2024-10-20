import random

class Player:
    def __init__(self, name, role='crew'):
        self.name = name
        self.role = role  # 'impostor' or 'crew'
        self.status = 'alive'

def generate_initial_room_assignment(players, num_rooms, require_same_room):
    while True:
        room_assignment = {}
        for player in players:
            room_number = random.randint(0, num_rooms - 1)
            room_assignment[player.name] = room_number
        if not (impostor_has_kill_opportunity(room_assignment, players) or impostor_has_kill_opportunity_same_room(room_assignment, players)):
            return room_assignment

def impostor_has_kill_opportunity(room_assignment, players):
    # Existing function: Checks if any crew member is alone in any room (not impostor's room)
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

def impostor_has_kill_opportunity_same_room(room_assignment, players):
    # New function: Checks if a crew member is alone in the same room as the impostor
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
    # Players in the impostor's room
    players_in_impostor_room = rooms[impostor_room_number]
    # Check if only the impostor and one crew member are in the room
    crew_members = [p for p in players_in_impostor_room if p.role == 'crew' and p.status == 'alive']
    if len(crew_members) == 1 and len(players_in_impostor_room) == 2:
        return True  # Kill opportunity exists (crew member alone with impostor)
    return False

def simulate_game_with_constraints(players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill, require_same_room):
    kill_opportunities = 0
    kill_opportunity_duration = 0
    kill_opportunity_counted = False

    kill_opportunities_same_room = 0
    kill_opportunity_duration_same_room = 0
    kill_opportunity_counted_same_room = False

    # Generate initial assignment where impostor cannot kill immediately
    room_assignment = generate_initial_room_assignment(players, num_rooms, require_same_room)
    last_reassignment_interval = {player.name: 0 for player in players}

    assignments_per_interval = []
    kill_opportunity_per_interval = []
    has_kill_opportunity_per_interval = []
    kill_opportunity_duration_per_interval = []

    kill_opportunity_per_interval_same_room = []
    has_kill_opportunity_per_interval_same_room = []
    kill_opportunity_duration_per_interval_same_room = []

    num_intervals = simulation_time // assignment_interval
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

        # Track kill opportunities
        kill_opportunity_in_interval = False
        has_kill_opportunity = False

        kill_opportunity_in_interval_same_room = False
        has_kill_opportunity_same_room = False

        # Simulate each second within the interval
        for second in range(assignment_interval):
            current_time += 1

            # Kill opportunity (any room)
            current_has_kill_opportunity = impostor_has_kill_opportunity(room_assignment, players)
            if current_has_kill_opportunity:
                has_kill_opportunity = True
                kill_opportunity_duration += 1
                if kill_opportunity_duration >= min_time_per_kill and not kill_opportunity_counted:
                    kill_opportunities += 1
                    kill_opportunity_counted = True
                    kill_opportunity_in_interval = True
            else:
                kill_opportunity_duration = 0
                kill_opportunity_counted = False

            # Kill opportunity (same room)
            current_has_kill_opportunity_same_room = impostor_has_kill_opportunity_same_room(room_assignment, players)
            if current_has_kill_opportunity_same_room:
                has_kill_opportunity_same_room = True
                kill_opportunity_duration_same_room += 1
                if kill_opportunity_duration_same_room >= min_time_per_kill and not kill_opportunity_counted_same_room:
                    kill_opportunities_same_room += 1
                    kill_opportunity_counted_same_room = True
                    kill_opportunity_in_interval_same_room = True
            else:
                kill_opportunity_duration_same_room = 0
                kill_opportunity_counted_same_room = False

            # Check termination condition
            if require_same_room:
                if kill_opportunities_same_room >= difficulty_ratio * (len(players) - 2):
                    break
            else:
                if kill_opportunities >= difficulty_ratio * (len(players) - 2):
                    break

        kill_opportunity_per_interval.append(kill_opportunity_in_interval)
        has_kill_opportunity_per_interval.append(has_kill_opportunity)
        kill_opportunity_duration_per_interval.append(kill_opportunity_duration)

        kill_opportunity_per_interval_same_room.append(kill_opportunity_in_interval_same_room)
        has_kill_opportunity_per_interval_same_room.append(has_kill_opportunity_same_room)
        kill_opportunity_duration_per_interval_same_room.append(kill_opportunity_duration_same_room)

        # Check termination condition after each interval
        if require_same_room:
            if kill_opportunities_same_room >= difficulty_ratio * (len(players) - 2):
                break
        else:
            if kill_opportunities >= difficulty_ratio * (len(players) - 2):
                break

    result = {
        'assignments_per_interval': assignments_per_interval,
        'kill_opportunity_per_interval': kill_opportunity_per_interval,
        'has_kill_opportunity_per_interval': has_kill_opportunity_per_interval,
        'kill_opportunity_duration_per_interval': kill_opportunity_duration_per_interval,
        'total_kill_opportunities': kill_opportunities,
        'kill_opportunity_per_interval_same_room': kill_opportunity_per_interval_same_room,
        'has_kill_opportunity_per_interval_same_room': has_kill_opportunity_per_interval_same_room,
        'kill_opportunity_duration_per_interval_same_room': kill_opportunity_duration_per_interval_same_room,
        'total_kill_opportunities_same_room': kill_opportunities_same_room,
        'players': players
    }

    return result

def run_simulation(num_players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill, require_same_room):
    # Create players
    players = [Player(name=f"Player_{i+1}") for i in range(num_players)]
    players[0].role = 'impostor'  # First player is the impostor

    # Simulate the game
    result = simulate_game_with_constraints(
        players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio, min_time_per_kill, require_same_room
    )

    # Calculate Difficulty metric
    num_crew = num_players - 1  # Subtract impostor
    if require_same_room:
        total_kill_opportunities = result['total_kill_opportunities_same_room']
    else:
        total_kill_opportunities = result['total_kill_opportunities']

    difficulty = total_kill_opportunities / (num_crew - 1)

    result['difficulty'] = difficulty

    return result

def get_difficulty_ratio(level):
    difficulty_levels = {
        'easy': 2,
        'medium': 1.5,
        'hard': 1
    }
    return difficulty_levels.get(level, 3)  # Default to medium if not found

def main():
    num_players = 6  # Adjust as needed
    num_rooms = 3    # Adjust as needed
    simulation_time = 1200  # Total game time in seconds (e.g., 10 minutes)
    assignment_interval = 10  # Room assignments change every 10 seconds
    min_time_per_kill = 30  # Minimum time kill opportunity must persist
    require_same_room = True  # Toggle between the two kill opportunity definitions

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
                min_time_per_kill=min_time_per_kill,
                require_same_room=require_same_room
            )

            if require_same_room:
                total_kill_opportunities = result['total_kill_opportunities_same_room']
            else:
                total_kill_opportunities = result['total_kill_opportunities']

            required_kill_opportunities = difficulty_ratio * (num_players - 2)  # Subtract impostor and one crew member

            if total_kill_opportunities >= required_kill_opportunities:
                print(f"\nSuccessful game room assignment found with X = {X}")
                print(f"Total Kill Opportunities: {total_kill_opportunities}")
                print(f"Difficulty Metric: {result['difficulty']:.2f}")

                # Print the roles of each player
                print("\nPlayer Roles:")
                for player in result['players']:
                    print(f"{player.name}: {player.role}")

                print("\nAssignments and Kill Opportunities per Interval:")
                for idx, assignment in enumerate(result['assignments_per_interval']):
                    # Build a string to display roles with assignments
                    assignment_with_roles = {}
                    for player_name, room_number in assignment.items():
                        assignment_with_roles[player_name] = room_number
                    if require_same_room:
                        kill_opportunity = result['kill_opportunity_per_interval_same_room'][idx]
                        has_kill_opportunity = result['has_kill_opportunity_per_interval_same_room'][idx]
                        duration = result['kill_opportunity_duration_per_interval_same_room'][idx]
                    else:
                        kill_opportunity = result['kill_opportunity_per_interval'][idx]
                        has_kill_opportunity = result['has_kill_opportunity_per_interval'][idx]
                        duration = result['kill_opportunity_duration_per_interval'][idx]
                    print(f"Interval {idx}: {assignment_with_roles}, kill opp: {has_kill_opportunity}, kill opportunity {min_time_per_kill} sec: {kill_opportunity}, game duration: {(simulation_time // max_X) * idx} ")

                break  # Exit the X loop when a successful assignment is found
        else:
            print(f"No suitable assignment found for difficulty level {difficulty_level}")

if __name__ == "__main__":
    main()