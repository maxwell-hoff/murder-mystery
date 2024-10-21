import random
import math

class Player:
    def __init__(self, name, role='crew'):
        self.name = name
        self.role = role  # 'impostor' or 'crew'
        self.status = 'alive'

def generate_initial_room_assignment(players, num_rooms):
    room_assignment = {}
    available_rooms = list(range(num_rooms))
    random.shuffle(available_rooms)
    for player in players:
        room_number = available_rooms.pop() if available_rooms else random.randint(0, num_rooms - 1)
        room_assignment[player.name] = room_number
    return room_assignment

def impostor_has_kill_opportunity_same_room(room_assignment, players):
    # Returns (True, crew_member_name, room_number) if there is a kill opportunity
    rooms = {}
    for player_name, room_number in room_assignment.items():
        if room_number not in rooms:
            rooms[room_number] = []
        player = next((p for p in players if p.name == player_name), None)
        if player and player.status == 'alive':
            rooms[room_number].append(player)
    # Find the impostor
    impostor = next((p for p in players if p.role == 'impostor' and p.status == 'alive'), None)
    if not impostor:
        return False, None, None
    impostor_room_number = room_assignment.get(impostor.name)
    if impostor_room_number is None:
        return False, None, None
    # Players in the impostor's room
    players_in_room = rooms.get(impostor_room_number, [])
    # Check for kill opportunity
    crew_members = [p for p in players_in_room if p.role == 'crew' and p.status == 'alive']
    if len(crew_members) == 1 and len(players_in_room) == 2:
        return True, crew_members[0].name, impostor_room_number
    return False, None, None

