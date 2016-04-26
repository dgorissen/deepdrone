async_mode = "threading"

if async_mode == "eventlet":
    import eventlet
    eventlet.monkey_patch()
elif async_mode == "gevent":
    from gevent import monkey, sleep
    monkey.patch_all()

from flask import Flask, render_template, Response
import zmq
import argparse
import signal
from Queue import Queue
from utils import *
import time
import threading
import cPickle
from collections import deque
from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_socketio import send, emit
import base64
import csv

app = Flask(__name__)
socketio = SocketIO(app, logger=False, binary=False, async_mode=async_mode)

# socket to receive frames on
recv_socket = None

# frame buffer (in seconds)
buffer_len = 25*5
buffer = deque(maxlen=buffer_len)

@app.route('/')
def index():
    return render_template('index.html')

def framegen():

    last = None

    # keep a csv log of what was received for post processing and vis
    ts = str(time.time())
    with open("log_" + ts + ".txt", "w") as f:
        w = None

        while True:
            # only get at roughly 25 frames per second
            time.sleep(0.04)

            try:
                data = buffer.pop()
                fn = data["fn"]
                frame = data["frame"]

                if last is None or (data["cls"] != last["cls"] or data["score"] != last["score"]):
                    d = {k : data[k] for k in ("fn", "lat", "lon", "score", "cls", "yaw")}
                    socketio.emit("meta", d)
                    last = data

                    # log to file
                    if w is None:
                        w = csv.DictWriter(f, d.keys())
                        w.writeheader()
                    w.writerow(d)
                    f.flush()

                yield (b'--frame\r\n'
                        + b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except IndexError as e:
                continue

@socketio.on('connected')
def handle_message(message):
     print "Client connected"

@app.route("/video_feed")
def video_feed():
    return Response(framegen(), mimetype='multipart/x-mixed-replace; boundary=frame')

def frame_grabber():
    while True:
        try:
            #  receive a frame and add it to the buffer
            topic, datastr = recv_socket.recv_multipart()
            data = cPickle.loads(datastr)
            #socketio.emit("frame",base64.b64encode(frame))
            buffer.appendleft(data)
        except zmq.ZMQError as e:
            time.sleep(0.2)


def setup(recv_url):
    # setup the zeromq sockets
    ctxt = zmq.Context()
    topic = "video"
    # socket to receive frames on
    recv_socket = ctxt.socket(zmq.SUB)
    recv_socket.set(zmq.SUBSCRIBE, topic)
    recv_socket.set_hwm(100)
    recv_socket.connect(recv_url)

    print("Webapp socket connecting to stream at %s" % recv_url)

    return recv_socket

if __name__ == '__main__':
    recv_url = "tcp://127.0.0.1"

    parser = argparse.ArgumentParser(description="Camera feed webapp",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-ru", dest="recv_url", help="host to pull jpeg stream from",
                        default=recv_url)

    args = parser.parse_args()
    recv_url = args.recv_url + ":5557" if istcp(args.recv_url) else args.recv_url

    recv_socket = setup(recv_url)

    t = threading.Thread(target=frame_grabber)
    t.daemon = True
    t.start()

    socketio.run(app, host='0.0.0.0', debug=True, use_reloader=False)
