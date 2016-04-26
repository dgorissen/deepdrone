import cv2
import zmq
import argparse
import signal
from utils import *
from drone import Drone
import datetime
import pandas as pd
import time
import cPickle
import math
import random

def run(send_url, recv_url, results_url, interval=50, drone=None, debug=True):

    # open the video stream
    vidFile = cv2.VideoCapture(0)

    if vidFile and vidFile.isOpened():
        print("Video stream opened")
    else:
        print("Error reading video input")
        exit(-1)

    orig_width = int(vidFile.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    orig_height = int(vidFile.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))

    # keep the frame small
    width = 600
    height = 450

    # setup the zeromq sockets
    ctxt = zmq.Context()
    # socket to post frames to (the classification worker)
    send_socket = ctxt.socket(zmq.PUSH)
    # socket to receive classified results on
    recv_socket = ctxt.socket(zmq.PULL)
    # socket to post classified frames on
    results_socket = ctxt.socket(zmq.PUB)

    send_socket.set_hwm(1)
    results_socket.set_hwm(100)
    results_topic = "video"

    send_socket.bind(send_url)
    recv_socket.connect(recv_url)
    results_socket.bind(results_url)

    print(("Videograbber running..\n  - Pushing frames from %s\n" +
           "  - Pulling results back from classifier at %s\n" +
           "  - Pushing final jpeg stream from %s") % (send_url, recv_url, results_url))

    meta = None
    fn = None
    frame_number = 0
    pos = None
    attitude = None

    # TODO: use a dict to ensure a changable reference, something nicer?
    running = {"running": True}

    # allow to stop  gracefully
    def signal_handler(signal, frame):
        print("Caught CTRL-C, stopping..")
        running["running"] = False
    signal.signal(signal.SIGINT, signal_handler)

    while running["running"] and vidFile.isOpened():

        # read a frame from the input
        ret, frame = vidFile.read()

        if frame is None:
            continue

        # resize it
        frame = cv2.resize(frame, (width, height))
        frame_number += 1

        # print("Captured frame ", frame_number)

        if frame_number % interval == 0:
            try:
                # send frame off to worker process to classify
                send_socket.send_pyobj((frame_number, frame), zmq.NOBLOCK)
            except zmq.ZMQError as e:
                print("Failed to send frame to classifier:", e)

        # try to receive a result
        try:
            fn, meta = recv_socket.recv_pyobj(zmq.NOBLOCK)
            print(" Got classification for frame ", fn, "(" + str(frame_number - fn) + " late): ",
                  meta[0][0] + ': ' + "%.2f" % (float(meta[0][1])*100))
        except zmq.ZMQError as e:
            pass

        if meta:
            # overlay the top three prediction
            cv2.rectangle(frame, (2, height - 100), (300, height-2), (250,250,250), thickness=-1)
            cv2.putText(frame, ("Frame #: %s | %s" % (frame_number, fn)),
                        (4, (height - 80)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, ("1. " + meta[0][0] + ': ' + "%.2f" % (float(meta[0][1])*100) + "%"),
                        (4, (height - 60)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, ("2. " + meta[1][0] + ': ' + "%.2f" % (float(meta[1][1])*100) + "%"),
                        (4, (height - 40)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, ("3. " + meta[2][0] + ': ' + "%.2f" % (float(meta[2][1])*100) + "%"),
                        (4, (height - 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            topclass = meta[0][0], float(meta[0][1])*100
        else:
            topclass = "", 0


        # publish the final frame (as a jpeg) to anybody who is listening
        ret, jpeg = cv2.imencode('.jpg', frame)

        try:
            if drone:
                pos = drone.get_position()
            else:
                pos = {}

            # ensure all keys are alwyas present
            data = {
                "ts": time.time(),
                "fn": frame_number,
                "cls": topclass[0],
                "score": topclass[1],
                "frame": jpeg.getbytes() if getattr(jpeg, 'getbytes', None) else jpeg.tostring(),
                "lat": 0,
                "lon": 0,
                "alt": 0,
                "pitch": 0,
                "roll": 0,
                "yaw": 0,
                "groundspeed": 0,
                "eph": 0,
                "epv": 0,
                "fix_type": 0,
                "nsat": 0
            }

            data.update(pos)

            if drone is None:
                data["lat"] = 50.8749 + random.random()/1000;
                data["lon"] = -1.328 + random.random()/1000;
                data["yaw"] = random.random();

            datastr = cPickle.dumps(data, 2)

            results_socket.send_multipart([results_topic, datastr], zmq.NOBLOCK)
        except zmq.ZMQError as e:
            pass

        # shows the frame in a window
        if debug:
            cv2.waitKey(10)
            cv2.imshow("Object Classifier", frame)

    vidFile.release()
    ctxt.destroy()


if __name__ == '__main__':
    local = "tcp://*"
    vc = "tcp://127.0.0.1"

    parser = argparse.ArgumentParser(description="Camera feed grabber",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-local", dest="local", help="local transport & ip to push from", default=local)

    parser.add_argument("-vc", dest="vc", help="video classifier host to pull from", default=vc)

    parser.add_argument("-i", dest="interval", type=int, help="Classify every i frames", default=50)

    parser.add_argument("-drone", dest="drone", action="store_true",
                        help="Connect to drone", default=False)

    parser.add_argument("-d", dest="debug", action="store_true",
                        help="show debug window", default=False)

    args = parser.parse_args()
    send_url = args.local + ":5555" if istcp(args.local) else args.local
    recv_url = args.vc + ":5556" if istcp(args.vc) else args.vc
    results_url = args.local + ":5557" if istcp(args.local) else args.local


    if args.drone:
        drone = Drone()
        drone.setup()
    else:
        drone = None

    run(send_url, recv_url, results_url, drone=drone, interval=args.interval, debug=args.debug)

    cv2.destroyAllWindows()
