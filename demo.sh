#!/bin/bash

#
# DEMO SCRIPT
#
# We can use this to test throughout development, and then we will have a script
# already prepared which we can use for the demo
#
# USAGE: bash$  ./demo.sh
# This will create two separate windows which run the client and server processes
#
#

if [ "$1" == "client" ]
then
   # Run client process
   python3 ./client/app/client
   sleep 30
fi

if [ "$1" == "server" ]
then
   # Run server process
   python3 ./server/app/server
fi
if [ "$1" == "time-db" ]
then
   # Watch DB
   watch -n .3 'python3 -c "import server_db;print(\"\n\".join(str(e) for e in server_db.get_records()))"'
fi


if [ "$1" == "" ]
then
  echo "Starting server & client processes";
  # Create two separate processes for server and client
  gnome-terminal -e './demo.sh server &'
  sleep 1
  gnome-terminal -e './demo.sh client &'
  gnome-terminal -e './demo.sh time-db &'

fi

if [ "$1" == "edit_files" ]
then
   # create folders and edit them
   python /test 3 5
fi
