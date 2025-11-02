from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_trivia'
socketio = SocketIO(app, cors_allowed_origins="*")

# Jugadores conectados: {sid: {"name": ..., "score": ...}}
players = {}

# Control de preguntas
current_question = 0
questions = [
    {"q": "¿Qué protocolo usa un cliente web para comunicarse con un servidor?",
     "options": ["HTTP", "FTP", "SMTP", "DNS"], "a": "HTTP"},
    {"q": "¿Qué comando puedes usar en tu PC para ver puertos abiertos (conexiones/puertos en escucha)?",
     "options": ["ss -tuln", "netstat -an", "lsof -i -P -n", "Get-NetTCPConnection"], "a": "netstat -an"},
    {"q": "¿Qué puerto usa HTTP por defecto?",
     "options": ["21", "80", "443", "25"], "a": "80"},
    {"q": "¿Qué significa DNS?",
     "options": ["Domain Name System", "Data Network Server", "Digital Name Service", "Direct Network System"], "a": "Domain Name System"},
    {"q": "¿Cuál es la diferencia entre cliente y servidor?",
     "options": ["Cliente recibe datos, servidor envía servicios",
                 "Servidor envía servicios, cliente los consume",
                 "No hay diferencia",
                 "Ambos son iguales"],
     "a": "El servidor provee servicios, el cliente los consume"},
    {"q": "Si quieres bloquear el tráfico DNS en tu router, ¿qué puerto deberías bloquear?",
     "options": ["21", "53", "80", "443"], "a": "53"},
     
]

@app.route("/")
def index():
    return render_template("index.html")


@socketio.on('join')
def handle_join(data):
    global current_question
    name = data.get('name')
    if not name:
        return

    players[request.sid] = {"name": name, "score": 0}
    emit("player_list", list(players.values()), broadcast=True)

    # Si hay dos jugadores, iniciar juego
    if len(players) == 2:
        if current_question < len(questions):
            emit("start_game", questions[current_question], broadcast=True)


@socketio.on('answer')
def handle_answer(data):
    global current_question
    player = players.get(request.sid)
    if not player:
        return  # Jugador desconectado

    # Validar que haya preguntas disponibles
    if current_question >= len(questions):
        return

    # Comparar respuesta
    answer = data.get("answer", "").strip().lower()
    correct = questions[current_question]["a"].lower()
    if answer == correct:
        player["score"] += 1

    # Marcar que respondió
    if "answered" not in player:
        player["answered"] = True

    # Si todos respondieron, pasar a la siguiente pregunta
    if all("answered" in p for p in players.values()):
        for p in players.values():
            p.pop("answered", None)

        current_question += 1
        if current_question < len(questions):
            emit("next_question", questions[current_question], broadcast=True)
        else:
            emit("game_over", list(players.values()), broadcast=True)

    emit("player_list", list(players.values()), broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    players.pop(request.sid, None)
    emit("player_list", list(players.values()), broadcast=True)

    # Si no quedan jugadores, reiniciar la partida
    global current_question
    if not players:
        current_question = 0


if __name__ == "__main__":
    # Con eventlet funciona bien en Windows
    socketio.run(app, host="0.0.0.0", port=5010)
