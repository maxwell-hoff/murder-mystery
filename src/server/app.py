import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='../client')

lobbies = {}  # Dictionary to store lobbies

def generate_lobby_code():
    """Generates a unique 6-character lobby code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/create', methods=['POST'])
def create_lobby():
    data = request.get_json()
    rooms = data.get('rooms')
    players = int(data.get('players'))  # Ensure it's an integer
    player_name = data.get('player_name')

    # Generate a lobby code
    lobby_code = generate_lobby_code()

    # Create the lobby
    lobbies[lobby_code] = {
        'rooms': rooms,
        'players': players,
        'player_names': [player_name]
    }

    print(f"Lobby {lobby_code} created with {rooms} rooms and {players} players. First player: {player_name}")
    return jsonify({
        'message': 'Lobby created',
        'lobby_code': lobby_code,
        'player_names': lobbies[lobby_code]['player_names'],
        'max_players': lobbies[lobby_code]['players']
    })

@app.route('/join', methods=['POST'])
def join_lobby():
    data = request.get_json()
    lobby_code = data.get('code')
    player_name = data.get('player_name')

    if lobby_code in lobbies:
        lobby = lobbies[lobby_code]
        if len(lobby['player_names']) < lobby['players']:
            lobby['player_names'].append(player_name)
            print(f"Player {player_name} joined lobby {lobby_code}.")
            return jsonify({
                'message': f'Joined lobby {lobby_code}',
                'lobby_code': lobby_code,
                'player_names': lobby['player_names'],
                'max_players': lobby['players']
            })
        else:
            return jsonify({'error': 'Lobby is full'}), 400
    else:
        return jsonify({'error': 'Lobby not found'}), 404

@app.route('/lobby/<lobby_code>', methods=['GET'])
def get_lobby(lobby_code):
    if lobby_code in lobbies:
        lobby = lobbies[lobby_code]
        return jsonify({
            'player_names': lobby['player_names'],
            'max_players': lobby['players']
        })
    else:
        return jsonify({'error': 'Lobby not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)