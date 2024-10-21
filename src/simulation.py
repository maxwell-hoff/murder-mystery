import random
import math

class Player:
    def __init__(self, name, role='crew'):
        self.name = name
        self.role = role  # 'impostor' or 'crew'
        self.status = 'alive'

def generate_initial_room_assignment(players, num_rooms):
    room_assignment = {}
    for player in players:
        room_number = random.randint(0, num_rooms - 1)
        room_assignment[player.name] = room_number
    return room_assignment

def simulate_game_with_constraints(
    players, num_rooms, simulation_time, assignment_interval, min_time_in_room_intervals, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery,
    max_seconds_until_discovery, initial_room_assignment=None, kill_rooms=None
):
    # Convert min_time_per_kill to intervals
    min_kill_intervals = math.ceil(min_time_per_kill / assignment_interval)

    # Calculate required kill opportunities
    required_kill_opportunities = int(difficulty_ratio * (len(players) - 2))
    if required_kill_opportunities < 1:
        required_kill_opportunities = 1

    # Initialize variables
    assignments_per_interval = []
    kill_opportunities_same_room = 0
    kill_rooms = {} if kill_rooms is None else kill_rooms.copy()
    last_reassignment_interval = {player.name: -min_time_in_room_intervals for player in players}
    total_intervals = simulation_time // assignment_interval

    # Schedule kill opportunities with variation and ensure no kill in the first interval
    kill_intervals = []
    current_interval = 1  # Start from interval 1 to avoid first interval
    while len(kill_intervals) < required_kill_opportunities and current_interval < total_intervals:
        # Random waiting time between kills
        min_wait = 1  # Minimum intervals to wait before next kill
        max_wait = 5  # Maximum intervals to wait before next kill
        waiting_intervals = random.randint(min_wait, max_wait)
        current_interval += waiting_intervals
        if current_interval + min_kill_intervals <= total_intervals:
            kill_intervals.append(current_interval)
            current_interval += min_kill_intervals  # Ensure minimum time per kill opportunity
        else:
            break
    kill_intervals = sorted(kill_intervals)

    # If not enough kill intervals were generated, adjust the schedule
    if len(kill_intervals) < required_kill_opportunities:
        # Adjust the required kill opportunities
        required_kill_opportunities = len(kill_intervals)

    crew_members_alive = [p.name for p in players if p.role == 'crew' and p.status == 'alive']
    random.shuffle(crew_members_alive)

    # Assign a crew member to be killed at each kill opportunity
    kill_schedule = {}
    for idx, interval in enumerate(kill_intervals):
        if idx < len(crew_members_alive):
            crew_member_to_kill = crew_members_alive[idx]
            kill_schedule[interval] = crew_member_to_kill
        else:
            # If more kill opportunities than crew members, reuse crew members
            crew_member_to_kill = random.choice(crew_members_alive)
            kill_schedule[interval] = crew_member_to_kill

    # Simulate game intervals
    kill_opportunity_per_interval_same_room = []
    has_kill_opportunity_per_interval_same_room = []
    kill_opportunity_duration_per_interval_same_room = []

    current_kill_duration = 0
    current_crew_member = None
    current_room_number = None
    kill_started_interval = None

    for interval in range(total_intervals):
        room_assignment = {}

        # Update time since kill for each room
        for room_number in list(kill_rooms.keys()):
            kill_rooms[room_number]['time_since_kill'] += assignment_interval
            # Remove rooms where discovery time has passed
            if kill_rooms[room_number]['time_since_kill'] >= max_seconds_until_discovery:
                del kill_rooms[room_number]

        # Update player statuses if any kills occurred
        for room_info in kill_rooms.values():
            killed_player_name = room_info['killed_player']
            killed_player = next((p for p in players if p.name == killed_player_name), None)
            if killed_player and killed_player.status != 'dead':
                killed_player.status = 'dead'

        # Prepare list of alive players
        alive_players = [p for p in players if p.status == 'alive']
        impostor = next((p for p in alive_players if p.role == 'impostor'), None)
        alive_crew_members = [p for p in alive_players if p.role == 'crew']

        # Check if game can continue
        if not impostor or len(alive_crew_members) == 0:
            break

        # Generate room assignments for the interval
        available_rooms = list(range(num_rooms))
        random.shuffle(available_rooms)

        if interval in kill_schedule:
            # Start a new kill opportunity
            crew_member_to_kill = kill_schedule[interval]
            # Assign impostor and crew member to the same room
            room_number = random.choice(available_rooms)
            room_assignment[impostor.name] = room_number
            room_assignment[crew_member_to_kill] = room_number
            current_crew_member = crew_member_to_kill
            current_room_number = room_number
            current_kill_duration = assignment_interval
            kill_started_interval = interval
            # Assign other players to rooms ensuring no additional kill opportunities
            other_players = [p for p in alive_players if p.name not in [impostor.name, crew_member_to_kill]]
            for player in other_players:
                possible_rooms = [r for r in available_rooms if r != room_number]
                if possible_rooms:
                    room_assignment[player.name] = random.choice(possible_rooms)
                else:
                    room_assignment[player.name] = room_number
        elif current_kill_duration > 0 and current_crew_member:
            # Continue the existing kill opportunity
            room_assignment[impostor.name] = current_room_number
            room_assignment[current_crew_member] = current_room_number
            current_kill_duration += assignment_interval
            # Assign other players
            other_players = [p for p in alive_players if p.name not in [impostor.name, current_crew_member]]
            for player in other_players:
                possible_rooms = [r for r in available_rooms if r != current_room_number]
                if possible_rooms:
                    room_assignment[player.name] = random.choice(possible_rooms)
                else:
                    room_assignment[player.name] = current_room_number
            # Check if kill opportunity duration has reached min_time_per_kill
            if current_kill_duration >= min_time_per_kill:
                kill_opportunities_same_room += 1
                # Record the kill room and reset its timer
                kill_rooms[current_room_number] = {
                    'time_since_kill': 0,
                    'killed_player': current_crew_member
                }
                # Mark the killed player as dead
                killed_player = next((p for p in players if p.name == current_crew_member), None)
                if killed_player:
                    killed_player.status = 'dead'
                # Reset kill opportunity tracking
                current_kill_duration = 0
                current_crew_member = None
                current_room_number = None
        else:
            # No kill opportunity in this interval
            current_kill_duration = 0
            current_crew_member = None
            current_room_number = None
            kill_started_interval = None
            # Assign players to rooms ensuring no kill opportunities
            for player in alive_players:
                time_in_room = interval - last_reassignment_interval[player.name]
                if time_in_room >= min_time_in_room_intervals:
                    # Assign to a room
                    if player.role == 'impostor':
                        impostor_room = random.choice(available_rooms)
                        room_assignment[player.name] = impostor_room
                    else:
                        # Exclude rooms with bodies where min_seconds_until_discovery has not passed
                        forbidden_rooms = [
                            room_number for room_number, room_info in kill_rooms.items()
                            if room_info['time_since_kill'] < min_seconds_until_discovery
                        ]
                        possible_rooms = [r for r in available_rooms if r != room_assignment.get(impostor.name, -1) and r not in forbidden_rooms]
                        if possible_rooms:
                            room_assignment[player.name] = random.choice(possible_rooms)
                        else:
                            room_assignment[player.name] = random.choice(available_rooms)
                    last_reassignment_interval[player.name] = interval
                else:
                    # Keep the player in the same room
                    room_assignment[player.name] = room_assignment.get(player.name, random.choice(available_rooms))

        # Record the room assignment
        assignments_per_interval.append(room_assignment.copy())

        # Check for unintended kill opportunities
        has_kill_opportunity = False
        kill_opportunity_in_interval = False
        duration = current_kill_duration

        # Ensure no unintended kill opportunities occur
        impostor_room = room_assignment.get(impostor.name)
        for player_name, room_number in room_assignment.items():
            if player_name != impostor.name and room_number == impostor_room:
                # Check if this is the intended kill opportunity
                if current_crew_member and player_name == current_crew_member:
                    has_kill_opportunity = True
                    kill_opportunity_in_interval = True
                else:
                    # Unintended kill opportunity, adjust assignment
                    other_rooms = [r for r in available_rooms if r != impostor_room]
                    if other_rooms:
                        room_assignment[player_name] = random.choice(other_rooms)
                    else:
                        # If no other rooms, swap with another player
                        for other_player_name in room_assignment:
                            if other_player_name != impostor.name and other_player_name != player_name:
                                temp_room = room_assignment[other_player_name]
                                room_assignment[other_player_name] = room_assignment[player_name]
                                room_assignment[player_name] = temp_room
                                break

        has_kill_opportunity_per_interval_same_room.append(has_kill_opportunity)
        kill_opportunity_per_interval_same_room.append(kill_opportunity_in_interval)
        kill_opportunity_duration_per_interval_same_room.append(duration)

    # Prepare result
    result = {
        'assignments_per_interval': assignments_per_interval,
        'total_kill_opportunities_same_room': kill_opportunities_same_room,
        'players': players,
        'kill_rooms': kill_rooms,
        'has_kill_opportunity_per_interval_same_room': has_kill_opportunity_per_interval_same_room,
        'kill_opportunity_per_interval_same_room': kill_opportunity_per_interval_same_room,
        'kill_opportunity_duration_per_interval_same_room': kill_opportunity_duration_per_interval_same_room,
        'required_kill_opportunities': required_kill_opportunities
    }
    return result

