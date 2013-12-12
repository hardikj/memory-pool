import flask 
from flask import *
import os
import time
from shutil import rmtree
from hashlib import sha1
from PIL import Image, ImageFile
from stat import S_ISREG, ST_CTIME, ST_MODE
from gevent.event import AsyncResult, Timeout
from gevent.queue import Empty, Queue
from firebase import firebase
from flickr import *

API_KEY = '5fe2225dc7b1955d14b3bc31c5f47a70'
API_SECRET = 'f662c05421e7d3c6'

DATA_DIR = 'static/data'
app = flask.Flask(__name__)

KEEP_ALIVE_DELAY = 25
MAX_IMAGE_SIZE = 800, 600
MAX_IMAGES = 10
MAX_DURATION = 300

broadcast_queue = Queue()

try:
    rmtree(DATA_DIR, True)
    os.mkdir(DATA_DIR)
except OSError:
    pass

def broadcast(message):
    """ Notify all waiting waiting gthreads of message. """
    waiting = []
    try:
        while True:
            waiting.append(broadcast_queue.get(block=False))
    except Empty:
        pass
    print('Broadcasting {0} messages'.format(len(waiting)))
    for item in waiting:
        item.set(message)

def receive():

    now = time.time()
    end = now + MAX_DURATION
    tmp = None
    while now < end:
        if not tmp:
            tmp = AsyncResult()
            broadcast_queue.put(tmp)
        try:
            yield tmp.get(timeout=KEEP_ALIVE_DELAY)
            tmp = None
        except Timeout:
            yield ''
        now = time.time()

def event_stream(client):
    force_disconnect = False
    try:
        for message in receive():
            yield 'data: {0}\n\n'.format(message)
        print('{0} force closing stream'.format(client))
        force_disconnect = True
    finally:
        if not force_disconnect:
            print('{0} disconnected from stream'.format(client))

@app.route('/stream')
def stream():
    return flask.Response(event_stream(flask.request.access_route[0]), mimetype='text/event-stream')

def save_image(path, data):
    image_parser = ImageFile.Parser()
    try:
        image_parser.feed(data)
        image = image_parser.close()
    except IOError:
        raise
        return False
    image.thumbnail(MAX_IMAGE_SIZE, Image.ANTIALIAS)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(path)
    return True

@app.route('/post', methods=["POST"])
def post():
    sha1sum = sha1(flask.request.data).hexdigest()
    target = os.path.join(DATA_DIR, '{0}.jpg'.format(sha1sum))
    message = json.dumps({'src': target})
    try:
        if save_image(target, flask.request.data):
            broadcast(message)
    except Exception as e:
        return format(e)
    return "sucess"

@app.route('/<name>/upload', methods=["GET", "POST"])
def upload(name):
    image_infos = []
    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        file_stat = os.stat(filepath)
        if S_ISREG(file_stat[ST_MODE]):
            image_infos.append((file_stat[ST_CTIME], filepath))

    images = []
    for i, (_, path) in enumerate(sorted(image_infos, reverse=True)):
        images.append(format(path))
        
    return render_template('upload.html', image=images)


#########################################################################################################

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/create', methods=["POST"])
def create():
    text = request.form['text']
    fb = firebase.FirebaseApplication('https://memory-pool.firebaseio.com', None)
    result = fb.get('/', None)
    if text in result:
        return redirect("%s"%text)
    else:
        return redirect('/%s/setup'%text)

@app.route('/<name>/setup')
def setup(name):
    if request.method == 'GET':
        fb = firebase.FirebaseApplication('https://memory-pool.firebaseio.com', None)
        result = fb.get('/', None)
        if name in result:
            return redirect("%s"%name)
        f = FlickrAPI(api_key = API_KEY, 
                      api_secret = API_SECRET,
                      callback_url='http://0.0.0.0:5000/%s/final'%name)
        auth_props = f.get_authentication_tokens()
        auth_url = auth_props['auth_url']
        app.config['OAUTH_TOKEN'] = auth_props['oauth_token']
        app.config['OAUTH_TOKEN_SECRET'] = auth_props['oauth_token_secret']
        return render_template('setup.html', url=auth_url, name=name)

@app.route('/<name>/final')
def final(name):
    if request.args['oauth_verifier']:
        f = FlickrAPI(api_key=API_KEY, 
                      api_secret=API_SECRET,
                      oauth_token=app.config['OAUTH_TOKEN'],
                      oauth_token_secret=app.config['OAUTH_TOKEN_SECRET'])
        authorized_tokens = f.get_auth_tokens(request.args['oauth_verifier'])
        final_oauth_token = authorized_tokens['oauth_token']
        final_oauth_token_secret = authorized_tokens['oauth_token_secret']
        fb = firebase.FirebaseApplication('https://memory-pool.firebaseio.com', None)
        result = fb.put('/',name,{'flickr':{'1':final_oauth_token, '2':final_oauth_token_secret}})
        return redirect("/%s/"%name)

@app.route('/<name>/')
def name(name):
    fb = firebase.FirebaseApplication('https://memory-pool.firebaseio.com', None)
    result = fb.get('/', None)
    if name not in result:
        redirect('/%s/setup/'%name)
    return render_template("app.html", name=name)


if __name__ == '__main__':
    app.debug = True
    app.run(threaded=True)
