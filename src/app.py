from flask import Flask, render_template, request, redirect, url_for, Blueprint, flash, session
from flask_login import LoginManager, login_required, current_user, login_user, UserMixin, logout_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import base64, os
 
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLITE_URI") #'sqlite:///posts.db'
app.config.from_object('src.config')
app.secret_key = os.environ.get("SECRETE_KEY")
db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    author_id = db.Column(db.Integer)
    profile_image = db.Column(db.LargeBinary)
    comments = db.relationship("Comment", backref=db.backref('user', lazy=True))

    def __repr__(self):
        return 'User' + str(self.id)

class BlogPost(db.Model):
    __tablename__ = 'blogpost'
    id = db.Column(db.Integer,primary_key = True)
    author = db.Column(db.String(100),nullable = False, default = 'N/A')
    author_id = db.Column(db.String(100))
    title = db.Column(db.String(100), nullable = False)
    content = db.Column(db.Text, nullable = False)
    date_posted = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    category = db.Column(db.String(1000))
    post_images = db.Column(db.LargeBinary)
    likes = db.Column(db.Integer, default=0)
    comments = db.relationship("Comment", backref=db.backref('blogpost', lazy=True))
    post_images = db.relationship("PostImage", backref=db.backref('blogpost', lazy=True))

    def __repr__(self):
        return 'Blog post ' + str(self.id)

class PostImage(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    name = db.Column(db.String(100))
    image_filename = db.Column(db.String(100))
    image_data = db.Column(db.LargeBinary)
    blog_id = db.Column(db.String(1000), db.ForeignKey('blogpost.id')) 

    def __repr__(self):
        return '< Image id={}, name={} >'.format(self.id, self.name)

class Comment(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    content = db.Column(db.Text, nullable = False)
    date_posted = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    blog_id = db.Column(db.String(1000), db.ForeignKey('blogpost.id')) 
    user_id = db.Column(db.String(1000), db.ForeignKey('user.id')) 

    def __repr__(self):
        return '<Comment %r>' % self.id
     
     
@app.before_first_request
def init_db():
    db.create_all()
  
@app.route('/')
def index():
    return render_template('index.html')


# Route for handling the login page logic
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # check if user actually exists
        # take the user supplied password, hash it, and compare it to the hashed password in database
        user = User.query.filter_by(email=email).first()
    
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login')) # if user doesn't exist or password is wrong, reload the page
        else:
            login_user(user) #remember = remember
            return redirect(url_for('profile'))

    #remember = True if request.form['remember'] else False
    return render_template('login.html') 


login_manager = LoginManager(app=app)
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))
    #return SessionUser.find_by_session_id(user_id)  # hits the database


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(name=username).first() # if this returns a user, then the email already exists in database

        if user: # if a user is found, we want to redirect back to signup page so user can try again
            flash('Email address already exists')
            return redirect(url_for('signup'))
        else:
            # create new user with the form data. Hash the password so plaintext version isn't saved.
            author_id = uuid.uuid4().hex 
            new_user = User(email=email, password=generate_password_hash(password, method='sha256'), name=username, author_id=author_id)
            # add the new user to the database
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('profile'))
    return render_template('signup.html') 

# The profile page section 
@app.route('/profile')
@login_required
def profile():
    all_posts = BlogPost.query.filter_by(author_id=current_user.author_id)
    if current_user.profile_image:
        profile_img = current_user.profile_image.decode('utf-8')
    else:
        profile_img = None
    return render_template('profile.html', user = current_user, profile_image=profile_img, posts=all_posts)

#===================================== The Upload section =========================================== 
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit_profile', methods=['POST', 'GET'])
def edit_profile():
    name = current_user.name
    email = current_user.email

    if request.method == 'POST':
        image = request.files['image_file']
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(path)
            with open(path, 'rb') as img:
                encoded_image = base64.b64encode(img.read())
                current_user.profile_image = encoded_image
        current_user.name = request.form['name']
        current_user.email = request.form['email']
        db.session.commit()
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', name=name, email=email)

