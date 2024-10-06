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
#     code = generate_code()
#     lobbies[code] = {"players": []}
#     return redirect(url_for('lobby', code=code))

@app.route('/create', methods=['POST'])
def create_lobby():
    # Retrieve form data
    rooms = request.form['rooms']
    players = request.form['players']
    
    # You can process these values here and create the lobby
    print(f"Lobby created with {rooms} rooms and {players} players.")
    
    # Redirect to a confirmation page or handle the lobby creation process
    return redirect(url_for('index'))

@app.route('/lobby/<code>')
def lobby(code):
    if code in lobbies:
        return render_template('lobby.html', code=code)
    else:
        return "Lobby not found", 404

@app.route('/join', methods=['POST'])
def join_lobby():
    code = request.form['code']
    if code in lobbies:
        return redirect(url_for('lobby', code=code))
    else:
        return "Invalid code", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)