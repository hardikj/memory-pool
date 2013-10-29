import os
from flask import Flask
from flask import *
from werkzeug import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = '/home/hardik/memory-cloud/static/'
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=["POST"])
def create():
	text = request.form['text']
	return redirect('/%s/upload'%text)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/<name>/upload', methods =['GET', 'POST'])
def upload(name):
	if request.method == 'POST':
		print "yes"
		file = request.files['file']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('uploaded_file', filename=filename))
	return render_template('upload.html', name=name)

@app.route('/upload1/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0')