# The LogOut section
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# The Delete User section
@app.route('/delete_user/<string:author_id>')
@login_required
def delete_user(author_id):
    User.query.filter_by(author_id=author_id).delete()
    BlogPost.query.filter_by(author_id=author_id).delete()
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/contact', methods=('GET', 'POST'))
def contact():
    if request.method == 'POST':
        post_name = request.form['name']
        post_email = request.form['email']
        post_content = request.form['comments']
        #new_contact = Contact(name = post_name, email=post_email, content = post.content)
        #db.session.add(new_contact)
        #db.session.commit()
        flash('Message Sent (:')
        return redirect(url_for('trending'))
    else:
        return render_template('trendingposts.html')

@app.route('/posts', methods = ['GET'])
@login_required
def posts():
    all_posts = BlogPost.query.order_by(BlogPost.date_posted).all()
    return render_template('posts.html', posts = all_posts)

@app.route("/user_posts/<string:author_id>", methods = ['GET'])
@login_required
def user_posts(author_id):
    all_posts = BlogPost.query.filter_by(author_id=author_id)
    return render_template('posts.html', posts = all_posts)

@app.route('/posts/delete/<int:id>')
@login_required
def delete(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return redirect('/posts')

@app.route('/posts/editpost/<int:id>', methods = ['GET', 'POST'])
@login_required
def editpost(id):
    post = BlogPost.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.author = request.form['author']
        post.content = request.form['content']
        db.session.commit()
        return redirect('/posts')
    else:
        return render_template('editpost.html', post = post)

@app.route('/posts/new/<string:id>', methods = ['GET', 'POST'])
@login_required
def new_post(id):
    user = User.query.get(id)
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        content = request.form['content']
        category = request.form['category']
        new_post = BlogPost(title = title, content = content, author = author, author_id=user.author_id, category=category)
        db.session.add(new_post)
        db.session.commit()
        image = request.files['image_file']
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(path)
            with open(path, 'rb') as img:
                encoded_image = base64.b64encode(img.read())
                new_post_image = PostImage(name=image.filename, image_filename=image.filename, image_data=encoded_image, blog_id=new_post.id)
                db.session.add(new_post_image)
        db.session.commit()
        return redirect('/user_posts/{}'.format(user.author_id)) 
    else:
        return render_template('new_post.html', user=user)


@app.route('/like_post/<int:post_id>')
def like_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    already_liked =[0]
    if already_liked[0] == 0:
        already_liked.pop()
        post.likes += 1
        db.session.commit()
    already_liked.append(1)   
    return redirect(url_for('readmore', post_id=post_id)) 


@app.route('/trending', methods = ['GET'])
def trending():
    all_posts = BlogPost.query.order_by(BlogPost.date_posted).all()
    all_post_images = []        # This returns a list of lists
    post_indexes = []
    for idx,post in enumerate(all_posts):
        if post.post_images:
            post_images = [image.image_data.decode('utf-8') for image in post.post_images] # current_user.profile_image.decode('utf-8')
            all_post_images.append(post_images) 
            post_indexes.append(idx)
    post_indexes.reverse()
    post_indexes.reverse()
    return render_template('trendingposts.html', posts = all_posts, post_images=all_post_images, post_indexes=post_indexes, posts_length=len(all_posts), indexes_length=len(post_indexes))

@app.route('/readmore/<int:post_id>', methods = ['GET', 'POST'])
def readmore(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'post':
        return render_template('readmore.html', post=post)
    if post.post_images:
        post_image = [image.image_data.decode('utf-8') for image in post.post_images]
    else:
        post_image = []
    comments = post.comments # This returns a list
    total_comments = len(comments)
    return render_template('readmore.html', post=post, post_image=post_image, comments=comments, total_comments=total_comments)

@app.route('/comment/<string:blog_id>', methods = ['POST'])
@login_required
def comment(blog_id):
    content = request.form['content']
    new_comment = Comment(content=content, blog_id=blog_id, user=current_user)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('readmore', post_id=blog_id)) 
