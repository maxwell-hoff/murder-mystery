import random
import math

class Player:
    def __init__(self, name, role='crew'):
        self.name = name
        self.role = role  # 'impostor' or 'crew'
        self.status = 'alive'

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
    total_intervals = simulation_time // assignment_interval

    # Initialize last reassignment intervals
    last_reassignment_interval = {player.name: 0 for player in players}

    # Initialize current room assignment
    if initial_room_assignment is not None:
        current_room_assignment = initial_room_assignment.copy()
    else:
        # Random initial assignment
        available_rooms = list(range(num_rooms))
        current_room_assignment = {}
        for player in players:
            current_room_assignment[player.name] = random.choice(available_rooms)

    # Schedule kill opportunities
    kill_intervals = []
    current_interval = 1
    while len(kill_intervals) < required_kill_opportunities and current_interval < total_intervals:
        min_wait = 1
        max_wait = 5
        waiting_intervals = random.randint(min_wait, max_wait)
        current_interval += waiting_intervals
        if current_interval + min_kill_intervals <= total_intervals:
            kill_intervals.append(current_interval)
            current_interval += min_kill_intervals
        else:
            break
    kill_intervals = sorted(kill_intervals)

    if len(kill_intervals) < required_kill_opportunities:
        required_kill_opportunities = len(kill_intervals)

    crew_members_alive = [p.name for p in players if p.role == 'crew']
    random.shuffle(crew_members_alive)

    # Assign a crew member to be killed at each kill opportunity
    kill_schedule = {}
    for idx, interval in enumerate(kill_intervals):
        if idx < len(crew_members_alive):
            crew_member_to_kill = crew_members_alive[idx]
            kill_schedule[interval] = crew_member_to_kill
        else:
            crew_member_to_kill = random.choice(crew_members_alive)
            kill_schedule[interval] = crew_member_to_kill

    # Initialize variables for kill tracking
    kill_opportunity_per_interval_same_room = []
    has_kill_opportunity_per_interval_same_room = []
    kill_opportunity_duration_per_interval_same_room = []

    current_kill_duration = 0
    current_crew_member = None
    current_room_number = None

    # Start the simulation loop
    for interval in range(total_intervals):
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
        if not impostor:
            break  # Game ends if impostor is dead

        # Initialize room_assignment as a copy of current_room_assignment
        room_assignment = current_room_assignment.copy()

        # Handle kill opportunities
        if interval in kill_schedule:
            # Start a new kill opportunity
            crew_member_to_kill = kill_schedule[interval]
            room_number = random.choice(list(range(num_rooms)))
            current_room_assignment[impostor.name] = room_number
            current_room_assignment[crew_member_to_kill] = room_number

            # Update last reassignment interval
            last_reassignment_interval[impostor.name] = interval
            last_reassignment_interval[crew_member_to_kill] = interval

            # Initialize kill tracking variables
            current_kill_duration = assignment_interval
            current_crew_member = crew_member_to_kill
            current_room_number = room_number

        elif current_kill_duration > 0 and current_crew_member:
            # Continue the existing kill opportunity
            current_kill_duration += assignment_interval

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

        # Now handle other players
        for player in alive_players:
            if player.name in [impostor.name, current_crew_member]:
                continue  # Already handled

            time_in_room = interval - last_reassignment_interval[player.name]
            if time_in_room >= min_time_in_room_intervals:
                # Reassign player
                forbidden_rooms = [
                    room_number for room_number, room_info in kill_rooms.items()
                    if room_info['time_since_kill'] < min_seconds_until_discovery
                ]
                possible_rooms = [r for r in range(num_rooms) if r not in forbidden_rooms]
                if possible_rooms:
                    new_room = random.choice(possible_rooms)
                    current_room_assignment[player.name] = new_room
                    last_reassignment_interval[player.name] = interval
                else:
                    # No rooms available, keep the player in the current room
                    pass
            else:
                # Keep the player in the same room
                pass  # No action needed

        # Ensure no unintended kill opportunities occur
        has_kill_opportunity = False
        kill_opportunity_in_interval = False
        duration = current_kill_duration

        # Check for unintended kill opportunities
        impostor_room = current_room_assignment.get(impostor.name)
        for player_name in current_room_assignment:
            if player_name != impostor.name and current_room_assignment[player_name] == impostor_room:
                # Check if this is the intended kill opportunity
                if current_crew_member and player_name == current_crew_member:
                    has_kill_opportunity = True
                    kill_opportunity_in_interval = True
                else:
                    # Unintended kill opportunity, adjust assignment
                    other_rooms = [r for r in range(num_rooms) if r != impostor_room]
                    if other_rooms:
                        current_room_assignment[player_name] = random.choice(other_rooms)
                    else:
                        # If no other rooms, swap with another player
                        for other_player_name in current_room_assignment:
                            if other_player_name != impostor.name and other_player_name != player_name:
                                temp_room = current_room_assignment[other_player_name]
                                current_room_assignment[other_player_name] = current_room_assignment[player_name]
                                current_room_assignment[player_name] = temp_room
                                break

        # Record the room assignment
        room_assignment = current_room_assignment.copy()
        assignments_per_interval.append(room_assignment)

        # Track kill opportunity per interval
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
    players, num_rooms, simulation_time, assignment_interval, min_time_in_room_minutes, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery, max_seconds_until_discovery,
    num_initial_assignments=10, max_attempts_per_assignment=10
):
    # Convert min_time_in_room_minutes to seconds and intervals
    min_time_in_room_seconds = min_time_in_room_minutes * 60
    min_time_in_room_intervals = min_time_in_room_seconds / assignment_interval

    # Calculate required kill opportunities
    required_kill_opportunities = int(difficulty_ratio * (len(players) - 2))
    if required_kill_opportunities < 1:
        required_kill_opportunities = 1

    # Loop over the number of initial assignments
    for initial_assignment_index in range(num_initial_assignments):
        # Try up to max_attempts_per_assignment for each initial assignment
        for attempt in range(max_attempts_per_assignment):
            for player in players:
                player.status = 'alive'

            # Simulate the game
            result = simulate_game_with_constraints(
                players, num_rooms, simulation_time, assignment_interval, min_time_in_room_intervals, difficulty_ratio,
                min_time_per_kill, require_same_room, min_seconds_until_discovery,
                max_seconds_until_discovery
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
            kill_opportunity = result['kill_opportunity_per_interval_same_room'][idx]
            has_kill_opportunity = result['has_kill_opportunity_per_interval_same_room'][idx]
            duration = result['kill_opportunity_duration_per_interval_same_room'][idx]
            print(f"Interval {idx}: {assignment}, Has Kill Opportunity: {has_kill_opportunity}, "
                  f"Kill Opportunity Duration: {duration} seconds, "
                  f"Kill Opportunity Passed {min_time_per_kill}s Threshold: {kill_opportunity}")
    else:
        print(f"No suitable assignment found after {num_initial_assignments} initial assignments")

if __name__ == "__main__":
    main()
