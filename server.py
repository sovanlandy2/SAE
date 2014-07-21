from flask import Flask, render_template, request, jsonify, make_response
from info import classify2
from math import e
from redis import Redis
from config import STATS_KEY, HOST, RHOST, RPASS, RPORT
from cors import crossdomain
from datetime import datetime
import json

app = Flask(__name__)
app.debug = False
app.config['MAX_CONTENT_LENGTH'] = (1 << 20) # 1 MB max request size
conn = Redis(RHOST, RPORT, password=RPASS)

def percentage_confidence(conf):
	return 100.0 * e ** conf / (1 + e**conf)

def today():
	return datetime.now().strftime('%Y-%m-%d')

def get_sentiment_info(text):
	flag, confidence, pos_score, neg_score = classify2(text)
	print "positive score: = %.9f" % pos_score
	print "negative score: = %.9f" % neg_score

	sentiment = "Empty"
	score = 0
	if confidence > 0.5:
		if flag: 
			sentiment = "Positive" 
			score = e**pos_score / (1+e**pos_score)
		else: 
			sentiment = "Negative"
			score = e**neg_score / -(1+e**neg_score)
	else:
		sentiment = "Neutral"
		score = 0
  
	conf = "%.4f" % percentage_confidence(confidence)
	return (sentiment, conf, score)

@app.route('/')
def home():
	conn.incr(STATS_KEY + "_hits")
	return render_template("index.html")

@app.route('/api/text/', methods=["POST"])
@crossdomain(origin='*')
def read_api():
	text = request.form.get("txt")
	sentiment, confidence, score = get_sentiment_info(text)
	result = {"sentiment": sentiment,"score": score, "confidence": confidence}
	conn.incr(STATS_KEY + "_api_calls")
	conn.incr(STATS_KEY + today())
	print "WE are in side read API "
	print jsonify(result=result)
	return jsonify(result=result)

@app.route('/web/text/', methods=["POST"])
@crossdomain(origin='*')
def evaldata():
	text = request.form.get("txt")
	result, confidence = get_sentiment_info(text)
	conn.incr(STATS_KEY + "_web_calls")
	conn.incr(STATS_KEY + today())
	return jsonify(result=result, confidence=confidence, sentence=text)

@app.route('/api/batch/', methods=["POST"])
@crossdomain(origin='*')
def batch_handler():
	json_data = request.get_json(force=True, silent=True)
	if not json_data:
		return jsonify(error="Bad JSON request")
	result = []
	for req in json_data:
		sent, conf = get_sentiment_info(req)
		result.append({"result": sent, "confidence": conf})

	conn.incrby(STATS_KEY + "_api_calls", len(json_data))
	conn.incrby(STATS_KEY + today(), len(json_data))
	resp = make_response(json.dumps(result))
	resp.mimetype = 'application/json'

	return resp

@app.route('/docs/api/')
def api():
	return render_template('api.html', host=HOST)

@app.route('/about/')
def about():
	return render_template('about.html')
