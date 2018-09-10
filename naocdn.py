import pickle
import logging
import random
import string
import json
import datetime
import os

from functools import wraps
from flask import Flask, flash, render_template, redirect, request, url_for, jsonify, abort, send_from_directory, Response, send_file, session
from flask_socketio import SocketIO, emit
from io import StringIO
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = "".join(random.choice(string.ascii_letters + string.digits) for x in range(random.randint(10,11)))
flasocket = SocketIO(app)

@flasocket.on('disconnect')
def disconnect_user():
    try:
        session.pop('n4o_logged', None)
    except:
        session.pop('logged_in', None)

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

def check_auth2(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    if username == 'admin' and password == 'admin': # CHANGE THIS
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

def superadmin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth2(auth.username, auth.password):
            session['n4o_logged'] = False
            return authenticate()
        session['n4o_logged'] = True
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
        return render_template(LOGINTEMPLATE, problem='')
    lastpage = None
    log.info('User logged in, sending files')
    m = _DIRPATH+'\\files\\locked\\'
    return send_from_directory(m, filename)

@app.route('/i/')
def imdex():
    log.info('Sending image index page')
    return render_template(TEMPLATEIMAGE, rooturl=root, rooturl2=root)

@app.route('/files/')
def findex():
    log.info('Sending files index page')
    return render_template(TEMPLATEFILES, rooturl=root, rooturl2=root)

@app.route('/files/r/')
def lockfindex():
    global lastpage
    root = request.url_root
    log.info('Accessing /files/r, checking access')
    if not session.get('logged_in'):
        lastpage = '/files/r'
        log.info('User hasn\'t logged in, sending login form')
        return render_template(LOGINTEMPLATE, problem='')
    lastpage = None
    log.info('User logged in, sending template page')
    return render_template(TEMPLATEFILESTRICT, tree=listfile(), rooturl=root, rooturl2=root, rooturl3=root)

@requires_auth
def delfile(file):
    f1 = [f for f in os.listdir(_DIRPATH+'\\files') if os.path.isfile(os.path.join(_DIRPATH+'\\files', f))]
    f2 = [f for f in os.listdir(_DIRPATH+'\\files\\locked') if os.path.isfile(os.path.join(_DIRPATH+'\\files\\locked', f))]
    i1 = [f for f in os.listdir(_DIRPATH+'\\i') if os.path.isfile(os.path.join(_DIRPATH+'\\i', f))]
    if file in f1:
        os.remove(_DIRPATH+'\\files\\'+file)
        return True
    if file in f2:
        os.remove(_DIRPATH+'\\files\\locked\\'+file)
        return True
    if file in i1:
        os.remove(_DIRPATH+'\\i\\'+file)
        return True
    return False

@superadmin_only
def create_invite(customcode):
    if len(str(customcode)) != 16:
        return jsonify({'ERROR': 'invitecode can only be a length of 16 character'})
    with open(_DIRPATH+'\\invites.txt', 'r') as f:
        inv = f.readlines()
    with open(_DIRPATH+'\\invites.txt', 'w') as f:
        dd = ''
        for e in inv:
            dd += e+'\n'
        dd += request.form['invitecode']+'\n'
        f.write(dd)
    return jsonify({'SUCCESS': 'Created invite code of `{}`, give it to the friend now!'.format(request.form['file'])})

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

@app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def index():
    global root
    log.info('Requesting Index')
    root = request.url_root
    if request.method == 'POST':
        if 'file' in request.files:
            te = upfile(request.files['file'], request.form['filename'])
            if not isinstance(te, str):
                return te
            return jsonify({'url': root[:-1]+te})
        elif 'url' in request.form:
            te = shortener(request.form["url"], request.form["short_url"], root)
            return jsonify(te)

        abort(404)
    elif request.method == 'DELETE':
        if 'file' in request.form:
            m = delfile(request.form['file'])
            if m:
                return jsonify({'SUCCESS': 'File `{}` deleted from the server'.format(request.form['file'])})
            return jsonify({'FAILED': 'File `{}` doesn\'t exists on this server'.format(request.form['file'])})
        elif 'url' in request.form:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
            return deleteshort(request.form['url'])
    elif request.method == 'PUT':
        if 'invitecode' in request.form:
            return create_invite(request.form['invitecode'])
    else:
        return render_template(TEMPLATE, rooturl=root, rooturl2=root, rooturl3=root)

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
    root = request.url_root
    path = request.path[1:]
    log.error(e)
    return render_template(ERRPAGE, errcode='404', errmsg='Not Found', extrainfo='Link `{}` are not found in this server.'.format(path), rooturl=root), 404

@app.errorhandler(401)
def not_authenticated(e):
    log.error(e)
    return render_template(ERRPAGE, errcode='404', errmsg='Not Authorized', extrainfo='Either you put the wrong username or password combination or the login info doesn\'t exist.'), 401

@app.route('/register', methods=['GET', 'POST'])
def registuser():
    if request.method == 'POST':
        with open(_DIRPATH+'\\invites.txt', 'r') as f:
            invitelist = f.readlines()
        ucode = request.form['invitecode']
        if len(str(ucode)) != 16:
            log.error('User tried to register, but provided more or less than 16 digit code')
            flash('Invite code can only be 16 digit', category='error')
            return render_template(INVITEDTEMPLATE, problem='Invite code can only be 16 digit')
        if ucode not in invitelist:
            log.error('User tried to register, but provided wrong invite code')
            flash('Invite code not found or used already', category='error')
            return render_template(INVITEDTEMPLATE, problem='Invite code not found or used already')

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
        return render_template(INVITEDTEMPLATE, problem='You\'re Successfully Registered')
    else:
        log.info('User requested register via GET method')
        return render_template(INVITEDTEMPLATE, problem='')

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
            return render_template(LOGINTEMPLATE, problem='Wrong Username or Password combination')
        if lastpage is None:
            return redirect(root)
        else:
            return redirect(root[:-1]+lastpage)
    else:
        log.info('User requested login via GET method')
        lastpage = None
        return render_template(LOGINTEMPLATE, problem='')

def makesure():
    log.debug('Make sure everything is ready and not buggy')
    global lastpage
    global _DIRPATH
    global ERRPAGE
    global TEMPLATE
    global TEMPLATEFILES
    global TEMPLATEFILESTRICT
    global TEMPLATEIMAGE
    global LOGINTEMPLATE
    global INVITEDTEMPLATE
    lastpage = None
    _DIRPATH = os.path.dirname(os.path.realpath(__file__))
    # Check necessary files
    if not os.path.isfile(_DIRPATH+'\\url_list.p'):
        with open(_DIRPATH+'\\url_list.p', 'wb') as fms:
            pickle.dump([('PADDING', '')], fms)
    if not os.path.isfile(_DIRPATH+'\\auth.json'):
        with open(_DIRPATH+'\\auth.json', 'w') as fms:
            json.dump({'0': {'username': 'admin', 'password': 'admin'}}, fms)
    if not os.path.isfile(_DIRPATH+'\\invites.txt'):
        with open(_DIRPATH+'\\invites.txt', 'w') as fms:
            fms.write('')
    # Check template page
    if not os.path.isfile(_DIRPATH+'\\templates\\error_page.html'):
        raise FileNotFoundError('template page of \'error_page\' not found')
    else:
        ERRPAGE = 'error_page.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\index.html'):
        raise FileNotFoundError('template page of \'index\' not found')
    else:
        TEMPLATE = 'index.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\index_files.html'):
        raise FileNotFoundError('template page of \'index_files\' not found')
    else:
        TEMPLATEFILES = 'index_files.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\index_files-strict.html'):
        raise FileNotFoundError('template page of \'index_files-strict\' not found')
    else:
        TEMPLATEFILESTRICT = 'index_files-strict.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\index_img.html'):
        raise FileNotFoundError('template page of \'index_img\' not found')
    else:
        TEMPLATEIMAGE = 'index_img.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\login.html'):
        raise FileNotFoundError('template page of \'login\' not found')
    else:
        LOGINTEMPLATE = 'login.html'
    if not os.path.isfile(_DIRPATH+'\\templates\\register.html'):
        raise FileNotFoundError('template page of \'register\' not found')
    else:
        INVITEDTEMPLATE = 'register.html'
    # Check folder
    if not os.path.isdir(_DIRPATH+'\\files'):
        os.makedirs(_DIRPATH+'\\files')
    if not os.path.isdir(_DIRPATH+'\\files\\locked'):
        os.makedirs(_DIRPATH+'\\files\\locked')
    if not os.path.isdir(_DIRPATH+'\\i'):
        os.makedirs(_DIRPATH+'\\i')
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
    app.run(host='0.0.0.0', debug=True)