# app.py
import os
from dotenv import load_dotenv
from config import Config
from smtplib import SMTPException


from flask import Flask, render_template, jsonify, request, redirect, url_for, session, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import random
from sqlalchemy import func
from flask_login import current_user
from flask_migrate import Migrate
import smtplib
from flask import jsonify
from flask import redirect, url_for
from flask_login import  logout_user
from werkzeug.utils import secure_filename
from flask import send_from_directory
from flask import Flask, jsonify, abort
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import secrets
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mail import Mail, Message
import socket
import logging
import secrets


app = Flask(__name__)
app.config.from_object(Config)  # Load configuration from the Config class
load_dotenv()
mail = Mail(app)
otp_storage = {}  # Temporary storage for demonstration purposes


 # Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///retailsysx.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
bcrypt = Bcrypt(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    email = db.Column(db.String(120), unique=True, nullable=False)
    reset_token = db.Column(db.String(32), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    product_name = db.Column(db.String(80), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', back_populates='cart_items')

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    cart_items = db.relationship('CartItem', back_populates='product')
    order_items = db.relationship('OrderItem', back_populates='product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    product_name = db.Column(db.String(80), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', name='fk_order_item_product'), nullable=False)
    product = db.relationship('Product', back_populates='order_items')


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Integer)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email = db.relationship('Email', backref='admin')


'''
# make sure every user is logged in no matter the link
@app.before_request
def before_request():
    # Add routes that should be accessible without authentication
    exempt_routes = [
        'user_login_page', 'admin_login_page', 'login', 'subscribe', 'index', 'serve_static',
        'verify_otp', 'generate_otp', 'send_otp_email', 'add_user', 'send_otp',
        'add_admin_page', 'delete_admin', 'forgot_password', 'reset_password'  # Add the admin-related routes
    ]

    # Exempt static files from authentication
    if request.endpoint and request.endpoint.startswith('static'):
        return

    if request.endpoint not in exempt_routes and not current_user.is_authenticated:
        flash('Please log in to access this page.', 'warning')
        if request.endpoint in ['add_admin_page', 'delete_admin']:
            return redirect(url_for('admin_login_page'))
        else:
            return redirect(url_for('user_login_page'))

    # If the route is admin-related, check if the user is an admin
    if request.endpoint and request.endpoint in ['add_admin_page', 'delete_admin'] and not current_user.is_admin:
        abort(403)  # or redirect to a forbidden page, as appropriate

'''

# Customized Unauthorized error handler
@app.errorhandler(401)
def unauthorized_error(error):
    response = jsonify({'error': 'Unauthorized access', 'message': 'You need to login '})
    return response, 401

# Route that triggers an unauthorized access error
@app.route('/unauthorized')
def unauthorized_route():
    abort(401)


def generate_otp():
    # Generate a random 6-digit number
    return '{:06}'.format(random.randint(0, 999999))


# function to send OTP via email

def send_otp_email(email, otp):
    subject = "Retailsysx OTP"
    greeting = "Hello,"
    verification_code_text = "Your verification code:"
    verification_code = str(otp)
    warning = "Please do not share this code with anyone."
    operation_link = "If you did not initiate this operation, click [here](https://www.retailsysx.com/en/support) to disable your account and then click the link below to contact retailsysx Customer Service:"
    retailsysx_support_link = "Retailsysx Support"
    retailsysx_team = "Retailsysx Team"
    automated_message = "Automated message. Please do not reply."

    # Construct the HTML content for the email
    html_content = f"""
        <p>{subject}</p>
        <p>{greeting}</p>
        <p>{verification_code_text}</p>
        <span style="padding:5px 0;font-size:20px;font-weight:bolder;color:#e9b434">{verification_code}</span>
        <p>{warning}</p>
        <p>{operation_link} <a href="{retailsysx_support_link}">{retailsysx_support_link}</a></p>
        <p>{retailsysx_team}</p>
        <p>{automated_message}</p>
    """

    # Create and send the email message
    msg = Message(subject, recipients=[email])
    msg.html = html_content
    mail.send(msg)

@app.route('/')
def index():
    return render_template('index.html')

##USER LOGIN PAGE
@app.route('/user/user_login_page')
def user_login_page():
    return render_template('user/login.html')

#ADMIN LOGIN PAGE
@app.route('/admin/admin_login_page')
def admin_login_page():
    return render_template('admin/login.html')

##ADMIN PANEL
#  'send_otp' route
@app.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        email = request.form.get('email')

        # Check if the email exists in the Email model
        existing_email = Email.query.filter_by(email=email).first()
        if not existing_email:
            abort(400, "Email does not exist. Please register first.")

        otp = generate_otp()
        otp_storage[email] = otp  # Store OTP temporarily for verification

        print(f'Generated OTP for {email}: {otp}')

        send_otp_email(email, otp)
        return jsonify({"success": True, "message": "OTP sent successfully! Please check your email."})
    except (SMTPException, ConnectionResetError) as e:
        # Log the error for debugging purposes
        print(f"Error sending email: {e}")

        # Return an error response
        return jsonify({"error": "Failed to send OTP"}), 500



# verify otp
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    email_address = request.form.get('email')
    user_input = request.form.get('otp')

    stored_otp = otp_storage.get(email_address)

    logging.info(f"Verifying OTP for email: {email_address}, Stored OTP: {stored_otp}, User Input: {user_input}")

    if stored_otp and stored_otp == user_input:
        # Delete stored OTP
        del otp_storage[email_address]

        # Fetch the admin user from the database based on the email
        admin = Admin.query.filter(Admin.email.has(email=email_address)).first()

        if admin:
            # Set the is_admin attribute to True
            admin.is_admin = True
            db.session.commit()  # Save the changes to the database

            logging.info(f"Successful authentication for admin with email: {email_address}")
            return jsonify({"success": True, "message": "Authentication successful!"}), 302
        else:
            logging.error(f"Admin not found for email: {email_address}")
            return jsonify({"success": False, "message": "Admin not found."})
    else:
        logging.warning(f"Authentication failed for email: {email_address}")
        return jsonify({"success": False, "message": "Authentication failed."})


# admin page after admin login
@app.route('/admin_page')
def admin_page():
    emails = Email.query.all()  # Fetch all email addresses from the database
    return render_template('admin/templates/index.html', emails=emails)

# Add this route to your Flask app
@app.route('/admin/add', methods=['GET'])
def add_admin_page():
    admins = Admin.query.all()
    return render_template('admin/templates/add_admin.html', admins=admins)

# Add this route to your Flask app
# Add this route to your Flask app
@app.route('/admin/add', methods=['POST'])
def add_admin():
    name = request.form.get('name')
    email = request.form.get('email')
    is_admin = 'is_admin' in request.form  # Checkbox value

    # Fetch the email record or create a new one
    existing_email = Email.query.filter_by(email=email).first()
    if not existing_email:
        existing_email = Email(email=email)
        db.session.add(existing_email)
        db.session.commit()

    # Create the admin user
    new_admin = Admin(name=name, email_id=existing_email.id, is_admin=is_admin)
    db.session.add(new_admin)
    db.session.commit()

    flash('Admin user added successfully!', 'success')


    return redirect(url_for('add_admin_page'))

# Define a route for deleting admin
@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_admin(id):
    # Retrieve the admin with the specified ID from the database
    admin_to_delete = Admin.query.get(id)

    if admin_to_delete:
        # Delete the admin from the database
        db.session.delete(admin_to_delete)
        db.session.commit()

        flash('Admin user deleted successfully!', 'success')
    else:
        flash('Admin user not found!', 'error')

    # Redirect to the page displaying all admins
    return redirect(url_for('add_admin'))

#verify email for admin
@app.route('/main')
def main():
    if 'email' in session:
        email = session['email']
        return render_template('admin/index.html', email=email)
    else:
        return redirect(url_for('admin_page'))

#load current user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Add a route for serving other static files (images, etc.)
@app.route('/static/<path:filename>')
def serve_static(filename):
    root_dir = os.path.dirname(os.getcwd())
    return send_from_directory(os.path.join(root_dir, 'static'), filename)

# login
@app.route('/login_page')
def login_page():
    return render_template('login_main.html')

# login route to authenticate
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password'].strip()

    user = User.query.filter_by(username=username).first()
    print(f'Entered Username: {username}, Entered Password: {password}, User from DB: {user}')

    if user and check_password_hash(user.password, password):
        # Login the user
        login_user(user)
        # Redirect to the main page after successful login_main
        return redirect(url_for('user_main'))



    return render_template('user/templates/login_alert.html')


@app.route('/add_user_page')
def add_user_page():
    return render_template('user/templates/add_user.html')

# add new users on login page
@app.route('/add_user', methods=['POST'])
def add_user():
    new_username = request.form['new_username']
    new_password = request.form['new_password']
    new_email = request.form['new_email']

    if not new_username or not new_password:
        return 'Username and password are required.'

    hashed_password = generate_password_hash(new_password)

    # Check if the username already exists
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user:
        return jsonify({"status": "error",
                        "message": f'Username {new_username} already exists. Please choose a different username.'})

    # Check if the email already exists
    existing_email = User.query.filter_by(email=new_email).first()
    if existing_email:
        return jsonify({"status": "error",
                        "message": f'The email {new_email} is already registered. Please choose a different email.'})



    new_user = User(username=new_username, password=hashed_password, email=new_email)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": f'User {new_username} added successfully! \n you may now Login'})
    except Exception as e:
        print(f"Error adding user: {str(e)}")  # Print the error for debugging
        db.session.rollback()
        return jsonify({"status": "error", "message": f'Error adding user: {str(e)}'})


#route for logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# Define the get_products function
def get_products(search_query=None):
    # Fetch products from the database using SQLAlchemy
    if search_query:
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
        products = Product.query.all()

    # Create a list of dictionaries with the required attributes
    products_data = [
        {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image_filename': product.image_filename,  # Include the image_filename attribute
        }
        for product in products
    ]

    return products_data

@app.route('/static/images/products/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Route for the products page
@app.route('/products')
def products():
    # Get search query from the URL parameters
    search_query = request.args.get('search')

    # Get products data based on the search query
    products_data = get_products(search_query)

    # Pass the product data to the template
    return render_template('user/templates/products.html', products=products_data, product_in_cart=product_in_cart)




# Route to render the product management HTML
@app.route('/manage-products')
def manage_products():
    products = Product.query.all()
    return render_template('admin/templates/manage_products.html', products=products)

UPLOAD_FOLDER = 'static/images/products'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# Route to add a product
@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    name = request.form.get('product_name')
    price = float(request.form.get('product_price'))
    image = request.files.get('product_image')

    # Check if a file is selected
    if image is None or image.filename == '':
        return jsonify({"status": "error", "message": "No file selected for the product image"})

    # Check if the file type is allowed
    if not allowed_file(image.filename):
        return jsonify({"status": "error", "message": "Invalid file type. Allowed types are jpg, jpeg, png, gif"})

    try:
        new_product = Product(name=name, price=price)

        db.session.add(new_product)
        db.session.commit()

        # Save image to the file system
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER, str(new_product.id), filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)

        # Update the product's image_filename in the database
        new_product.image_filename = os.path.join(str(new_product.id), filename)
        db.session.commit()

        return redirect('/manage-products')
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Error adding product: {str(e)}"})


# Route to delete a product


@app.route('/delete-product', methods=['POST'])
def delete_product():
    product_id = request.form.get('product_id')

    # Fetch the product from the database
    product = Product.query.get(product_id)

    # Check if the product exists
    if product:
        try:
            # Check for and delete related order items
            order_items = OrderItem.query.filter_by(product_id=product_id).all()
            for order_item in order_items:
                db.session.delete(order_item)

            # Delete the associated image file
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

            # Delete the product from the database
            db.session.delete(product)

            # Commit the changes
            db.session.commit()

            return redirect('/manage-products')
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"Error deleting product: {str(e)}"})
    else:
        return jsonify({"status": "error", "message": "Product not found"})



