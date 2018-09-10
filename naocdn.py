import pickle
import logging
import random
import string
import json
import datetime
import os

from functools import wraps
from flask import Flask, flash, render_template_string, redirect, request, url_for, jsonify, abort, send_from_directory, Response, send_file, session
from flask_socketio import SocketIO, emit
from io import StringIO
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = "".join(random.choice(string.ascii_letters + string.digits) for x in range(random.randint(10,11)))
flasocket = SocketIO(app)

@flasocket.on('disconnect')
def disconnect_user():
    session.pop('logged_in', None)

TEMPLATEFILES = """
<!DOCTYPE html>
<html>
<head>
  <link rel="shortcut icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O - WebFiles</title>
  <meta name="description" content="n4o meme hosting for image and file serving">
<style type="text/css">
body {
    width: 600px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
<body>
<p>nothing here :(</p>
<h4><a href="https://blog.n4o.xyz">web</a> | <a href="https://github.com/noaione/noaione.github.io">manage</a> | <a href="{{ rooturl }}login">login</a> | <a href="{{ rooturl2 }}register">register</a></h4>
</body>
</head>
</html>
"""

TEMPLATEFILESTRICT = """
<!DOCTYPE html>
<html>
<head>
  <link rel="shortcut icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O - WebFiles (RESTRICTED!)</title>
  <meta name="description" content="n4o meme hosting for image and file serving">
<style type="text/css">
body {
    width: 800px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
<body>
<h4><a href="https://blog.n4o.xyz">web</a> | <a href="https://github.com/noaione/noaione.github.io">manage</a> | <a href="{{ rooturl }}login">login</a> | <a href="{{ rooturl2 }}register">register</a></h4>
<p><strong>Filename</strong> || Filesize || Download button</p>
<p>
{%- for item in tree.children recursive %}
    <strong>{{ item.name }}</strong> || {{ item.size }} || <button type="button" onclick="window.location.href='{{ rooturl3 }}files/r/{{ item.name }}' ">Download</button><br />
{%- endfor %}
</p>
</body>
</head>
</html>
"""

FZFPAGE = """
<!DOCTYPE html>
<html>

  <head>
    <link rel="icon" href="https://blog.n4o.xyz/favicon.png">
    <title>N4O WebFiles - Whoops! 404</title>

    <meta name="description" content="blog.n4o.xyz files hosting but link not found :(">

    <style type="text/css">
      body {
        position: absolute;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif
        width: 600px;
        height: 650px;
        left: 50%;
        top: 50%;
        margin-left: -390px;
        margin-top: -325px;
        text-align: center;
        background-color: rgb(237, 237, 237);
        color: rgb(100,100,100);
      }

    </style>

    <body>
      <h2><img src="https://static.thenounproject.com/png/801773-200.png" alt="Logo" /></h2>
      <h1>404</h1>
      <h3><b>Not Found</b></h3>
      <p>Link requested are not found in this server.<br />Please contact this website administrator<br />Discord: N4O#8868 | email: admin@n4o.xyz</p>
      <span style="font-size: 10pt"><a href="https://blog.n4o.xyz">web</a> || <a href="https://github.com/noaione/noaione.github.io">manage</a></span>
    </body>
  </head>

</html>
"""

TEMPLATEIMAGE = """
<!DOCTYPE html>
<html>
<head>
  <link rel="shortcut icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O - WebFiles</title>
  <meta name="description" content="n4o meme hosting for image and file serving">
<style type="text/css">
body {
    width: 600px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
<body>
<p>nothing here :(</p>
<h4><a href="https://blog.n4o.xyz">web</a> | <a href="https://github.com/noaione/noaione.github.io">manage</a> | <a href="{{ rooturl }}login">login</a> | <a href="{{ rooturl2 }}register">register</a></h4>
</body>
</head>
</html>
"""

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <link rel="icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O WebFiles Main Page</title>

  <meta name="description" content="blog.n4o.xyz files hosting">

