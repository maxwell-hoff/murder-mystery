from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import random
import string
import os

app = Flask(__name__, static_folder='../client')

lobbies = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')
    # return render_template('index.html')

# @app.route('/create', methods=['POST'])
# def create_lobby():
#     # Retrieve form data
#     rooms = request.form['rooms']
#     players = request.form['players']
    
#     # You can process these values here and create the lobby
#     print(f"Lobby created with {rooms} rooms and {players} players.")
    
#     # Redirect to a confirmation page or handle the lobby creation process
#     return redirect(url_for('index'))

# @app.route('/create', methods=['POST'])
# def create_lobby():
#     # Get the JSON data from the request
#     data = request.get_json()
#     rooms = data.get('rooms')
#     players = data.get('players')
#     player_name = data.get('player_name')

#     # Simulate lobby creation (store player and lobby info)
#     print(f"Creating lobby with {rooms} rooms and {players} players. First player: {player_name}")

#     # For now, just return a success message
#     return jsonify({'message': 'Lobby created successfully', 'player': player_name})

@app.route('/lobby/<code>')
def lobby(code):
    if code in lobbies:
        return render_template('lobby.html', code=code)
    else:
        return "Lobby not found", 404

# @app.route('/join', methods=['POST'])
# def join_lobby():
#     code = request.form['code']
#     if code in lobbies:
#         return redirect(url_for('lobby', code=code))
#     else:
#         return "Invalid code", 404

@app.route('/create', methods=['POST'])
def create_lobby():
    data = request.get_json()
    rooms = data.get('rooms')
    players = data.get('players')
    player_name = data.get('player_name')

    # Simulate lobby creation
    print(f"Lobby created with {rooms} rooms and {players} players. First player: {player_name}")
    return jsonify({'message': 'Lobby created', 'player': player_name})

@app.route('/join', methods=['POST'])
def join_lobby():
    data = request.get_json()
    code = data.get('code')
    player_name = data.get('player_name')

    # Simulate joining a lobby by code
    print(f"Player {player_name} joined lobby with code {code}.")
    return jsonify({'message': f'Joined lobby {code}', 'player': player_name})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)