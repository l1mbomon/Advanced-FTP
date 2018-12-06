

# Remove all client directories
clean:
	rm -rf $$(find server/.data/* -type d )

# Remove db file
cleandb-server:
	rm -f server/.data/server.*

cleandb-client:
	rm -f client/.data/client.*
	rm -f client/.data/t*

cleanall: clean cleandb-server cleandb-client

# to install: sudo apt-get install pylint3
pylint-client:
	pylint3 --rcfile pylint.rc -rn $$(find client/*/*.py client/app/*)

pylint-server:
	pylint3 --rcfile pylint.rc -rn $$(find server/app/* server/*/*.py)


demo:
	./demo.sh


run-server:
	python3 server/app/server

run-client:
	python3 client/app/client