# Route for the index page (main route)
@app.route('/user_main')
def user_main():
    # Get products data
    products_data = get_products()

    # Pass the product data to the template
    return render_template('user/templates/index.html', products=products_data)





# Route to view all email addresses
@app.route('/view-emails')
def view_emails():
    emails = Email.query.all()
    return render_template('admin/templates/view_emails.html', emails=emails)

# Route to add an email address
@app.route('/add-email', methods=['POST'])
def add_email():
    email_address = request.form.get('email')

    # Check if the email already exists
    existing_email = Email.query.filter_by(email=email_address).first()

    if existing_email:
        return jsonify({'success': False, 'message': 'Email already exists.'})
    else:
        new_email = Email(email=email_address)
        db.session.add(new_email)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email added successfully.'})

# Route to delete an email address
@app.route('/delete-email/<int:email_id>', methods=['POST'])
def delete_email(email_id):
    email = Email.query.get_or_404(email_id)
    db.session.delete(email)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Email deleted successfully.'})


@app.route('/about')
def about():
    return render_template('user/templates/about.html')


@app.route('/contact')
def contact():
    return render_template('user/templates/contact.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form['email']

        # Perform any necessary validation on the email address

        # Send email
        to_email = email  # Use the entered email address as the recipient
        subject = 'New Subscriber'

        # Make the message longer
        message = f'Thank you for subscribing to our newsletter!\n\n'
        message += f'We appreciate your interest and look forward to keeping you updated on our latest news and events.\n\n'
        message += f'Best regards,\nThe RetailsysX Team\n\n'
        message += f'---\nOriginal Email: {email}'
        message += f'\nUnsubscribe: https://www.retailsysx.com/unsubscribe'



         # Use environment variables for SMTP credentials
        smtp_server = os.getenv('MAIL_SERVER')
        smtp_port = int(os.getenv('MAIL_PORT'))
        smtp_username = os.getenv('MAIL_USERNAME')
        smtp_password = os.getenv('MAIL_PASSWORD')

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)

            server.sendmail(smtp_username, to_email, f'Subject: {subject}\n\n{message}')

        return 'Subscription successful'

