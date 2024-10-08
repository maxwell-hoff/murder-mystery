
import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory
import redis
import json
import ssl
import certifi  # Make sure to install certifi

app = Flask(__name__, static_folder='../client')
lobbies = {}  # Dictionary to store lobbies

# Set up Redis connection with SSL parameters
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
if redis_url.startswith('redis://'):
    redis_url = redis_url.replace('redis://', 'rediss://', 1)

r = redis.Redis.from_url(
    redis_url,
    ssl_cert_reqs='required',
    ssl_ca_certs=certifi.where()
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
    players = data.get('players')
    player_name = data.get('player_name')
    # Generate a lobby code
    lobby_code = generate_lobby_code()
    # Create the lobby data
    lobby_data = {
        'rooms': rooms,
        'max_players': int(players),
        'player_names': [player_name],
        'ready_statuses': [False]  # Initialize ready statuses with False
    }
    # Store the lobby data in Redis
    r.set(f"lobby:{lobby_code}", json.dumps(lobby_data))
    print(f"Lobby {lobby_code} created with {rooms} rooms and {players} players. First player: {player_name}")
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
    lobby_code = data.get('code')
    player_name = data.get('player_name')
    lobby_key = f"lobby:{lobby_code}"
    lobby_data_json = r.get(lobby_key)
    if lobby_data_json:
        lobby_data = json.loads(lobby_data_json)
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
        lobby_data = json.loads(lobby_data_json)
        # Update the ready status for the player
        for idx, name in enumerate(lobby_data['player_names']):
            if name == player_name:
                lobby_data['ready_statuses'][idx] = True
                print(f"Player {player_name} is ready in lobby {lobby_code}.")
                break
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
        lobby_data = json.loads(lobby_data_json)
        return jsonify({
            'player_names': lobby_data['player_names'],
            'ready_statuses': lobby_data['ready_statuses']
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
