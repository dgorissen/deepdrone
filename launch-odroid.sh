#!/bin/bash
rm -f screenlog.*
screen -L -d -m -S vidgrab -s /bin/bash python videograbber.py -vc tcp://192.168.2.1 -drone
screen -L -d -m -S webapp -s /bin/bash python webapp.py

 # var for session name (to avoid repeated occurences)
#sn=deepflying

# Start the session and window 0
#tmux new-session -s "$sn" -n vidgrab "python videograbber.py -vc tcp://192.168.0.10"
#tmux set remain-on-exit on
#tmux new-window -n webapp "python webapp.py"

