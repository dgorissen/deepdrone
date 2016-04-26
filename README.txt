The codebase consists of 3 parts that communicate over ZeroMQ:

1. videograbber.py:
    a) grabs a frame from the webcam, sends it to the classifier
    b) sends every nth frame to the classifier
    c) if there is a classified result, overlay it on the then current frame
    d) publish full results as jpeg stream

2. classifier.py:
    a) get a frame to be classified from the video grabber
    b) classify with caffe
    c) return result

3) webapp.py: flask webapp, running on port 5000, that shows the videograbber jpeg stream feed

To run locally over ipc, simply run each in a separate terminal (python <file>) and then open localhost:5000
in a browser.

See python <file> -h for more options
