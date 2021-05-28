# thaw_app.py
#
# Thaws upgraded (premium) user data
#
# Copyright (C) 2011-2021 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import json
import os

from flask import Flask

app = Flask(__name__)
environment = 'thaw_app_config.Config'
app.config.from_object(environment)
app.url_map.strict_slashes = False

@app.route('/', methods=['GET'])
def home():
	return (f"This is the Thaw utility: POST requests to /thaw.")

@app.route('/thaw', methods=['POST'])
def thaw_premium_user_data():
	print("thaw endpoint it")

### EOF