def run_simulation(
    num_players, num_rooms, simulation_time, assignment_interval, min_time_in_room_minutes, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery, max_seconds_until_discovery,
    num_initial_assignments=10, max_attempts_per_assignment=10, initial_room_assignments=None, kill_rooms_list=None
):
    # Convert min_time_in_room_minutes to seconds and intervals
    min_time_in_room_seconds = min_time_in_room_minutes * 60
    min_time_in_room_intervals = min_time_in_room_seconds / assignment_interval

    # Calculate required kill opportunities
    required_kill_opportunities = int(difficulty_ratio * (num_players - 2))
    if required_kill_opportunities < 1:
        required_kill_opportunities = 1

    # Loop over the number of initial assignments
    for initial_assignment_index in range(num_initial_assignments):
        # Generate or use the provided initial room assignment
        initial_room_assignment = None  # Will be generated inside the simulation function

        # Use the provided kill_rooms if available
        kill_rooms = None  # Start with empty kill_rooms

        # Try up to max_attempts_per_assignment for each initial assignment
        for attempt in range(max_attempts_per_assignment):
            # Create players
            players = [Player(name=f"Player_{i+1}") for i in range(num_players)]
            players[0].role = 'impostor'  # First player is the impostor

            # Simulate the game
            result = simulate_game_with_constraints(
                players, num_rooms, simulation_time, assignment_interval, min_time_in_room_intervals, difficulty_ratio,
                min_time_per_kill, require_same_room, min_seconds_until_discovery,
                max_seconds_until_discovery, initial_room_assignment, kill_rooms
            )

            # Check if the required kill opportunities were achieved
            if result['total_kill_opportunities_same_room'] >= required_kill_opportunities:
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
    simulation_time = 600  # Total game time in seconds
    assignment_interval = 10  # Room assignments change every 10 seconds
    min_time_per_kill = 30  # Kill opportunity must persist for at least 30 seconds
    min_seconds_until_discovery = 240  # Minimum time until a body is discovered
    max_seconds_until_discovery = 1000  # Maximum time until a body is discovered
    require_same_room = True  # Focus on same room kill opportunities
    # Set the difficulty level directly
    difficulty_level = 'hard'
    difficulty_ratio = get_difficulty_ratio(difficulty_level)
    # Number of initial room assignments to try
    num_initial_assignments = 10
    max_attempts_per_assignment = 10
    # Set minimum time a player must stay in a room (in minutes)
    min_time_in_room_minutes = 2  # Players must stay in the same room for at least 2 minutes

    # Run the simulation
    result = run_simulation(
        num_players=num_players,
        num_rooms=num_rooms,
        simulation_time=simulation_time,
        assignment_interval=assignment_interval,
        min_time_in_room_minutes=min_time_in_room_minutes,
        difficulty_ratio=difficulty_ratio,
        min_time_per_kill=min_time_per_kill,
        require_same_room=require_same_room,
        min_seconds_until_discovery=min_seconds_until_discovery,
        max_seconds_until_discovery=max_seconds_until_discovery,
        num_initial_assignments=num_initial_assignments,
        max_attempts_per_assignment=max_attempts_per_assignment
    )

    if result is not None:
        # Successful simulation found
        total_kill_opportunities = result['total_kill_opportunities_same_room']
        required_kill_opportunities = result['required_kill_opportunities']
        print(f"\nSuccessful game room assignment found with minimum time in room = {min_time_in_room_minutes} minutes")
        print(f"Total Kill Opportunities: {total_kill_opportunities}")
        print(f"Required Kill Opportunities: {required_kill_opportunities}")
        difficulty_metric = total_kill_opportunities / required_kill_opportunities if required_kill_opportunities > 0 else 0
        print(f"Difficulty Metric: {difficulty_metric:.2f}")

        # Print the roles and statuses of each player
        print("\nPlayer Roles:")
        for player in result['players']:
            print(f"{player.name}: {player.role}, status: {player.status}")

        print("\nAssignments and Kill Opportunities per Interval:")
        for idx, assignment in enumerate(result['assignments_per_interval']):
            assignment_with_roles = assignment.copy()
            kill_opportunity = result['kill_opportunity_per_interval_same_room'][idx]
            has_kill_opportunity = result['has_kill_opportunity_per_interval_same_room'][idx]
            duration = result['kill_opportunity_duration_per_interval_same_room'][idx]
            print(f"Interval {idx}: {assignment_with_roles}, Has Kill Opportunity: {has_kill_opportunity}, "
                  f"Kill Opportunity Duration: {duration} seconds, "
                  f"Kill Opportunity Passed {min_time_per_kill}s Threshold: {kill_opportunity}")
    else:
        print(f"No suitable assignment found after {num_initial_assignments} initial assignments")

if __name__ == "__main__":
    main()
