import os
from flask import Flask
from flask import *
from werkzeug import secure_filename
from flickr import *
from firebase import firebase

app = Flask(__name__)


UPLOAD_FOLDER = '/home/hardik/memory-cloud/static/'
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
	return render_template('index.html')

@app.route('/create', methods=["POST"])
def create():
	text = request.form['text']
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
		return render_template('create.html', url=auth_url)

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
	return "<a href=\"upload\">upload</a>"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/<name>/upload', methods =['GET', 'POST'])
def upload(name):
    fb = firebase.FirebaseApplication('https://memory-pool.firebaseio.com', None)
    result = fb.get('/', None)
    if name in result:
        result =  fb.get('/%s/flickr'%name, None)
    else:
        return redirect("/%s/setup"%name)

    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            f = FlickrAPI(api_key=API_KEY,            
                          api_secret=API_SECRET,
                          oauth_token=str(result[1]),
                          oauth_token_secret=str(result[2]))
            add_photo = f.post(params={'title':filename}, files=file)
    return render_template('upload.html', name=name)

@app.route('/<name>/timeline')
def timeline(name):
	#return all photos by this user
	return "hello %s"%name

if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0')