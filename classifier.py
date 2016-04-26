import numpy as np
import pandas as pd
import skimage.io
import zmq
import argparse
import signal
import time
import os
from utils import *

# turn off log output when loading net
os.environ['GLOG_minloglevel'] = '2'

import caffe


# helper method to change image format from openCV to Caffe for classification
def preprocessFrame(image):
    img = skimage.img_as_float(image[:,:,[2,1,0]]).astype(np.float32)
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
        if color:
            img = np.tile(img, (1, 1, 3))
    elif img.shape[2] == 4:
        img = img[:, :, :3]
    return img


def load_model(model="bvlc_reference_caffenet"):
    # Path to caffe install
    # caffe_root = '~/deep-learning/caffe'
    caffe_root = "~/git/caffe"
    caffe_root = os.path.expanduser(caffe_root)

    # Set the right paths to your model definition file, pretrained model weights
    # and labels file. This example uses the pre-trained ILSVRC12 image classifier
    # CaffeNet model.
    # You can download it by following the installation instructions steps under
    # http://caffe.berkeleyvision.org/model_zoo.htmli
    MODEL_FILE = caffe_root + ('/models/%s/deploy.prototxt' % model)
    PRETRAINED = caffe_root + ('/models/%s/%s.caffemodel' % (model, model))
    LABELS_FILE = caffe_root + '/data/ilsvrc12/synset_words.txt'
    MEAN_FILE = caffe_root + "/python/caffe/imagenet/ilsvrc_2012_mean.npy"

    # load the network via the cafe.Classifier() method
    net = caffe.Classifier(MODEL_FILE, PRETRAINED,
                           mean=np.load(MEAN_FILE).mean(1).mean(1),
                           channel_swap=(2, 1, 0),
                           raw_scale=255,
                           image_dims=(256, 256))

    # get labels from according file
    labels = []
    with open(LABELS_FILE) as f:
        labels = pd.DataFrame([
            {
                'synset_id': l.strip().split(' ')[0],
                'name': ' '.join(l.strip().split(' ')[1:]).split(',')[0]
            }
            for l in f.readlines()])
        labels = labels.sort_values('synset_id')['name'].values

    return net, labels

# Worker function that takes a frame to be classified from an input queue and
# returns the classification result
def classifier(recv_url, send_url, gpu=False):

    if gpu:
        caffe.set_mode_gpu()
        print "Running in GPU mode"
    else:
        caffe.set_mode_cpu()
        print "Running in CPU mode"

    net, labels = load_model()

    print(("Classifier worker started..\n  - Pulling frames from videograbber at %s\n" +
          "  - Pushing results back from %s") % (recv_url, send_url))

    # setup the zeromq sockets
    ctxt = zmq.Context()
    # socket to receive frames to be classified on
    recv_socket = ctxt.socket(zmq.PULL)
    # socket to post classifications on
    send_socket = ctxt.socket(zmq.PUSH)

    # recv_socket.set_hwm(3)
    # send_socket.set_hwm(3)
    recv_socket.connect(recv_url)
    send_socket.bind(send_url)

    # TODO: use a dict to ensure a changable reference, something nicer?
    running = {"running": True}

    # allow to stop  gracefully
    def signal_handler(signal, frame):
        print("Caught CTRL-C, stopping..")
        running["running"] = False
    signal.signal(signal.SIGINT, signal_handler)

    while running["running"]:
        # try to get the next frame from the queue
        fn, frame = None, None
        try:
            # do it the noblocking way so we can always ctrl-c
            # out of the while loop even if the videograbber is
            # dead
            fn, frame = recv_socket.recv_pyobj(zmq.NOBLOCK)
        except zmq.ZMQError as e:
            time.sleep(0.1)
            continue

        # turn it into a format caffee likes
        image = preprocessFrame(frame)
        # perform the actual prediction
        predictions = net.predict([image]).flatten()
        # get indices of the top 3 classes with the highest probability
        indices = (-predictions).argsort()[:3]
        # and the corresponding labels of the top results
        scores = labels[indices]

        # create a 2-dimensional array containing the meta-information
        # example: [('monitor', '0.41708'), ('screen', '0.28103'), ...]

        # predictions[i] represents the probability of the i-th best result
        meta = [(p, '%.5f' % predictions[i]) for i, p in zip(indices, scores)]

        # put the result on the output queue
        try:
            send_socket.send_pyobj((fn, meta), zmq.NOBLOCK)
        except zmq.ZMQError as e:
            pass

        print "Classification sent off for frame", fn

    ctxt.destroy()

if __name__ == "__main__":
    local = "tcp://*"
    vg = "tcp://127.0.0.1"

    parser = argparse.ArgumentParser(description="Camera feed classifier",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-vg", dest="vg", help="video grabber host to pull from",
                        default=vg)

    parser.add_argument("-local", dest="local", help="local transport & ip to push results from",
                        default=local)

    parser.add_argument("-gpu", dest="gpu", help="Use GPU", action="store_true",
                        default=False)

    parser.add_argument("-m", dest="model", help="Caffe model to use", default="googlenet")


    args = parser.parse_args()
    recv_url = args.vg + ":5555" if istcp(args.vg) else args.vg
    send_url = args.local + ":5556" if istcp(args.local) else args.local

    model = "bvlc_" + args.model

    classifier(recv_url, send_url, gpu=args.gpu)
