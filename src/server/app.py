import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='../client')

lobbies = {}  # Dictionary to store lobbies

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

    # Create the lobby with initialized player names and ready statuses
    lobbies[lobby_code] = {
        'rooms': rooms,
        'max_players': int(players),
        'player_names': [player_name],
        'ready_statuses': [False]  # Initialize ready statuses with False
    }

    print(f"Lobby {lobby_code} created with {rooms} rooms and {players} players. First player: {player_name}")
    return jsonify({'message': 'Lobby created', 'lobby_code': lobby_code, 'player_names': lobbies[lobby_code]['player_names'], 'ready_statuses': lobbies[lobby_code]['ready_statuses'], 'max_players': players})

@app.route('/join', methods=['POST'])
def join_lobby():
    data = request.get_json()
    lobby_code = data.get('code')
    player_name = data.get('player_name')

    if lobby_code in lobbies:
        lobbies[lobby_code]['player_names'].append(player_name)
        lobbies[lobby_code]['ready_statuses'].append(False)  # Initialize as not ready
        print(f"Player {player_name} joined lobby {lobby_code}.")
        return jsonify({'message': f'Joined lobby {lobby_code}', 'lobby_code': lobby_code, 'player_names': lobbies[lobby_code]['player_names'], 'ready_statuses': lobbies[lobby_code]['ready_statuses'], 'max_players': lobbies[lobby_code]['max_players']})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/ready/<lobby_code>', methods=['POST'])
def set_ready_status(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')

    if lobby_code in lobbies:
        # Update the ready status for the player
        for idx, name in enumerate(lobbies[lobby_code]['player_names']):
            if name == player_name:
                lobbies[lobby_code]['ready_statuses'][idx] = True
                print(f"Player {player_name} is ready in lobby {lobby_code}.")
                break
        return jsonify({'message': 'Player ready status updated'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/lobby/<lobby_code>', methods=['GET'])
def get_lobby(lobby_code):
    if lobby_code in lobbies:
        return jsonify({
            'player_names': lobbies[lobby_code]['player_names'],
            'ready_statuses': lobbies[lobby_code]['ready_statuses']  # Return ready statuses
        })
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/check_lobby', methods=['POST'])
def check_lobby():
    data = request.get_json()
    lobby_code = data.get('code')

    if lobby_code in lobbies:
        return jsonify({'message': 'Lobby found'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