# Route to add an item to the cart
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        print(f"Received data: {data}")  # inspect the received data
        product_name = data.get('name')
        quantity = data.get('quantity', 1)

        # Query the product to get the ID
        product = Product.query.filter_by(name=product_name).first()

        if not product:
            return jsonify(success=False, error=f"Product '{product_name}' not found"), 404

        # Check if the item is already in the cart
        existing_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()

        if existing_item:
            # Update the quantity if the item is already in the cart
            existing_item.quantity += quantity
        else:
            # Create a new cart item if the item is not in the cart
            new_cart_item = CartItem(
                user_id=current_user.id,
                product_name=product_name,
                product_price=product.price,
                quantity=quantity,
                product_id=product.id
            )

            db.session.add(new_cart_item)

        db.session.commit()

        return jsonify(success=True, message="Item added to cart successfully")

    except Exception as e:
        db.session.rollback()
        print(f"Error adding item to cart: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/view_cart')
@login_required
def view_cart():
    # Get the user's cart items
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()


    # Calculate the total
    total = db.session.query(func.sum(CartItem.product_price * CartItem.quantity)).filter_by(user_id=current_user.id).scalar()

    return render_template('user/templates/cart.html', cart_items=cart_items, total=total or 0)

# Add this route to app.py
@app.route('/delete_from_cart', methods=['POST'])
@login_required
def delete_from_cart():
    item_id = int(request.form.get('item_id'))
    cart_item = CartItem.query.get_or_404(item_id)

    try:
        db.session.delete(cart_item)
        db.session.commit()
        return redirect('/view_cart')
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Error deleting item from cart: {str(e)}"})


@app.route('/update_quantity', methods=['POST'])
@login_required
def update_quantity():
    try:
        item_id = int(request.form.get('item_id'))
        quantity = int(request.form.get('quantity'))

        # Check if the item is in the user's cart
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()

        if cart_item:
            # Update the quantity
            cart_item.quantity = quantity
            db.session.commit()

            return redirect('/view_cart')  # Redirect to the cart page
        else:
            return jsonify(success=False, error='Item not found in the cart'), 404

    except Exception as e:
        db.session.rollback()
        print(f"Error updating quantity: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

# function to check if a product is in the cart
def product_in_cart(product_name):
    if current_user.is_authenticated:
        return CartItem.query.filter_by(user_id=current_user.id, product_name=product_name).first() is not None
    return False


# Modify the delete_user_page route
@app.route('/delete_user_page')
@login_required
def delete_user_page():
    users = User.query.all()
    return render_template('admin/templates/user.html', users=users)

# Add this route to delete the user
@app.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    user_id = request.form.get('user_id')

    # Find the user in the database
    user = User.query.get(user_id)

    if user:
        try:
            # Delete the user from the database
            db.session.delete(user)
            db.session.commit()

            return redirect(url_for('delete_user_page'))
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"Error deleting user: {str(e)}"})
    else:
        return jsonify({"status": "error", "message": "User not found."})

