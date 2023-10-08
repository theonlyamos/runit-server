import socketio
sio = socketio.Client()

@sio.event
def connect():
    print('Connected to server')

@sio.event
def connect_error():
    print('Websocket Error')

if __name__ == "__main__":
    sio.connect('http://localhost:9000',transports=['websocket'])