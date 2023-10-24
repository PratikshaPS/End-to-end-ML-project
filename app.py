from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_cors import cross_origin
import PIL
from PIL import Image
from werkzeug.utils import secure_filename
import sklearn
import pickle
import pandas as pd
import xgboost as xgb
from xgboost import XGBRegressor
from datetime import datetime,date
from pandas import MultiIndex, Int64Index

app = Flask(__name__)

model = pickle.load(open("model_rf.pkl", "rb"))

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Pr@tiksha12345'
app.config['MYSQL_DB'] = 'LoginDB'

mysql = MySQL(app)

class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')
    
    def validate_username(self, username):
        if username.data != session['username']:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                'Select * from accounts where username = %s', (username, ))
            account = cursor.fetchone()
            if account:
                return ('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != session['email']:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                'Select * from accounts where email = %s', (email, ))
            account = cursor.fetchone()
            if account:
                return ('That email is taken. Please choose a different one.')


@app.route('/home')
def home():
    return render_template('index.html')


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'Select * from accounts where username = %s and password = %s', (username, password, ))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']
            msg = 'Logged in successfully!'
            return redirect(url_for('home'))
        else:
            msg = 'Wrong username/password'
    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('id')
    session.pop('username')
    session.pop('email')
    return redirect(url_for('login'))



@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        profile_image = 'user1'
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email, profileimage) VALUES (% s, % s, % s, %s)', (username, password, email, profile_image, ))
            mysql.connection.commit()
            msg = 'You have registered successfully!'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)


'''
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'Select * from accounts where username = %s', (username, ))
        print(username)
        account = cursor.fetchone()
        print(account)
        if account:
            msg = 'Account already exists! Try to Login'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
            print('Im inside else')
            cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', (username, password, email, ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
        print(msg)
    elif request.method == 'POST':
        msg = 'Please fill out the form.'
    return render_template('register.html', msg=msg)
'''

def save_picture(form_picture):
    '''
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    '''
    picture_fn = request.files['picture']
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn



@app.route("/account", methods=['GET', 'POST'])
def account():
    msg = ''
    image_file = ''
    form = UpdateAccountForm()
    if request.method == 'POST' :
        if request.files['picture'] :
            f = request.files['picture']
            f.save(os.path.join('static/profile_pics/', secure_filename(f.filename)))
            image_file = f.filename
            session['profileimage'] = image_file
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'Select * from accounts where username = %s', (session['username'], ))
        account = cursor.fetchone()
        if account:
            cursor.execute('UPDATE accounts SET username = %s, email = %s, profileimage = %s WHERE username = %s' , 
                           (request.form['username'], request.form['email'], image_file, session['username']))
            
            mysql.connection.commit()
            
            msg = 'Your profile has been updated successfully!'
            
            image_file = url_for('static', filename='profile_pics/' + account['profileimage'])
        return render_template('account.html', msg=msg, form=form, image_file=image_file)
    elif request.method == "GET" :
        form.username.data = session['username']
        form.email.data = session['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'Select * from accounts where username = %s', (session['username'], ))
        account = cursor.fetchone()
        image_file = url_for('static', filename='profile_pics/' + account['profileimage'])
    return render_template('account.html', msg=msg, form=form, image_file=image_file)

@app.route("/predict", methods=["GET", "POST"])
@cross_origin()
def predict():
    if request.method == "POST":

        # Date_of_Journey
        Dep_date = datetime.strptime(request.form["Dep_date"], '%Y-%m-%d').date()
        current_date = date.today()
        print("Today's date:", current_date)
        print("Journey Date : ",Dep_date, type(Dep_date))
        print((Dep_date-current_date).days, " days")
        
        # Departure
        #Dep_hour = int(pd.to_datetime(date_dep, format="%Y-%m-%dT%H:%M").hour)
        #Dep_min = int(pd.to_datetime(date_dep, format="%Y-%m-%dT%H:%M").minute)
        # print("Departure : ",Dep_hour, Dep_min)

        # Arrival
        #date_arr = request.form["Arrival_Time"]
        #Arrival_hour = int(pd.to_datetime(date_arr, format="%Y-%m-%dT%H:%M").hour)
        #Arrival_min = int(pd.to_datetime(date_arr, format="%Y-%m-%dT%H:%M").minute)
        # print("Arrival : ", Arrival_hour, Arrival_min)

        # Duration
        # dur_hour = abs(Arrival_hour - Dep_hour)
        # dur_min = abs(Arrival_min - Dep_min)
        # print("Duration : ", dur_hour, dur_min)

        # Total Stops
        Total_stops = int(request.form["stops"])
        print(Total_stops)

        # Total Stops
        duration_h = int(request.form["duration"])
        print(duration_h)

        # Airline
        # AIR ASIA = 0 (not in column)
        
        Air_India = 0
        AirAsia = 0
        GO_FIRST = 0
        IndiGo = 0
        SpiceJet = 0
        Vistara = 0
        
        source_Bangalore = 0
        source_Chennai = 0
        source_Delhi = 0
        source_Hyderabad = 0
        source_Kolkata = 0
        source_Mumbai = 0

        destination_Bangalore = 0
        destination_Chennai = 0
        destination_Delhi = 0
        destination_Hyderabad = 0
        destination_Kolkata = 0
        destination_Mumbai = 0

        zero_two = 0
        eleven_fifteen  = 0
        fifteen_fortyeight = 0
        three_nine = 0
        
        dep_Early_Morning = 0
        dep_Eve = 0
        dep_Late_Night = 0
        dep_Morning = 0
        dep_Night = 0
        dep_Noon = 0
        
        arr_Early_Morning = 0
        arr_Eve = 0
        arr_Late_Night = 0
        arr_Morning = 0
        arr_Night = 0
        arr_Noon = 0

        # airline
        airline = request.form['airline']
        if (airline == 'Air India'):
            Air_India = 1
        elif (airline == 'IndiGo'):
            IndiGo = 1
        elif (airline == 'SpiceJet'):
            SpiceJet = 1
        elif (airline == 'Vistara'):
            Vistara = 1
        elif (airline == 'Go FIRST'):
            Go_FIRST = 1
        elif (airline == 'AirAsia'):
            AirAsia = 1

        # Source
        Source = request.form["Source"]
        if (Source == 'Delhi'):
            source_Delhi = 1
        elif (Source == 'Kolkata'):
            source_Kolkata = 1
        elif (Source == 'Mumbai'):
            source_Mumbai = 1
        elif (Source == 'Chennai'):
            source_Chennai = 1
        elif (Source == 'Bangalore'):
            source_Bangalore = 1
        elif (Source == 'Hyderabad'):
            source_Bangalore = 1

        # Destination
        # Banglore = 0 (not in column)
        Destination = request.form["Destination"]
        if (Destination == 'Delhi'):
            destination_Delhi = 1
        elif (Destination == 'Kolkata'):
            destination_Kolkata = 1
        elif (Destination == 'Mumbai'):
            destination_Mumbai = 1
        elif (Destination == 'Chennai'):
            destination_Chennai = 1
        elif (Destination == 'Bangalore'):
            destination_Bangalore = 1
        elif (Destination == 'Hyderabad'):
            destination_Hyderabad = 1

        '''
        if row['days_to_dep'] >= 0 and row['days_to_dep'] < 3:
            return '0-2 Days'
        elif row['days_to_dep'] >= 3 and row['days_to_dep'] <= 10:
            return '3-9 Days'
        elif row['days_to_dep'] >= 11  and row['days_to_dep'] <= 15:
            return '11-15 Days'
        elif row['days_to_dep'] > 15  and row['days_to_dep'] <= 48:
            return '15-48 Days'
    '''
    
        # Stopage
        # Banglore = 0 (not in column)
        stops = request.form["stops"]
        if (stops == 'Delhi'):
            zero_two = 1
        elif (stops == 'Kolkata'):
            eleven_fifteen = 1
        elif (stops == 'Mumbai'):
            fifteen_fortyeight = 1
        elif (stops == 'Chennai'):
            three_nine = 1

        # Destination
        # Banglore = 0 (not in column)
        Destination = request.form["Destination"]
        if (Destination == 'Delhi'):
            destination_Delhi = 1
        elif (Destination == 'Kolkata'):
            destination_Kolkata = 1
        elif (Destination == 'Mumbai'):
            destination_Mumbai = 1
        elif (Destination == 'Chennai'):
            destination_Chennai = 1
        elif (Destination == 'Bangalore'):
            destination_Bangalore = 1
        elif (Destination == 'Hyderabad'):
            destination_Hyderabad = 1

        prediction = model.predict([[
            Total_stops,
            duration_h,
           # Air_India,
            AirAsia,
            GO_FIRST,
            IndiGo,
            SpiceJet,
            Vistara,
           # source_Bangalore,
            source_Chennai,
            source_Delhi,
            source_Hyderabad,
            source_Kolkata,
            source_Mumbai,
           # destination_Bangalore,
            destination_Chennai,
            destination_Delhi,
            destination_Hyderabad,
            destination_Kolkata,
            destination_Mumbai,
           # zero_two,
            eleven_fifteen,
            fifteen_fortyeight,
            three_nine,
           # dep_Early_Morning,
            dep_Eve,
            dep_Late_Night,
            dep_Morning,
            dep_Night,
            dep_Noon,
           # arr_Early_Morning,
            arr_Eve,
            arr_Late_Night,
            arr_Morning,
            arr_Night,
            arr_Noon
        ]])

        output = round(prediction[0], 2)

        return render_template('index.html', prediction_text="Your Flight price is Rs. {}".format(output))

    return render_template("index.html")

if __name__ == "__main__":
    app.config['SECRET_KEY'] = 'development key'

    #login_manager = LoginManager(app)
    #login_manager.init_app(app)

    app.run(debug=False)