# Add this route to add a new user in the admin panel
@app.route('/register_user', methods=['POST'])
@login_required
def register_user():
    new_username = request.form['new_username']
    new_password = request.form['new_password']
    new_email = request.form['new_email']


    if not new_username or not new_password or not new_email:
        return 'Username and password are required.'

    hashed_password = generate_password_hash(new_password)

    # Check if the username already exists
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user:
        return jsonify({"status": "error",
                        "message": f'Username {new_username} already exists. Please choose a different username.'})

    # Check if the email already exists
    existing_email = User.query.filter_by(email=new_email).first()
    if existing_email:
        return jsonify({"status": "error",
                        "message": f'The email {new_email} is already registered. Please choose a different email.'})



    new_user = User(username=new_username, password=hashed_password, email=new_email)

    try:
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('delete_user_page'))
    except:
        db.session.rollback()
        return jsonify({"status": "error", "message": f'Username {new_username} already exists. Please choose a different username.'})


# Update the order_confirmation route
@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    # Fetch the order and order items from the database
    order = Order.query.get_or_404(order_id)
    order_items = OrderItem.query.filter_by(order_id=order_id).all()

    # Render the order confirmation template
    return render_template('user/templates/order.html', order=order, order_items=order_items, user=current_user)

def calculate_total(user_id):
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    return sum(item.product_price * item.quantity for item in cart_items)




