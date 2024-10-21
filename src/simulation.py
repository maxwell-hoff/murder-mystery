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
        # Adjusted to handle new return values
        has_kill_opportunity, _, _ = impostor_has_kill_opportunity_same_room(room_assignment, players)
        if not (impostor_has_kill_opportunity(room_assignment, players) or has_kill_opportunity):
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
    impostor = next((p for p in players if p.role == 'impostor' and p.status == 'alive'), None)
    if impostor is None:
        return False
    impostor_room_number = room_assignment.get(impostor.name)
    if impostor_room_number is None:
        return False
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
    # Returns (True, crew_member_name, room_number) if there is a kill opportunity
    # where the impostor is alone with one crew member in a room.
    # Returns (False, None, None) otherwise.
    rooms = {}
    for player_name, room_number in room_assignment.items():
        if room_number not in rooms:
            rooms[room_number] = []
        player = next(p for p in players if p.name == player_name)
        if player.status == 'alive':
            rooms[room_number].append(player)
    # Find the impostor
    impostor = next((p for p in players if p.role == 'impostor' and p.status == 'alive'), None)
    if impostor is None:
        return False, None, None
    impostor_room_number = room_assignment.get(impostor.name)
    if impostor_room_number is None:
        return False, None, None  # Impostor is not in any room
    # Players in the impostor's room
    players_in_impostor_room = rooms.get(impostor_room_number, [])
    # Check if only the impostor and one crew member are in the room
    crew_members = [p for p in players_in_impostor_room if p.role == 'crew' and p.status == 'alive']
    if len(crew_members) == 1 and len(players_in_impostor_room) == 2:
        crew_member = crew_members[0]
        return True, crew_member.name, impostor_room_number  # Kill opportunity exists
    return False, None, None

def simulate_game_with_constraints(
    players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery,
    max_seconds_until_discovery, initial_room_assignment=None, kill_rooms=None
):
    kill_opportunities = 0
    kill_opportunity_duration = 0
    kill_opportunity_counted = False

    kill_opportunities_same_room = 0
    kill_opportunity_duration_same_room = 0
    kill_opportunity_counted_same_room = False
    current_crew_member = None
    current_room = None

    # Dictionary to track rooms where kills have occurred and time since kill
    if kill_rooms is None:
        kill_rooms = {}  # key: room_number, value: {'time_since_kill': time_since_kill, 'killed_player': 'Player_X'}

    # Use initial room assignment if provided, else generate one
    if initial_room_assignment is not None:
        room_assignment = initial_room_assignment.copy()
    else:
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
        # Update time since kill for each room
        for room_number in list(kill_rooms.keys()):
            kill_rooms[room_number]['time_since_kill'] += assignment_interval
            # Remove rooms where discovery time has passed
            if kill_rooms[room_number]['time_since_kill'] >= max_seconds_until_discovery:
                del kill_rooms[room_number]

        # Reassign one eligible player
        eligible_players = [
            player for player in players
            if player.status == 'alive' and (interval - last_reassignment_interval[player.name]) >= X
        ]
        if eligible_players:
            player_to_reassign = random.choice(eligible_players)
            current_room_player = room_assignment.get(player_to_reassign.name)
            possible_rooms = list(range(num_rooms))
            if current_room_player is not None and current_room_player in possible_rooms:
                possible_rooms.remove(current_room_player)

            if player_to_reassign.role == 'impostor':
                # Impostor cannot enter any room where a kill has occurred
                possible_rooms = [room for room in possible_rooms if room not in kill_rooms]
            else:
                # Crew members cannot enter rooms where a kill has occurred and discovery time hasn't passed
                possible_rooms = [
                    room for room in possible_rooms
                    if room not in kill_rooms or (
                        min_seconds_until_discovery <= kill_rooms[room]['time_since_kill'] < max_seconds_until_discovery
                    )
                ]
                # Additionally, crew member should not be the killed player
                # This is already handled since dead players are not in eligible_players

            if possible_rooms:
                new_room = random.choice(possible_rooms)
                room_assignment[player_to_reassign.name] = new_room
                last_reassignment_interval[player_to_reassign.name] = interval
            else:
                # No rooms available; player stays in the current room
                pass

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
            current_has_kill_opportunity_same_room, crew_member_name, room_number = impostor_has_kill_opportunity_same_room(room_assignment, players)
            if current_has_kill_opportunity_same_room:
                has_kill_opportunity_same_room = True
                if current_crew_member == crew_member_name and current_room == room_number:
                    # Same crew member and room as previous second
                    kill_opportunity_duration_same_room += 1
                else:
                    # Different crew member or room
                    kill_opportunity_duration_same_room = 1  # Start over
                    kill_opportunity_counted_same_room = False  # Reset counted flag
                    current_crew_member = crew_member_name
                    current_room = room_number
                if kill_opportunity_duration_same_room >= min_time_per_kill and not kill_opportunity_counted_same_room:
                    kill_opportunities_same_room += 1
                    kill_opportunity_counted_same_room = True
                    kill_opportunity_in_interval_same_room = True
                    # Record the kill room and reset its timer
                    kill_rooms[current_room] = {
                        'time_since_kill': 0,
                        'killed_player': current_crew_member
                    }
                    # Mark the killed player as dead
                    killed_player = next(p for p in players if p.name == current_crew_member)
                    killed_player.status = 'dead'
                    # Remove the killed player from room assignments
                    if killed_player.name in room_assignment:
                        del room_assignment[killed_player.name]
            else:
                kill_opportunity_duration_same_room = 0
                kill_opportunity_counted_same_room = False
                current_crew_member = None
                current_room = None

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
        'players': players,
        'kill_rooms': kill_rooms
    }

    return result