<style type="text/css">
body {
    width: 900px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
</head>
<body>
<p><img src="https://i.warosu.org/data/biz/img/0022/71/1496517555527.jpg" width=200 height=200 alt="Logo" /></p>
<h1>N4O WebFiles Main Page</h1>
<p>Seems like you get to my image/files web hosting</p>
<p>Public shortener: `curl -F="url=your.long/url/that/you/want/to/shorten" {{ rooturl }}
<h4><a href="https://blog.n4o.xyz">web</a> | <a href="https://github.com/noaione/noaione.github.io">manage</a> | <a href="{{ rooturl2 }}login">login</a> | <a href="{{ rooturl3 }}register">register</a></h4>
</body>
</html>
"""

LOGINTEMPLATE = """
<head>
  <link rel="shortcut icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O - Login</title>
  <meta name="description" content="n4o meme hosting for image and file serving">
<style type="text/css">
body {
    width: 600px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
</head>
{% block body %}
{% if session['logged_in'] %}
<p>You're logged in already!</p>
{% else %}
 
 
<form action="/login" method="POST">
	<div class="login">
		<div class="login-screen">
			<div class="app-title">
				<h2>Authorized Login Only</h2>
                <p>Access to this page is restricted<br /> Ask N4O#8868 at Discord for Access<br /><font color="red">{{ problem }}</font></p>
			</div>
 
			<div class="login-form">
				<div class="control-group">
				Enter Username: <input type="text" class="login-field" value="" placeholder="Your Username" name="username">
				<label class="login-field-icon fui-user" for="login-name"></label>
				</div>
 
				<div class="control-group">
				Enter Password: &nbsp;<input type="password" class="login-field" value="" placeholder="Your Password" name="password">
				<label class="login-field-icon fui-lock" for="login-pass"></label>
				</div>
                <br />
                <input type="submit" value="Gain Access" class="btn btn-primary btn-large btn-block" >
			    <br>
			</div>
		</div>
	</div>
</form>
 
{% endif %}
{% endblock %}
"""

INVITEDTEMPLATE = """
<head>
  <link rel="shortcut icon" href="https://blog.n4o.xyz/favicon.png">
  <title>N4O - Register/Invite</title>
  <meta name="description" content="n4o meme hosting for image and file serving">
<style type="text/css">
body {
    width: 600px;
    margin: 10px auto;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
}
</style>
</head>
{% block body %}

<form action="/register" method="POST">
	<div class="login">
		<div class="login-screen">
			<div class="app-title">
				<h2>Welcome to my invite page</h2>
                <p>Ask N4O#8868 at Discrod for Invite :teehee:<br /><font color="red">{{ problem }}</font></p>
			</div>
 
			<div class="login-form">
				<div class="control-group">
				Enter Invite Code: <input type="text" class="login-field" value="" placeholder="Invite code (16 digit)" name="invitecode">
				<label class="login-field-icon fui-user" for="login-name"></label>
				</div>
 
				<div class="control-group">
				Enter Desired Username: <input type="text" class="login-field" value="" placeholder="Your Username" name="username">
				<label class="login-field-icon fui-user" for="login-name"></label>
				</div>

				<div class="control-group">
				Enter Desired Password: &nbsp;<input type="password" class="login-field" value="" placeholder="Your Password" name="password">
				<label class="login-field-icon fui-lock" for="login-pass"></label>
				</div>
                <br />
                <input type="submit" value="Gain Access" class="btn btn-primary btn-large btn-block" >
			    <br>
			</div>
		</div>
	</div>
</form>
 
{% endblock %}
"""

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    with open(_DIRPATH+'\\auth.json', 'r') as fp:
        auth = json.load(fp)
    uc = []
    pc = []
    for up in auth: # For multiple user authorization
        uc.append(auth[up]["username"])
        pc.append(auth[up]["password"])
    if username in uc and password in pc: # Check it
        if uc.index(username) != pc.index(password):
            return False
        return True
    return False

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response("ERROR: Not Authorized to use this command or access this page", 401, {'WWW-Authenticate': 'Secret things="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            session['logged_in'] = False
            return authenticate()
        session['logged_in'] = True
        return f(*args, **kwargs)
    return decorated

def shortener(url, customurl, root):
    log.info('Trying to shortening url of {}'.format(url))
    with open('url_list.p', 'rb') as f:
        url_list = pickle.load(f)

    for item in url_list:
        if url == item[0]:
            log.info('URL `{}` already exists in the server, using that to user that request it.'.format(url))
            surl = '{r}{it}'.format(r=root, it=item[1])
            return {'url': url, 'short_url': surl}

    if customurl is not None:
        log.info('User provided custom short url, using that')
        url_hash = customurl
        url_list.append((url, url_hash))
    elif customurl is None:
        letters = string.ascii_letters + string.digits
        url_hash = "".join(random.choice(letters) for x in range(random.randint(4, 8)))
        url_list.append((url, url_hash))
    with open('url_list.p', 'wb') as f:
        pickle.dump(url_list, f)

    shortened_url = '{r}{url}'.format(r=root, url=url_hash)
    return {'url': url, 'short_url': shortened_url}

def checkifimage(f):
    log.info('Checking files type')
    imgfmt = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.heif']
    fe = os.path.splitext(f)[1].lower()
    if fe in imgfmt:
        log.info('File detected as an image')
        if not os.path.isdir(_DIRPATH+'/i/'):
            log.debug('Creating image folder')
            os.makedirs(_DIRPATH+'/i/')
        return '/i/'
    else:
        log.info('File detected as a non-image')
        if not os.path.isdir(_DIRPATH+'/files/'):
            log.debug('Creating files folder')
            os.makedirs(_DIRPATH+'/files/')
        return '/files/'

def listfile():
    tree = dict(children=[])
    listfile = [f for f in os.listdir(_DIRPATH+'/files/locked/') if os.path.isfile(os.path.join(_DIRPATH+'/files/locked/', f))]
    rootdir = _DIRPATH+'/files/locked/'
    for file in listfile:
        size = f'{os.path.getsize(rootdir+file)/1000} kb'
        tree['children'].append(dict(name=file, size=size))
    
    return tree


def secure_filename(f, filename, savedir):
    log.info('Securing filename for {}'.format(f))
    def hash(ext):
        letters = string.ascii_letters + string.digits
        url_hash = "".join(random.choice(letters) for x in range(random.randint(4, 8)))
        return url_hash+ext
    ext = os.path.splitext(f)[1]
    if filename is None:
        log.info('Filename not provided by user, randomizing...')
        filename = hash(ext)
    listfiles = [f for f in os.listdir(savedir) if os.path.isfile(os.path.join(savedir, f))]
    while True:
        if filename not in listfiles:
            break
        log.info('Filename are clashing, randomzing...')
        filename = hash(ext)
    log.info('Filename secured for {}, with filename of {}'.format(f, filename))
    return filename

@requires_auth
def upfile(f, fn):
    log.info('Grabbing files and data from POST request')
    dd = f.stream.read()
    f = f.filename
    cwd = os.getcwd()
    spx = checkifimage(f)
    fd = cwd+spx
    fn = secure_filename(f, fn, fd)

    with open(fd+fn, 'wb') as saveas:
        log.info('Writing stream data to file')
        saveas.write(dd)

    log.info('Finished downloading `{}`'.format(f))
    return spx+fn

@app.route('/i/<path:filename>')
def image(filename):
    m = _DIRPATH+'\\i\\'
    log.info('Trying to send {} to user'.format(filename))
    return send_from_directory(m, filename)

@app.route('/files/<path:filename>')
def files(filename):
    m = _DIRPATH+'\\files\\'
    log.info('Trying to send {} to user'.format(filename))
    return send_from_directory(m, filename)

@app.route('/files/r/<path:filename>')
def fileslock(filename):
    global lastpage
    log.info('Accessing /files/r/{}, checking access'.format(filename))
    if not session.get('logged_in'):
        lastpage = '/files/r/{}'.format(filename)
        log.info('User hasn\'t logged in, sending login form')
        return render_template_string(LOGINTEMPLATE, problem='')
    lastpage = None
    log.info('User logged in, sending files')
    m = _DIRPATH+'\\files\\locked\\'
    return send_from_directory(m, filename)

@app.route('/i/')
def imdex():
    log.info('Sending image index page')
    return render_template_string(TEMPLATEIMAGE, rooturl=root, rooturl2=root)

@app.route('/files/')
def findex():
    log.info('Sending files index page')
    return render_template_string(TEMPLATEFILES, rooturl=root, rooturl2=root)

@app.route('/files/r/')
def lockfindex():
    global lastpage
    root = request.url_root
    log.info('Accessing /files/r, checking access')
    if not session.get('logged_in'):
        lastpage = '/files/r'
        log.info('User hasn\'t logged in, sending login form')
        return render_template_string(LOGINTEMPLATE, problem='')
    lastpage = None
    log.info('User logged in, sending template page')
    return render_template_string(TEMPLATEFILESTRICT, tree=listfile(), rooturl=root, rooturl2=root, rooturl3=root)

@requires_auth
def deleteshort(short_url):
    log.info('Trying to delete short url: {}'.format(short_url))
    url = os.path.basename(short_url)
    with open('url_list.p', 'rb') as f:
        url_list = pickle.load(f)

    num = 0
    for item in url_list:
        if url == item[1]:
            break
        num += 1

    try:
        url_list.remove(url_list[num])
    except:
        log.error('Failed deleting `{}`, reason: Not Found'.format(short_url))
        return abort(jsonify({'error': 'SHORT URL provided not found'}))

    with open('url_list.p', 'wb') as f:
        pickle.dump(url_list, f)

    log.info('Success deleting `{}`'.format(short_url))
    return jsonify({"success": "short url \"{url}\" deleted".format(url=url)})

@app.route('/', methods=['GET', 'POST', 'DELETE'])
def index():
    global root
    log.info('Requesting Index')
    root = request.url_root
    if request.method == 'POST':
        if 'files' in request.files:
            print(request.form['filename'])
            te = upfile(request.files['files'], request.form['filename'])
            if not isinstance(te, str):
                return te
            return jsonify({'url': root[:-1]+te})
        elif 'url' in request.form:
            te = shortener(request.form["url"], request.form["short_url"], root)
            return jsonify(te)

        abort(404)
    elif request.method == 'DELETE':
        return deleteshort(request.form['url'])
    else:
        return render_template_string(TEMPLATE, rooturl=root, rooturl2=root, rooturl3=root)

@app.route('/listing', methods=['GET'])
def _list():
    with open('url_list.p', 'rb') as f:
        url_list = pickle.load(f)
    
    data = {}
    num = 0
    for item in url_list:
        data[num] = {'url': item[0], 'short_url': item[1]}
        num += 1
    
    return jsonify(data)

@app.route('/<hash>')
def redirect_url(hash):
    with open('url_list.p', 'rb') as f:
        url_list = pickle.load(f)
    for item in url_list:
        if hash == item[1]:
            return redirect(item[0])
    return abort(404)

@app.errorhandler(404)
def not_found(e):
    log.error(e)
    return render_template_string(FZFPAGE), 404

@app.errorhandler(401)
def not_authenticated(e):
    log.error(e)
    return "You're not authorized <br />Either you put the wrong username or password combination or the login info doesn't exist", 401

@app.route('/register', methods=['GET', 'POST'])
def registuser():
    root = request.url_root
    if request.method == 'POST':
        with open(_DIRPATH+'\\invites.txt', 'r') as f:
            invitelist = f.readlines()
        ucode = request.form['invitecode']
        if len(str(ucode)) != 16:
            log.error('User tried to register, but provided more or less than 16 digit code')
            flash('Invite code can only be 16 digit', category='error')
            return render_template_string(INVITEDTEMPLATE, problem='Invite code can only be 16 digit')
        if ucode not in invitelist:
            log.error('User tried to register, but provided wrong invite code')
            flash('Invite code not found or used already', category='error')
            return render_template_string(INVITEDTEMPLATE, problem='Invite code not found or used already')

        usern = request.form['username']
        passw = request.form['username']
        invitelist.remove(ucode)

        with open(_DIRPATH+'\\auth.json', 'r') as f:
            authdata = json.load(f)
        n = 0
        for auth in authdata:
            n += 1
        
        authdata[n+1] = {"username": usern, "password": passw}

        with open(_DIRPATH+'\\auth.json', 'w') as f:
            json.dump(authdata, f)
        with open(_DIRPATH+'\\invites.txt', 'w') as fp:
            dd = ''
            for invite in invitelist:
                dd += invite+'\n'
            fp.write(dd)
        
        session['logged_in'] = True
        log.info('Registered user, Username `{}`, password `{}`'.format(usern, passw))
        return redirect(root)
    else:
        log.info('User requested register via GET method')
        return render_template_string(INVITEDTEMPLATE, problem='')

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    global lastpage
    root = request.url_root
    if request.method == 'POST':
        if check_auth(request.form['username'], request.form['password']):
            log.info('User `{}` Logged in'.format(request.form['username']))
            session['logged_in'] = True
        else:
            log.error('Someone tried to logged in but failed, wrong Username or password')
            return render_template_string(LOGINTEMPLATE, problem='Wrong Username or Password combination')
        if lastpage is None:
            return redirect(root)
        else:
            return redirect(root[:-1]+lastpage)
    else:
        log.info('User requested login via GET method')
        lastpage = None
        return render_template_string(LOGINTEMPLATE, problem='')

def makesure():
    log.debug('Make sure everything is ready and not buggy')
    global lastpage
    global _DIRPATH
    lastpage = None
    _DIRPATH = os.path.dirname(os.path.realpath(__file__))
    if not os.path.isfile(_DIRPATH+'\\url_list.p'):
        with open(_DIRPATH+'\\url_list.p', 'wb') as fms:
            pickle.dump(('PADDING', ''), fms)
    if not os.path.isfile(_DIRPATH+'\\auth.json'):
        with open(_DIRPATH+'\\auth.json', 'w') as fms:
            json.dump({'0': {'username': 'admin', 'password': 'admin'}}, fms)
    if not os.path.isfile(_DIRPATH+'\\invites.txt'):
        with open(_DIRPATH+'\\invites.txt', 'w') as fms:
            fms.write('')
    log.debug('Everything is OK!')

if __name__ == '__main__':
    STARTTIME = datetime.datetime.now()
    print('@@ Starting up server')
    print('!! Current time: {}'.format(STARTTIME))
    print('!! Booting up Logger')
    log = logging.getLogger('werkzeug')
    formatter = logging.Formatter(
        "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    handler = RotatingFileHandler(str(STARTTIME).replace(':', '-')+'.log', maxBytes=10000000, backupCount=5)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.info('Server Started at {}'.format(STARTTIME))
    print('!! Logger Booted up')
    print('@@ Making sure everything is ready')
    makesure()
    print('@@ Server booted up')
    app.run(host='0.0.0.0')