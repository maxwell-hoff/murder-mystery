import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Global dictionary to store lobby data
lobbies = {}

# Function to generate lobby code
def generate_lobby_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Route to create a new lobby
@app.route('/create', methods=['POST'])
def create_lobby():
    data = request.get_json()
    lobby_code = generate_lobby_code()
    rooms = data.get('rooms')
    max_players = int(data.get('players'))
    player_name = data.get('player_name')

    # Initialize the lobby with the first player and their status
    lobbies[lobby_code] = {
        'rooms': rooms,
        'max_players': max_players,
        'player_names': [player_name],
        'ready_statuses': [False]  # Player is not ready initially
    }

    return jsonify({
        'message': 'Lobby created',
        'lobby_code': lobby_code,
        'player_names': lobbies[lobby_code]['player_names'],
        'ready_statuses': lobbies[lobby_code]['ready_statuses'],
        'max_players': max_players
    })

# Route to join an existing lobby
@app.route('/join', methods=['POST'])
def join_lobby():
    data = request.get_json()
    lobby_code = data.get('code')
    player_name = data.get('player_name')

    if lobby_code in lobbies:
        lobby = lobbies[lobby_code]
        if len(lobby['player_names']) < lobby['max_players']:
            lobby['player_names'].append(player_name)
            lobby['ready_statuses'].append(False)  # New player is not ready initially
            return jsonify({
                'message': 'Joined lobby',
                'lobby_code': lobby_code,
                'player_names': lobby['player_names'],
                'ready_statuses': lobby['ready_statuses'],
                'max_players': lobby['max_players']
            })
        else:
            return jsonify({'error': 'Lobby is full'}), 403
    else:
        return jsonify({'error': 'Lobby not found'}), 404

# Route to get the current status of a lobby (polling)
@app.route('/lobby/<lobby_code>', methods=['GET'])
def get_lobby(lobby_code):
    if lobby_code in lobbies:
        return jsonify({
            'player_names': lobbies[lobby_code]['player_names'],
            'ready_statuses': lobbies[lobby_code]['ready_statuses']
        })
    else:
        return jsonify({'error': 'Lobby not found'}), 404

# Route to update the ready status of a player
@app.route('/ready/<lobby_code>', methods=['POST'])
def set_ready_status(lobby_code):
    data = request.get_json()
    player_name = data.get('player_name')

    if lobby_code in lobbies:
        lobby = lobbies[lobby_code]
        for idx, name in enumerate(lobby['player_names']):
            if name == player_name:
                lobby['ready_statuses'][idx] = True
                break
        return jsonify({'message': 'Player ready status updated'})
    else:
        return jsonify({'error': 'Lobby not found'}), 404

# Start the Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)