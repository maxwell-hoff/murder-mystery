from flask import Flask, request, send_from_directory, redirect, url_for

app = Flask(__name__, static_folder='../client')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/create', methods=['POST'])
def create_lobby():
    # Retrieve form data
    rooms = request.form['rooms']
    players = request.form['players']
    
    # You can process these values here and create the lobby
    print(f"Lobby created with {rooms} rooms and {players} players.")
    
    # Redirect to a confirmation page or handle the lobby creation process
    return redirect(url_for('index'))

@app.route('/join', methods=['POST'])
def join_lobby():
    code = request.form['code']
    # Handle the lobby join process here
    print(f"Joined lobby with code: {code}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)