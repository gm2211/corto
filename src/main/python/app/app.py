from flask import Flask, render_template, jsonify

app = Flask(__name__)

# This would eventually come from your actual boat sensors/GPS
def get_boat_location():
    return {
        "lat": 43.7696,  # Example: Portland, ME coordinates
        "lng": -70.2544,
        "heading": 45  # Example: heading in degrees
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/boat-location')
def boat_location():
    return jsonify(get_boat_location())

if __name__ == '__main__':
    app.run(debug=True) 