def run_simulation(
    num_players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery, max_seconds_until_discovery,
    num_initial_assignments=10, max_attempts_per_assignment=10, initial_room_assignments=None, kill_rooms_list=None
):
    # Loop over the number of initial assignments
    for initial_assignment_index in range(num_initial_assignments):
        # Generate or use the provided initial room assignment
        if initial_room_assignments and initial_assignment_index < len(initial_room_assignments):
            initial_room_assignment = initial_room_assignments[initial_assignment_index]
        else:
            initial_room_assignment = None  # Will be generated inside the simulation function

        # Use the provided kill_rooms if available
        if kill_rooms_list and initial_assignment_index < len(kill_rooms_list):
            kill_rooms = kill_rooms_list[initial_assignment_index]
        else:
            kill_rooms = None  # Start with empty kill_rooms

        # Try up to max_attempts_per_assignment for each initial assignment
        for attempt in range(max_attempts_per_assignment):
            # Create players
            players = [Player(name=f"Player_{i+1}") for i in range(num_players)]
            players[0].role = 'impostor'  # First player is the impostor

            # If there are dead players in the kill_rooms, mark them as dead
            if kill_rooms:
                for room_info in kill_rooms.values():
                    killed_player_name = room_info['killed_player']
                    killed_player = next((p for p in players if p.name == killed_player_name), None)
                    if killed_player:
                        killed_player.status = 'dead'

            # Simulate the game
            result = simulate_game_with_constraints(
                players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio,
                min_time_per_kill, require_same_room, min_seconds_until_discovery,
                max_seconds_until_discovery, initial_room_assignment, kill_rooms.copy() if kill_rooms else None
            )

            # Calculate Difficulty metric
            num_crew = sum(1 for p in players if p.role == 'crew' and p.status == 'alive')  # Count current crew members
            if require_same_room:
                total_kill_opportunities = result['total_kill_opportunities_same_room']
            else:
                total_kill_opportunities = result['total_kill_opportunities']

            difficulty = total_kill_opportunities / max(num_crew - 1, 1)  # Avoid division by zero

            result['difficulty'] = difficulty

            # Check if termination condition met
            required_kill_opportunities = difficulty_ratio * (num_players - 2)  # Initial crew members minus one
            if total_kill_opportunities >= required_kill_opportunities:
                return result  # Successful simulation

        # If no suitable assignment found for this initial assignment, continue to next
        print(f"No suitable assignment found for initial assignment {initial_assignment_index + 1}")

    # If no suitable assignment found after all initial assignments
    return None

def get_difficulty_ratio(level):
    difficulty_levels = {
        'easy': 3,
        'medium': 2,
        'hard': 1
    }
    return difficulty_levels.get(level, 2)  # Default to medium if not found

def main():
    num_players = 6  # Adjust as needed
    num_rooms = 4    # Adjust as needed
    simulation_time = 600  # Total game time in seconds (e.g., 20 minutes)
    assignment_interval = 10  # Room assignments change every 10 seconds
    min_time_per_kill = 30  # Minimum time kill opportunity must persist
    min_seconds_until_discovery = 100  # Minimum time until a body is discovered
    max_seconds_until_discovery = 500  # Maximum time until a body is discovered
    require_same_room = True  # Toggle between the two kill opportunity definitions

    # Set the difficulty level directly
    difficulty_level = 'hard'
    difficulty_ratio = get_difficulty_ratio(difficulty_level)

    # Number of initial room assignments to try
    num_initial_assignments = 100  # Parameterized number of initial assignments
    max_attempts_per_assignment = 1000  # Number of simulations per initial assignment

    # Set initial room assignments and kill rooms if needed (optional)
    initial_room_assignments = None  # List of dictionaries for each initial assignment
    kill_rooms_list = None  # List of dictionaries for kill rooms corresponding to initial assignments

    # Set X (minimum intervals before a player can be reassigned)
    X = 2  # Adjust as needed

    # Run the simulation with the specified number of initial assignments
    result = run_simulation(
        num_players=num_players,
        num_rooms=num_rooms,
        simulation_time=simulation_time,
        assignment_interval=assignment_interval,
        X=X,
        difficulty_ratio=difficulty_ratio,
        min_time_per_kill=min_time_per_kill,
        require_same_room=require_same_room,
        min_seconds_until_discovery=min_seconds_until_discovery,
        max_seconds_until_discovery=max_seconds_until_discovery,
        num_initial_assignments=num_initial_assignments,
        max_attempts_per_assignment=max_attempts_per_assignment,
        initial_room_assignments=initial_room_assignments,
        kill_rooms_list=kill_rooms_list
    )

    if result is not None:
        # Successful simulation found
        if require_same_room:
            total_kill_opportunities = result['total_kill_opportunities_same_room']
        else:
            total_kill_opportunities = result['total_kill_opportunities']

        print(f"\nSuccessful game room assignment found")
        print(f"Total Kill Opportunities: {total_kill_opportunities}")
        print(f"Difficulty Metric: {result['difficulty']:.2f}")

        # Print the roles of each player
        print("\nPlayer Roles:")
        for player in result['players']:
            print(f"{player.name}: {player.role}, status: {player.status}")

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
            print(f"Interval {idx}: {assignment_with_roles}, Has Kill Opportunity: {has_kill_opportunity}, Kill Opportunity Duration: {duration} seconds, Kill Opportunity Passed {min_time_per_kill}s Threshold: {kill_opportunity}, interval time: {inter}")
    else:
        print(f"No suitable assignment found after {num_initial_assignments} initial assignments")

if __name__ == "__main__":
    main()
