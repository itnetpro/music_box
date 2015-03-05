# -*- encoding: utf-8 -*-

import os
import datetime
from flask import Flask, render_template, request, session, redirect, url_for, \
    flash
from utils import load_config, save_config, generate_keys

tmpl_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'templates')

app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.debug = True
ini = load_config()


@app.route("/", methods=['GET', 'POST'])
def index():
    if not session.get('dt'):
        session['dt'] = datetime.datetime.now()
    if (datetime.datetime.now() - session.get('dt')).total_seconds() > 360:
        session.is_auth = False
    if request.method == 'POST':
        if not request.form.get('login') and not request.form.get('passwd'):
            return redirect(url_for('index'))
        login = request.form.get('login')
        passwd = request.form.get('passwd')
        if unicode(login) != unicode(ini.get('main', 'login')):
            flash(u'Неверный логин', 'error')
            return redirect(url_for('index'))

        if unicode(passwd) != unicode(ini.get('main', 'passwd')):
            flash(u'Неверный пароль', 'error')
            return redirect(url_for('index'))

        session['dt'] = datetime.datetime.now()
        session['is_auth'] = True

        return redirect(url_for('settings'))
    return render_template('index.html')


@app.route("/settings/", methods=['GET', 'POST'])
def settings():
    if not session.get('is_auth'):
        return redirect(url_for('index'))
    if not session.get('dt'):
        return redirect(url_for('index'))
    if (datetime.datetime.now() - session.get('dt')).total_seconds() > 360:
        session.is_auth = False
        return redirect(url_for('index'))

    ctx = dict(
        key=ini.get('main', 'key'),
        secret_key=ini.get('main', 'secret_key'),
        login=ini.get('main', 'login'),
        password=ini.get('main', 'passwd'),
        price=ini.get('main', 'price'),
        pin=ini.get('main', 'pin'),
        acceptor=ini.get('main', 'acceptor'),
        api=ini.get('main', 'api'),
    )

    if request.method == 'POST':
        keys = ('passwd', 'price', 'pin', 'acceptor', 'api')
        for key in keys:
            ini.set('main', key, request.form.get(key))
        save_config(ini)
        flash(u'Настройки сохранены', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', **ctx)


@app.route("/generate_keys/")
def gen_keys():
    if not session.get('is_auth'):
        return redirect(url_for('index'))
    if not session.get('dt'):
        return redirect(url_for('index'))
    if (datetime.datetime.now() - session.get('dt')).total_seconds() > 360:
        session.is_auth = False
        return redirect(url_for('index'))
    key, secret = generate_keys()
    ini.set('main', 'key', key)
    ini.set('main', 'secret_key', secret)
    save_config(ini)
    flash(u'Новые ключи сгенирированны', 'success')
    return redirect(url_for('settings'))


if __name__ == "__main__":
    app.run(host='127.0.0.1')