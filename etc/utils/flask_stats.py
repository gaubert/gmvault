from flask import Flask

import scrapping
import json
import datetime

app = Flask(__name__)

@app.route("/")
def hello():
    return "error 404"

@app.route("/stats")
def stats():
    return scrapping.get_stats("JSON")


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8181)
    #app.run(debug=False, port=80)
