import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory
import redis
import json
import game_logic
import time

app = Flask(__name__, static_folder='../client')

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
    rooms = data.get('rooms')  # Now expecting a list of room names
    players = data.get('players')
    player_name = data.get('player_name')
    duration = data.get('duration')  # Get the game duration

    # Generate a lobby code
    lobby_code = generate_lobby_code()
    # Create the lobby data
    lobby_data = {
        'rooms': rooms,  # Store the room names list
        'max_players': int(players),
        'player_names': [player_name],
        'ready_statuses': [False],  # Initialize ready statuses with False
        'game_started': False,      # New flag to indicate if the game has started
        'duration': int(duration),  # Store the game duration in minutes
        'game_start_time': None     # Will store the game start timestamp
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
        # Decode the bytes to string
        lobby_data = json.loads(lobby_data_json.decode('utf-8'))
        # Update the ready status for the player
        for idx, name in enumerate(lobby_data['player_names']):
            if name == player_name:
                lobby_data['ready_statuses'][idx] = True
                print(f"Player {player_name} is ready in lobby {lobby_code}.")
                break
        # Check if all players are ready
        if all(lobby_data['ready_statuses']) and len(lobby_data['player_names']) == lobby_data['max_players']:
            # Assign roles using game_logic
            roles = game_logic.assign_roles(lobby_data['player_names'])
            lobby_data['roles'] = roles  # Store roles in lobby data

            # Assign rooms using game_logic
            rooms = lobby_data['rooms']
            room_assignments = game_logic.assign_rooms(lobby_data['player_names'], rooms)
            lobby_data['room_assignments'] = room_assignments  # Store room assignments

            # Record the game start time in milliseconds since epoch
            lobby_data['game_start_time'] = int(round(time.time() * 1000))

            # Initialize meeting state
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None

            # Update the lobby data in Redis
            r.set(lobby_key, json.dumps(lobby_data))

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
            'has_voted': lobby_data.get('has_voted', {})
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

        # Record the vote
        lobby_data['votes'][player_name] = voted_player
        lobby_data['has_voted'][player_name] = True

        # Check if all players have voted or skipped
        if all(lobby_data['has_voted'].values()):
            # End the meeting
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None
            # Optionally, process votes here
            print(f"All players have voted or skipped in lobby {lobby_code}.")

        # Update the lobby data in Redis
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

        # Record the skip
        lobby_data['votes'][player_name] = 'skip'
        lobby_data['has_voted'][player_name] = True

        # Check if all players have voted or skipped
        if all(lobby_data['has_voted'].values()):
            # End the meeting
            lobby_data['meeting_active'] = False
            lobby_data['meeting_start_time'] = None
            # Optionally, process votes here
            print(f"All players have voted or skipped in lobby {lobby_code}.")

        # Update the lobby data in Redis
        r.set(lobby_key, json.dumps(lobby_data))

        return jsonify({'message': 'Vote submitted'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)