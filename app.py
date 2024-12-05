from flask import Flask, render_template, request, redirect, url_for,jsonify, session
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
from PIL import Image
import numpy as np
from tempfile import NamedTemporaryFile
from pymongo import MongoClient


app = Flask(__name__)
app.secret_key = 'abcd1234'

# Load the model from the file
model = load_model('Models/dishid_model1.h5')

#DB Connection
mongodb_uri = 'mongodb+srv://harshanabuddhika9:uh4Av1QRBqmhXjwL@cluster0.bgvrx7w.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
# Ensure the connection string is not None
if not mongodb_uri:
    raise ValueError("No MongoDB URI found. Please set MONGODB_URI in the environment variables.")

client = MongoClient(mongodb_uri)
db = client['Dish'] 
user_collection = db['user_collection']
past_analysis_collection = db['past_analysis_collection']

#-------------------------------------------------------------- Page Load-------------------------------------------------------------------
# Login Page
@app.route('/')
def index():
    return render_template('login.html')

#Register Page
@app.route('/register_load')
def register():
    return render_template('register.html')

#Home Page
@app.route('/home', methods=['GET','POST'])
def home():
    return render_template('home.html')

# Analysis Page
@app.route('/analysis')
def about():
    return render_template('analysis.html')

#-------------------------------------------------------------------------------------------------------------------------------------------

#----------------------------------------------------------- Form Handling --------------------------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Query the database to find the user with the provided username
    user = user_collection.find_one({"User_name": username})

    if user and user['Password'] == password:
        # If the user is found and passwords match, return success
        session['username'] = username
        return jsonify({"status": "Success"}), 200
    else:
        # If no user is found or passwords don't match, return an error message
        return jsonify({"status": "Error", "message": "Invalid username or password"}), 400


@app.route('/registration', methods=['POST'])
def registration():
        First_name = request.form['firstname']
        Last_name = request.form['lastname']
        User_name = request.form['username']
        Email = request.form['email']
        Password = request.form['password']

        # Check if the email or username already exists
        existing_user = user_collection.find_one({"Email": Email})
        if existing_user:
            return jsonify({"status": "Error", "message": "Email already registered"}), 400
        
        # Optionally, you might want to also check for username uniqueness
        existing_user_by_username = user_collection.find_one({"User_name": User_name})
        if existing_user_by_username:
            return jsonify({"status": "Error", "message": "Username already taken"}), 400

        db_payload = {
            "First_name": First_name,
            "Last_name": Last_name,
            "User_name": User_name,
            "Email": Email,
            "Password": Password
        }

        #print("Received payload:", db_payload)  # For debugging

        if db_payload:
            user_collection.insert_one(db_payload)
            session['username'] = User_name
            return jsonify({"status": "Success"}), 200
        else:
            return jsonify({"status": "No data provided"}), 400

@app.route('/submit', methods=['POST'])
def submit():
    
    if 'file' not in request.files:
        return "No file part in the request", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    try:
        # Validate the uploaded file using Pillow
        with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        with Image.open(temp_file_path) as img:
            # Convert image to RGB (handles grayscale, RGBA, etc.)
            img = img.convert('RGB')
            img = img.resize((224, 224))  # Resize to target dimensions

            # Convert to a NumPy array for model compatibility
            img_array = np.array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0  # Normalize pixel values

        # Make a prediction
        predictions = model.predict(img_array)
        predicted_class = np.argmax(predictions, axis=1)

        # Define class mapping
        class_mapping = {
            0: 'Butter naan',
            1: 'Chapati',
            2: 'Fried Rice',
            3: 'Idli',
            4: 'Kadai Paneer',
            5: 'Masala Dosa',
            6: 'Paani Puri',
            7: 'Pakode',
            8: 'Samosa'
        }

        # Map each class to a corresponding PDF file
        recipe_pdfs = {
            'Butter naan': 'Butter_naan.pdf',
            'Chapati': 'Chapati.pdf',
            'Fried Rice': 'Fried_Rice.pdf',
            'Idli': 'Idli.pdf',
            'Kadai Paneer': 'Kadai_Paneer.pdf',
            'Masala Dosa': 'Masala_Dosa.pdf',
            'Paani Puri': 'Paani_Puri.pdf',
            'Pakode': 'Pakode.pdf',
            'Samosa': 'Samosa.pdf'
        }


        predicted_class_name = class_mapping.get(predicted_class[0], 'Unknown')
        recipe_pdf = recipe_pdfs.get(predicted_class_name, None)

        #print(recipe_pdf)

        username = session.get('username')
        db_payload = {
            'Username':username,
            'Food_Item':predicted_class_name,
        }
        past_analysis_collection.insert_one(db_payload)    
        return render_template('results.html',
                               food_item = predicted_class_name,
                               pdf_name = recipe_pdf
                               )
    
    except IOError:
        return "The uploaded file is not a valid image.", 400
    except Exception as e:
        return f"Error processing the image: {str(e)}", 500
    
@app.route('/pastanalysis', methods=['POST','GET'])
def pastanalysis():
    username = session.get('username')
    analysis_collection = list(past_analysis_collection.find({'Username':username}))
    context = {
        'analysis_collection':analysis_collection
    }

    return render_template('pastanalysis.html', **context)

@app.route('/print', methods=['GET'])
def print():
    
    food_item_name = request.args.get('food_item')

    recipe_pdfs = {
            'Butter naan': 'Butter_naan.pdf',
            'Chapati': 'Chapati.pdf',
            'Fried Rice': 'Fried_Rice.pdf',
            'Idli': 'Idli.pdf',
            'Kadai Paneer': 'Kadai_Paneer.pdf',
            'Masala Dosa': 'Masala_Dosa.pdf',
            'Paani Puri': 'Paani_Puri.pdf',
            'Pakode': 'Pakode.pdf',
            'Samosa': 'Samosa.pdf'
        }
    
    recipe_pdf = recipe_pdfs.get(food_item_name, None)
    return render_template('results.html',
                               food_item = food_item_name,
                               pdf_name = recipe_pdf
                               )
    

@app.route('/delete', methods=['GET','POST'])
def delete():
    food_item_name = request.args.get('food_item')
    username = session.get('username')

    past_analysis_collection = db['past_analysis_collection']

    # Ensure both food_item_name and user_name are present
    if food_item_name and username:
        delete_result = past_analysis_collection.delete_one({
            'Username': username,
            'Food_Item': food_item_name
        })

        # Check if a document was deleted
        if delete_result.deleted_count > 0:
            message = f"Successfully deleted {food_item_name} for user {username}."
        else:
            message = "No matching record found to delete."
    else:
        message = "Missing food_item or username."

    analysis_collection = list(past_analysis_collection.find({'Username':username}))
    context = {
        'analysis_collection':analysis_collection
    }

    return render_template('pastanalysis.html', **context)

#-----------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
