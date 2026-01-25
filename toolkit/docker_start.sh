#!/bin/bash

cd /home/ddrx/f1tenth_ws/

export PYTHONPATH=$PYTHONPATH:/home/ddrx/f1tenth_ws/toolkit/casadi/

source /opt/ros/noetic/setup.bash
source /home/ddrx/f1tenth_ws/devel/setup.bash

echo "Environment initialized. You should now be in the /home/ddrx/f1tenth_ws workspace."