def simulate_game_with_constraints(
    players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio,
    min_time_per_kill, require_same_room, min_seconds_until_discovery,
    max_seconds_until_discovery, initial_room_assignment=None, kill_rooms=None
):
    # Calculate required kill opportunities
    required_kill_opportunities = int(difficulty_ratio * (len(players) - 2))
    if required_kill_opportunities < 1:
        required_kill_opportunities = 1

    # Initialize variables
    assignments_per_interval = []
    kill_opportunities_same_room = 0
    kill_rooms = {} if kill_rooms is None else kill_rooms.copy()
    last_reassignment_interval = {player.name: -X for player in players}
    total_intervals = simulation_time // assignment_interval
    intervals_per_kill = math.ceil(min_time_per_kill / assignment_interval)
    kill_opportunity_intervals = []

    # Schedule kill opportunities
    available_intervals = list(range(total_intervals))
    random.shuffle(available_intervals)
    kill_intervals = sorted(available_intervals[:required_kill_opportunities])
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
        if interval in kill_schedule:
            # Create kill opportunity
            crew_member_to_kill = kill_schedule[interval]
            # Assign impostor and crew member to the same room
            room_number = random.randint(0, num_rooms - 1)
            room_assignment[impostor.name] = room_number
            room_assignment[crew_member_to_kill] = room_number
            # Assign other players to different rooms ensuring no additional kill opportunities
            other_players = [p for p in alive_players if p.name not in [impostor.name, crew_member_to_kill]]
            available_rooms = [r for r in range(num_rooms) if r != room_number]
            for player in other_players:
                assigned = False
                for r in available_rooms:
                    if r not in room_assignment.values():
                        room_assignment[player.name] = r
                        assigned = True
                        break
                if not assigned:
                    room_assignment[player.name] = random.choice(available_rooms)
        else:
            # Assign players to rooms ensuring no kill opportunities
            available_rooms = list(range(num_rooms))
            random.shuffle(available_rooms)
            for player in alive_players:
                if interval - last_reassignment_interval[player.name] >= X:
                    # Assign to a room not occupied by the impostor
                    if player.role == 'impostor':
                        impostor_room = random.choice(available_rooms)
                        room_assignment[player.name] = impostor_room
                        available_rooms.remove(impostor_room)
                    else:
                        # Assign crew members to rooms not causing kill opportunities
                        possible_rooms = [r for r in available_rooms if r != room_assignment.get(impostor.name, -1)]
                        if possible_rooms:
                            room = possible_rooms.pop()
                            room_assignment[player.name] = room
                            available_rooms.remove(room)
                        else:
                            room_assignment[player.name] = random.choice(available_rooms)
                else:
                    # Keep the player in the same room
                    room_assignment[player.name] = room_assignment.get(player.name, random.choice(available_rooms))
        # Record the last reassignment interval
        for player_name in room_assignment.keys():
            last_reassignment_interval[player_name] = interval

        # Record the room assignment
        assignments_per_interval.append(room_assignment.copy())

        # Check for kill opportunity in this interval
        has_kill_opportunity, crew_member_name, room_number = impostor_has_kill_opportunity_same_room(room_assignment, players)
        if has_kill_opportunity and interval in kill_schedule:
            kill_opportunities_same_room += 1
            # Record the kill room and reset its timer
            kill_rooms[room_number] = {
                'time_since_kill': 0,
                'killed_player': crew_member_name
            }
            # Mark the killed player as dead
            killed_player = next((p for p in players if p.name == crew_member_name), None)
            if killed_player:
                killed_player.status = 'dead'
                # Remove the killed player from room assignments
                del room_assignment[killed_player.name]
        else:
            # Ensure no unintended kill opportunities occur
            if has_kill_opportunity:
                # Adjust assignments to remove unintended kill opportunities
                # For simplicity, swap the crew member to another room
                crew_member = next((p for p in players if p.name == crew_member_name), None)
                if crew_member:
                    other_rooms = [r for r in range(num_rooms) if r != room_assignment[impostor.name]]
                    room_assignment[crew_member.name] = random.choice(other_rooms)

    # Prepare result
    result = {
        'assignments_per_interval': assignments_per_interval,
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

            # Simulate the game
            result = simulate_game_with_constraints(
                players, num_rooms, simulation_time, assignment_interval, X, difficulty_ratio,
                min_time_per_kill, require_same_room, min_seconds_until_discovery,
                max_seconds_until_discovery, initial_room_assignment, kill_rooms
            )

            # Check if the required kill opportunities were achieved
            if result['total_kill_opportunities_same_room'] >= int(difficulty_ratio * (num_players - 2)):
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
    simulation_time = 600  # Total game time in seconds (e.g., 10 minutes)
    assignment_interval = 10  # Room assignments change every 10 seconds
    min_time_per_kill = 30  # Minimum time kill opportunity must persist
    min_seconds_until_discovery = 240  # Minimum time until a body is discovered
    max_seconds_until_discovery = 1000  # Maximum time until a body is discovered
    require_same_room = True  # We are focusing on same room kill opportunities

    # Set the difficulty level directly
    difficulty_level = 'hard'
    difficulty_ratio = get_difficulty_ratio(difficulty_level)

    # Number of initial room assignments to try
    num_initial_assignments = 10  # Parameterized number of initial assignments
    max_attempts_per_assignment = 10  # Number of simulations per initial assignment

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
        initial_room_assignments=None,
        kill_rooms_list=None
    )

    if result is not None:
        # Successful simulation found
        total_kill_opportunities = result['total_kill_opportunities_same_room']

        print(f"\nSuccessful game room assignment found")
        print(f"Total Kill Opportunities: {total_kill_opportunities}")

        # Print the roles and statuses of each player
        print("\nPlayer Roles and Statuses:")
        for player in result['players']:
            print(f"{player.name}: {player.role}, status: {player.status}")

        print("\nAssignments per Interval:")
        for idx, assignment in enumerate(result['assignments_per_interval']):
            print(f"Interval {idx}: {assignment}")
    else:
        print(f"No suitable assignment found after {num_initial_assignments} initial assignments")

if __name__ == "__main__":
    main()