# Paste this into Jenkins' "executable script" section in the configuration
# page this is not meant to be executed from where it is.

easy_install --user virtualenv
export PATH="$HOME/.local/bin:$PATH"
if [ '!' -d _ve ]; then
    virtualenv --distribute _ve
fi;

source _ve/bin/activate
easy_install coverage
psql -c "create database spyne_test_$USER" -U postgres

bash -c "coverage run setup.py test; exit 0"
coverage xml -i;