# Update the process_order route
@app.route('/process_order/<int:user_id>', methods=['GET', 'POST'])
@login_required
def process_order(user_id):
    # Get the items from the form submission
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    # Check if the cart is empty
    if not cart_items:
        flash('Your cart is empty. Add items before placing an order.', 'warning')
        return redirect(url_for('view_cart'))

    # Calculate the total
    total = sum(item.product_price * item.quantity for item in cart_items)

    # Create a new order only if the cart is not empty
    new_order = Order(user_id=user_id, total=total)
    db.session.add(new_order)
    db.session.commit()

    # Add order items
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_name=item.product_name,
            product_price=item.product_price,
            quantity=item.quantity,
            product_id =item.product_id
        )
        db.session.add(order_item)

    # Clear the user's cart
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    # Redirect to the order confirmation page with the order ID
    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_confirmation', order_id=new_order.id, user=current_user))


# Modify the route where you process the order
@app.route('/process_order', methods=['POST'])
@login_required
def process_order_route():
    # Pass the id of the current user to the process_order route
    return render_template('user/templates/order_details_form.html', user=current_user)



# Modify the submit_order route
@app.route('/submit_order', methods=['POST'])
@login_required
def submit_order():
    try:
        # Get user details from the form submission
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        # Get other user details fields as needed

        # Check if the cart is empty
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty. Add items before placing an order.', 'warning')
            return redirect(url_for('view_cart'))

        # Calculate the total
        total = sum(item.product_price * item.quantity for item in cart_items)

        # Create a new order
        new_order = Order(
            user_id=current_user.id,
            total=total,
            full_name=full_name,
            address=address,
            # Set other user details fields as needed
        )
        db.session.add(new_order)
        db.session.commit()

        # Add order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_name=item.product_name,
                product_price=item.product_price,
                quantity=item.quantity,
                product_id=item.product_id  # Include the product_id in OrderItem
            )
            db.session.add(order_item)

        # Clear the user's cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # Redirect to the order confirmation page with the order ID
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=new_order.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error placing order: {str(e)}', 'danger')
        return redirect(url_for('view_cart'))

