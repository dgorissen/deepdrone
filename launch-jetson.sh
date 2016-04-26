#!/bin/bash

rm -f screenlog.*
# assumes this; http://superuser.com/questions/235760/ld-library-path-unset-by-screen (chgrp of scren)
screen -l -L -d -m -S class -s -/bin/bash python classifier.py -gpu
screen -l -L -d -m -S vidgrab -s -/bin/bash python videograbber.py -drone
screen -l -L -d -m -S webapp -s -/bin/bash python webapp.py

 # var for session name (to avoid repeated occurences)
#sn=deepflying

# Start the session and window 0
#tmux new-session -s "$sn" -n vidgrab "python videograbber.py -vc tcp://192.168.0.10"
#tmux set remain-on-exit on
#tmux new-window -n webapp "python webapp.py"

