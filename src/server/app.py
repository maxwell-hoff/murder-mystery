import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory
import redis
import json
import game_logic
import time

app = Flask(__name__, static_folder='../client', static_url_path='/static')

# Set up Redis connection with SSL parameters
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
if redis_url.startswith('redis://'):
    redis_url = redis_url.replace('redis://', 'rediss://', 1)

r = redis.Redis.from_url(
    redis_url,
    ssl_cert_reqs=None
)

def generate_lobby_code():
    """Generates a unique 6-character lobby code."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/create', methods=['POST'])
def create_lobby():
    data = request.get_json()
    rooms = data.get('rooms')
    players = int(data.get('players'))
    player_name = data.get('player_name')
    duration = data.get('duration')

    # Validate minimum number of players
    if players < 4:
        return jsonify({'error': 'The minimum number of players is 4.'}), 400

    # Validate number of rooms
    if not (3 <= len(rooms) <= 10):
        return jsonify({'error': 'The number of rooms must be between 3 and 9.'}), 400

    # Generate a lobby code
    lobby_code = generate_lobby_code()
    # Create the lobby data
    lobby_data = {
        'rooms': rooms,
        'max_players': players,
        'player_names': [player_name],
        'ready_statuses': [False],
        'game_started': False,
        'duration': int(duration),
        'game_start_time': None,
        'activity_log': []
    }
    # Store the lobby data in Redis
    r.set(f"lobby:{lobby_code}", json.dumps(lobby_data))
    print(f"Lobby {lobby_code} created with rooms {rooms}, {players} players, and duration {duration} minutes. First player: {player_name}")
    return jsonify({
        'message': 'Lobby created',
        'lobby_code': lobby_code,
        'player_names': lobby_data['player_names'],
        'ready_statuses': lobby_data['ready_statuses'],
        'max_players': lobby_data['max_players']
    })


@app.route('/join', methods=['POST'])
def join_lobby():
    data = request.get_json()
    print('Join request data:', data)
    lobby_code = data.get('code')
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        # Decode the bytes to string
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        if lobby_data.get('game_started'):
            return jsonify({'error': 'Game has already started'}), 400
        if len(lobby_data['player_names']) < lobby_data['max_players']:
            lobby_data['player_names'].append(player_name)
            lobby_data['ready_statuses'].append(False)  # Initialize as not ready
            # Update the lobby data in Redis
            r.set(lobby_key, json.dumps(lobby_data))
            print(f"Player {player_name} joined lobby {lobby_code}.")
            return jsonify({
                'message': f'Joined lobby {lobby_code}',
                'lobby_code': lobby_code,
                'player_names': lobby_data['player_names'],
                'ready_statuses': lobby_data['ready_statuses'],
                'max_players': lobby_data['max_players']
            })
        else:
            return jsonify({'error': 'Lobby is full'}), 400
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/ready/<lobby_code>', methods=['POST'])
def set_ready_status(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        # Update the ready status for the player
        for idx, name in enumerate(lobby_data['player_names']):
            if name == player_name:
                lobby_data['ready_statuses'][idx] = True
                print(f"Player {player_name} is ready in lobby {lobby_code}.")
                break
        # Check if all players are ready
        if all(lobby_data['ready_statuses']) and len(lobby_data['player_names']) == lobby_data['max_players']:
            # Ensure minimum players have joined
            if len(lobby_data['player_names']) < 4:
                return jsonify({'error': 'At least 4 players are required to start the game.'}), 400
            # Assign roles using game_logic
            roles = game_logic.assign_roles(lobby_data['player_names'])
            lobby_data['roles'] = roles  # Store roles in lobby data
            # Assign rooms using game_logic
            rooms = lobby_data['rooms']
            room_assignments = game_logic.assign_rooms(lobby_data['player_names'], rooms)
            lobby_data['room_assignments'] = room_assignments  # Store room assignments
            # Record the game start time
            lobby_data['game_start_time'] = int(round(time.time() * 1000))
            # Initialize meeting state and player statuses
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None
            lobby_data['player_statuses'] = {player: 'alive' for player in lobby_data['player_names']}
            lobby_data['game_started'] = True
            print(f"All players are ready. Game starting in lobby {lobby_code}. Roles and rooms assigned.")
        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))
        return jsonify({'message': 'Player ready status updated'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/lobby/<lobby_code>', methods=['GET'])
def get_lobby(lobby_code):
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        # Decode the bytes to string
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        return jsonify({
            'player_names': lobby_data['player_names'],
            'ready_statuses': lobby_data['ready_statuses'],
            'game_started': lobby_data['game_started'],
            'duration': lobby_data.get('duration'),
            'game_start_time': lobby_data.get('game_start_time'),
            'meeting_active': lobby_data.get('meeting_active', False),
            'meeting_start_time': lobby_data.get('meeting_start_time'),
            'has_voted': lobby_data.get('has_voted', {}),
            'player_statuses': lobby_data.get('player_statuses', {}),
            'game_over': lobby_data.get('game_over', False),
            'winner': lobby_data.get('winner'),
            'game_over_message': lobby_data.get('game_over_message')  # Include the message
        })
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/check_lobby', methods=['POST'])
def check_lobby():
    data = request.get_json()
    lobby_code = data.get('code')
    lobby_key = f"lobby:{lobby_code}"
    if r.exists(lobby_key):
        return jsonify({'message': 'Lobby found'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/get_role/<lobby_code>', methods=['POST'])
def get_role(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        if lobby_data.get('roles'):
            role = lobby_data['roles'].get(player_name)
            if role:
                return jsonify({'role': role})
            else:
                return jsonify({'error': 'Player not found in lobby'}), 404
        else:
            return jsonify({'error': 'Roles not assigned yet'}), 400
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/get_room/<lobby_code>', methods=['POST'])
def get_room(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        if lobby_data.get('room_assignments'):
            room = lobby_data['room_assignments'].get(player_name)
            if room:
                return jsonify({'room': room})
            else:
                return jsonify({'error': 'Player not found in lobby'}), 404
        else:
            return jsonify({'error': 'Rooms not assigned yet'}), 400
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/call_meeting/<lobby_code>', methods=['POST'])
def call_meeting(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if not lobby_data.get('game_started'):
            return jsonify({'error': 'Game has not started yet'}), 400

        if lobby_data.get('meeting_active'):
            return jsonify({'error': 'A meeting is already in progress'}), 400

        # After starting the meeting
        # Start the meeting
        lobby_data['meeting_active'] = True
        lobby_data['meeting_start_time'] = int(round(time.time() * 1000))

        # Initialize votes and voting status
        lobby_data['votes'] = {}  # Reset votes
        lobby_data['has_voted'] = {}  # Track who has voted or skipped
        for player in lobby_data['player_names']:
            lobby_data['has_voted'][player] = False

        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))

        print(f"Player {player_name} called a meeting in lobby {lobby_code}.")

        return jsonify({'message': 'Meeting started', 'meeting_start_time': lobby_data['meeting_start_time']})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/submit_vote/<lobby_code>', methods=['POST'])
def submit_vote(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    voted_player = data.get('voted_player')
    lobby_key = f"lobby:{lobby_code}"

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if not lobby_data.get('meeting_active'):
            return jsonify({'error': 'No meeting in progress'}), 400

        if lobby_data['has_voted'].get(player_name):
            return jsonify({'error': 'Player has already voted'}), 400

        # Check if player is alive
        if lobby_data['player_statuses'].get(player_name) != 'alive':
            return jsonify({'error': 'Dead players cannot vote'}), 400

        # Record the vote
        lobby_data['votes'][player_name] = voted_player
        lobby_data['has_voted'][player_name] = True

        # Check if all alive players have voted or skipped
        alive_players = [player for player, status in lobby_data['player_statuses'].items() if status == 'alive']
        if all(lobby_data['has_voted'].get(player, False) for player in alive_players):
            # End the meeting
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None
            # Process votes
            process_votes(lobby_data)
            print(f"All players have voted or skipped in lobby {lobby_code}.")

        # Update the lobby data in Redis (moved outside the if block)
        r.set(lobby_key, json.dumps(lobby_data))

        return jsonify({'message': 'Vote submitted'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/skip_vote/<lobby_code>', methods=['POST'])
def skip_vote(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if not lobby_data.get('meeting_active'):
            return jsonify({'error': 'No meeting in progress'}), 400

        if lobby_data['has_voted'].get(player_name):
            return jsonify({'error': 'Player has already voted or skipped'}), 400

        # Check if player is alive
        if lobby_data['player_statuses'].get(player_name) != 'alive':
            return jsonify({'error': 'Dead players cannot vote'}), 400

        # Record the skip
        lobby_data['votes'][player_name] = 'skip'
        lobby_data['has_voted'][player_name] = True

        # Check if all alive players have voted or skipped
        alive_players = [player for player, status in lobby_data['player_statuses'].items() if status == 'alive']
        if all(lobby_data['has_voted'].get(player, False) for player in alive_players):
            # End the meeting
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None
            # Process votes
            process_votes(lobby_data)
            print(f"All players have voted or skipped in lobby {lobby_code}.")

        # Update the lobby data in Redis (moved outside the if block)
        r.set(lobby_key, json.dumps(lobby_data))

        return jsonify({'message': 'Vote submitted'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/activity_log/<lobby_code>', methods=['GET'])
def get_activity_log(lobby_code):
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        activity_log = lobby_data.get('activity_log', [])
        return jsonify({'activity_log': activity_log})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/meeting_expired/<lobby_code>', methods=['POST'])
def meeting_expired(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')  # Not strictly necessary here
    lobby_key = f"lobby:{lobby_code}"

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if not lobby_data.get('meeting_active'):
            return jsonify({'error': 'No meeting in progress'}), 400

        # For all alive players who haven't voted, mark their vote as 'skip'
        alive_players = [player for player, status in lobby_data['player_statuses'].items() if status == 'alive']
        for player in alive_players:
            if not lobby_data['has_voted'].get(player):
                lobby_data['votes'][player] = 'skip'
                lobby_data['has_voted'][player] = True

        # End the meeting
        lobby_data['meeting_active'] = False
        lobby_data['meeting_start_time'] = None

        # Process votes
        process_votes(lobby_data)
        print(f"Meeting timer expired. Votes processed in lobby {lobby_code}.")

        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))

        return jsonify({'message': 'Meeting expired and votes processed'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/game_time_expired/<lobby_code>', methods=['POST'])
def game_time_expired(lobby_code):
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)

    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if lobby_data.get('game_over'):
            return jsonify({'message': 'Game already over'})

        # Set game over and impostor wins
        lobby_data['game_over'] = True
        lobby_data['winner'] = 'impostor'
        message = "Game time has run out. Impostor wins!"
        lobby_data['game_over_message'] = message  # Store the message
        print(message)
        append_activity_log(lobby_data, message)

        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))

        return jsonify({'message': 'Game time expired, impostor wins'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/leave_lobby/<lobby_code>', methods=['POST'])
def leave_lobby(lobby_code):
    print(f"leave_lobby called with lobby_code: {lobby_code}")
    data = request.get_json()
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"
    print(f"Player name received: {player_name}")

    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        if player_name in lobby_data['player_names']:
            idx = lobby_data['player_names'].index(player_name)
            # Remove the player from the player_names and ready_statuses
            lobby_data['player_names'].pop(idx)
            lobby_data['ready_statuses'].pop(idx)

            # Remove player from player_statuses if game has started
            if lobby_data.get('player_statuses'):
                lobby_data['player_statuses'].pop(player_name, None)
            # Remove player role if assigned
            if lobby_data.get('roles'):
                lobby_data['roles'].pop(player_name, None)
            # Remove room assignment
            if lobby_data.get('room_assignments'):
                lobby_data['room_assignments'].pop(player_name, None)
            # If the game hasn't started yet, check if lobby is empty
            if not lobby_data['player_names']:
                # Delete the lobby
                r.delete(lobby_key)
                return jsonify({'message': 'Player left and lobby deleted because it was empty'})
            else:
                # Update the lobby data in Redis
                r.set(lobby_key, json.dumps(lobby_data))
                return jsonify({'message': 'Player left the lobby'})
        else:
            return jsonify({'error': 'Player not found in lobby'}), 404
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/reset_lobby/<lobby_code>', methods=['POST'])
def reset_lobby(lobby_code):
    print(f"reset_lobby called with lobby_code: {lobby_code}")
    data = request.get_json()
    player_name = data.get('player_name')
    print(f"Player name received: {player_name}")

    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))

        # Reset game-specific data while keeping the player list intact
        lobby_data['ready_statuses'] = [False] * len(lobby_data['player_names'])
        lobby_data['game_started'] = False
        lobby_data['game_start_time'] = None
        lobby_data['meeting_active'] = False
        lobby_data['meeting_start_time'] = None
        lobby_data['player_statuses'] = {}
        lobby_data['roles'] = {}
        lobby_data['room_assignments'] = {}
        lobby_data['activity_log'] = []
        lobby_data['votes'] = {}
        lobby_data['has_voted'] = {}
        lobby_data['game_over'] = False
        lobby_data['winner'] = None
        lobby_data['game_over_message'] = None

        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))
        return jsonify({'message': 'Lobby has been reset'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

def process_votes(lobby_data):
    votes = lobby_data['votes']
    player_statuses = lobby_data['player_statuses']
    # game_start_time = lobby_data.get('game_start_time')
    # game_duration_minutes = lobby_data.get('duration')
    # game_duration_ms = game_duration_minutes * 60 * 1000  # Convert minutes to milliseconds

    # Only consider votes from alive players
    alive_players = [player for player, status in player_statuses.items() if status == 'alive']
    alive_votes = {player: vote for player, vote in votes.items() if player_statuses[player] == 'alive'}
    
    # Count votes for each player
    vote_counts = {}
    for vote in alive_votes.values():
        if vote != 'skip':
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

    # Initialize message
    message = ""

    if not vote_counts:
        # No votes cast
        message = "No votes were cast."
        print(message)
    else:
        # Find the player(s) with the highest votes
        max_votes = max(vote_counts.values())
        players_with_max_votes = [player for player, count in vote_counts.items() if count == max_votes]
        
        # Check for tie
        if len(players_with_max_votes) > 1:
            message = "Tie detected. No one is eliminated."
            print(message)
        else:
            # Check if majority is achieved
            if max_votes >= (len(alive_players) // 2) + 1:
                # Eliminate the player
                eliminated_player = players_with_max_votes[0]
                player_statuses[eliminated_player] = 'dead'
                message = f"Player {eliminated_player} has been eliminated."
                print(message)
            else:
                message = "No majority. No one is eliminated."
                print(message)

    # Calculate the remaining game time
    # current_time_ms = int(round(time.time() * 1000))
    # elapsed_time_ms = current_time_ms - game_start_time
    # remaining_time_ms = game_duration_ms - elapsed_time_ms

    # Ensure that the remaining time is not negative
    # remaining_time_ms = max(0, remaining_time_ms)

    # remaining_time_str = format_time_ms(remaining_time_ms)

    # # Append the message and time to the activity log
    # activity_entry = {
    #     'time': remaining_time_str,
    #     'message': message
    # }
    # lobby_data['activity_log'].append(activity_entry)

    # Append the message and time to the activity log
    append_activity_log(lobby_data, message)

    # Check for win conditions after processing votes
    check_win_conditions(lobby_data)

def format_time_ms(milliseconds):
    seconds = (milliseconds // 1000) % 60
    minutes = (milliseconds // (1000 * 60)) % 60
    formatted_time = f"{minutes}:{seconds:02}"
    return formatted_time

def append_activity_log(lobby_data, message):
    # Calculate the remaining game time
    game_start_time = lobby_data.get('game_start_time')
    game_duration_minutes = lobby_data.get('duration')
    game_duration_ms = game_duration_minutes * 60 * 1000  # Convert minutes to milliseconds
    current_time_ms = int(round(time.time() * 1000))
    elapsed_time_ms = current_time_ms - game_start_time
    remaining_time_ms = game_duration_ms - elapsed_time_ms

    # Ensure that the remaining time is not negative
    remaining_time_ms = max(0, remaining_time_ms)

    remaining_time_str = format_time_ms(remaining_time_ms)

    # Append the message and time to the activity log
    activity_entry = {
        'time': remaining_time_str,
        'message': message
    }
    lobby_data['activity_log'].append(activity_entry)


def check_win_conditions(lobby_data):
    player_statuses = lobby_data['player_statuses']
    roles = lobby_data['roles']
    alive_players = [player for player, status in player_statuses.items() if status == 'alive']
    impostor = next((player for player, role in roles.items() if role == 'impostor'), None)

    # Condition 1: If the impostor is eliminated, crew members win
    if player_statuses.get(impostor) == 'dead':
        lobby_data['game_over'] = True
        lobby_data['winner'] = 'crew'
        message = "The impostor has been eliminated. Crew members win!"
        lobby_data['game_over_message'] = message  # Store the message
        print(message)
        append_activity_log(lobby_data, message)
        return

    # Condition 2: If the game gets down to 2 players with one being the impostor, impostor wins
    if len(alive_players) == 2 and impostor in alive_players:
        lobby_data['game_over'] = True
        lobby_data['winner'] = 'impostor'
        message = "Only two players remain, and the impostor is among them. Impostor wins!"
        lobby_data['game_over_message'] = message  # Store the message
        print(message)
        append_activity_log(lobby_data, message)
        return

    # Condition 3: If the game time runs out, impostor wins
    # This condition will be checked separately in the timer logic

    # No win condition met yet
    lobby_data['game_over'] = False
    lobby_data['game_over_message'] = None  # Clear any previous message

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)