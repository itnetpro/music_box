# -*- encoding: utf-8 -*-

import os
import re
import hashlib
import ConfigParser
from random import random
from time import time
from subprocess import check_output


def load_config():
    ini = ConfigParser.ConfigParser()
    conf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    if os.path.exists(conf_path):
        if os.path.isfile(conf_path):
            ini.read(conf_path)
        else:
            print('INI-file "%s" not found' % conf_path)
            exit(1)

    if not ini.get('main', 'key') or not ini.get('main', 'secret_key'):
        key, secret = generate_keys()
        if not ini.get('main', 'key'):
            ini.set('main', 'key', key)
        if not ini.get('main', 'secret_key'):
            ini.set('main', 'secret_key', secret)
        save_config(ini)
    return ini


def save_config(ini):
    conf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'config.ini')

    with open(conf_path, 'w') as f:
            ini.write(f)


def generate_keys():
    out = check_output(['ifconfig']).decode('UTF-8')
    m = re.search(r'(HWaddr|ether) ([:0-9a-f]+)', out)
    key = hashlib.sha1(m.group(2).encode('UTF-8')).hexdigest()

    secret_key = str(random())[2:] + str(time()).replace('.', '') + str(random())[2:]
    secret_key = hashlib.sha256(secret_key.encode('UTF-8')).hexdigest()

    return key, secret_key