# Update the all_orders route
@app.route('/all_orders')
@login_required
def all_orders():
    # Fetch all orders from the database
    orders = Order.query.all()

    # Render the all orders template
    return render_template('admin/templates/admin_order.html', orders=orders)

@app.route('/navigate_to_all_orders')
@login_required
def navigate_to_all_orders():
    return redirect(url_for('all_orders'))


@app.route('/pay/<int:order_id>')
def pay(order_id):
    # Fetch the order and order items from the database
    order = Order.query.get_or_404(order_id)
    order_items = OrderItem.query.filter_by(order_id=order_id).all()

    # Render the pay template
    return render_template('user/templates/pay.html', order=order, order_items=order_items, user=current_user)


# Modify the cancel_order route to redirect to the products page
@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    # Fetch the order from the database
    order = Order.query.get_or_404(order_id)

    # Check if the logged-in user is the owner of the order
    if current_user.id != order.user_id:
        return jsonify({"status": "error", "message": "You don't have permission to cancel this order."}), 403

    try:
        # Delete the order and associated order items from the database
        OrderItem.query.filter_by(order_id=order.id).delete()
        db.session.delete(order)
        db.session.commit()

        return redirect(url_for('products'))  # Redirect to the products page after cancellation
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Error canceling order: {str(e)}"}), 500


@app.route('/forgot_pass')
def forgot_pass():
    return render_template('user/templates/forgot_password.html')

def generate_reset_token():
    return secrets.token_urlsafe(32)


def send_reset_email(user):
    token = generate_reset_token()
    user.reset_token = token
    user.reset_token_expiration = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()

    msg = Message('Password Reset Request', sender='your@gmail.com', recipients=[user.email])
    msg.body = f'To reset your password, click the following link: {url_for("reset_password", token=token, _external=True)}'
    mail.send(msg)


def handle_socket_error():
    flash('Unable to send email. Please check your internet connection.', 'error')
    return jsonify({'error': 'Unable to send email. Please check your internet connection.'})

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        try:
            if user:
                send_reset_email(user)
                flash('An email has been sent with instructions to reset your password.', 'info')
                # return jsonify({'message': 'Email sent successfully', 'type': 'success'})
            else:
                flash('Email not found. Please check your email address.', 'danger')
        except socket.gaierror as e:
            flash('Unable to send email. Please check your internet connection.', 'error')
            # return jsonify({'message': 'Unable to send email. Please check your internet connection.', 'type': 'error'})

    return render_template('user/templates/forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if user and user.reset_token_expiration > datetime.utcnow():
        if request.method == 'POST':
            new_password = request.form.get('password')
            if not new_password:
                flash('Password is required.', 'danger')
                return redirect(url_for('reset_password', token=token))

            # Use the same hashing method used when adding the user
            user.password = generate_password_hash(new_password)

            user.reset_token = None
            user.reset_token_expiration = None

            db.session.commit()

            flash('Your password has been reset successfully. You can now log in.', 'success')
            # return redirect(url_for('login'))

        return render_template('user/templates/reset_password.html', token=token)

    else:
        flash('Invalid or expired token. Please try again.', 'danger')
        return redirect(url_for('forgot_password'))




if __name__ == '__main__':
    app.run(debug=True)
