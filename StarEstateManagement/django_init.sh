#!/bin/bash
while ! nc -z mysql 3306 ; do
    echo "Waiting for the MySQL Server"
    sleep 3
done

python3 manage.py makemigrations&&
python3 manage.py migrate&&
coproc glances -w --disable-webui &&
uwsgi --ini uwsgi.ini -d uwsgi.log&&
tail -f /dev/null
exec "$@"
