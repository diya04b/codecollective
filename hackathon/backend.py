from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)
app.secret_key = "hello"
app.config['SQLALCHEMY_BINDS'] = {
    'hsm': 'mysql://root:anjanawatal%40240405@10.79.2.89:3306/hsm'
}
db = SQLAlchemy(app)


# Define the models
class Patient(db.Model):
    __bind_key__ = 'hsm'
    id = db.Column(db.String(50), unique=True, nullable=False, primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    phoneNumber = db.Column(db.String(15))
    emailid = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)


class Beds(db.Model):
    __bind_key__ = 'hsm'
    wardID = db.Column(db.String(50), primary_key=True)
    totalNumberOfBeds = db.Column(db.Integer, nullable=False)
    bedsAvailable = db.Column(db.Integer, nullable=False)


class bed_ids(db.Model):
    __bind_key__ = 'hsm'
    bedID = db.Column(db.String(50), primary_key=True)
    wardID = db.Column(db.String(50), db.ForeignKey('Beds.wardID'))
    patientID = db.Column(db.String(50), nullable=True)


# Index route
@app.route('/')
def index():
    if "user" in session:
        return render_template("index.html", visited=1)
    return render_template("index.html")


# Signup route
@app.route('/Signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        phoneNumber = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not phoneNumber or not email or not password:
            flash("All fields are required!")
            return render_template("Signup.html", visited=0)

        id = str(uuid.uuid4())
        user = Patient.query.filter_by(emailid=email).first()
        if user:
            flash("Email already exists. Please use a different email.")
            return render_template("Signup.html", visited=0)
        else:
            new_user = Patient(
                id=id,
                name=name,
                password=password,
                phoneNumber=phoneNumber,
                emailid=email,
            )
            db.session.add(new_user)
            db.session.commit()
            session['user'] = name
            return render_template('index.html', visited=1)
    return render_template("Signup.html", visited=0)


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form.get('userID')
        password = request.form.get('password')
        join_as = request.form.get('joinAs')
        ad = 1 if join_as == 'Admin' else 0

        if not userid or not password:
            flash("Both fields are required!")
            return render_template("login.html")

        user = Patient.query.filter_by(id=userid).first()
        if user is None:
            flash("User ID not found. Please create an account first.")
            return render_template("login.html")
        elif user.password != password:
            flash("Wrong username or password.")
            return render_template("login.html")
        else:
            session['user'] = user.name
            if ad == 1:
                return render_template("discharge.html")
            return render_template('index.html', visited=1)
    return render_template("login.html")


# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return render_template('index.html', visited=0)


# Bed booking route
@app.route('/bed', methods=['GET', 'POST'])
def bed():
    if request.method == 'GET':
        beds_data = Beds.query.all()
        return render_template('bed.html', beds_data=beds_data)

    if request.method == 'POST':
        ward_id = request.form.get('ward_id')
        patient_id = request.form.get('patient_id')

        if not ward_id or not patient_id:
            flash('Ward ID or Patient ID is missing!')
            return render_template('bed.html')

        bed_record = Beds.query.filter_by(wardID=ward_id).first()

        if bed_record:
            if bed_record.bedsAvailable > 0:
                bed_record.bedsAvailable -= 1
                available_bed = bed_ids.query.filter_by(wardID=ward_id, patientID=None).first()

                if available_bed:
                    available_bed.patientID = patient_id
                    db.session.commit()
                    flash(f"Bed {available_bed.bedID} in ward {ward_id} booked for patient {patient_id}.")
                else:
                    flash('No available beds in the ward.')
            else:
                flash('No available beds. Cannot book at this time.')

            return render_template('bed.html', beds_data=Beds.query.all())
        else:
            flash('Ward ID not found.')
            return render_template('bed.html', beds_data=Beds.query.all())


# Discharge route
@app.route('/discharge', methods=['GET', 'POST'])
def discharge():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')

        if not patient_id:
            flash('Patient ID is missing!')
            return render_template("discharge.html")

        patient_bed = bed_ids.query.filter_by(patientID=patient_id).first()
        if patient_bed:
            ward_id = patient_bed.wardID
            patient_bed.patientID = None
            db.session.commit()

            # Check if there are any patients who need a bed in this ward
            available_bed = bed_ids.query.filter_by(wardID=ward_id, patientID=None).first()
            if available_bed:
                # Assign the freed bed to the first patient needing a bed
                patient_to_reassign = bed_ids.query.filter_by(wardID=ward_id, patientID=None).first()
                if patient_to_reassign:
                    patient_to_reassign.patientID = patient_id
                    db.session.commit()

            flash('Patient discharged and bed reassigned if necessary.')
            return render_template("discharge.html")
        else:
            flash('No bed found for this patient ID.')
            return render_template("discharge.html")

    return render_template('discharge.html')
@app.route('/opd')
def op():
    return render_template("opd.html")

@app.route('/pharma')
def pharma():
    return render_template("pharmacy.html")
# Run the app
if __name__ == "__main__":
    app.run(debug=True)