import pandas as pd
import numpy as np
import matplotlib.pylab as plt
#matplotlib inline
from matplotlib.pylab import rcParams
rcParams['figure.figsize'] = 15, 6



from pandas import Series
from pandas import concat
from pandas import read_csv
from pandas import datetime
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from math import sqrt
from matplotlib import pyplot
import numpy
import requests


import json

def predict(d):
	listy = []
	listy2 = []
	for result in d['results']:
		d1 = result['date']['local']
    		d2 = result['value']
    		listy.append(d1)
    		listy2.append(d2)

	
	df = pd.DataFrame(listy,columns = ['local'])
	print listy

	df2 = pd.DataFrame(listy2, columns = ['value'])

   
	df = pd.concat([df,df2],axis=1)
	

	data = df
	print data
	data['local'] = pd.to_datetime(data['local'])


	data = data.iloc[:100]
	ts = data['value']

	data2 = pd.concat([data.local,ts],axis = 1)

	data = data2
	data.index = data.local
	#data = data.sort_values(by='Sampling Date')
	del data['local']
	data.head

	ts = data
	

	train_size = int(len(ts) * 0.66)

# frame a sequence as a supervised learning problem
	def timeseries_to_supervised(data, lag=1):
		df = pd.DataFrame(data)
		columns = [df.shift(i) for i in range(1, lag+1)]
		columns.append(df)
		df = concat(columns, axis=1)
		df.fillna(0, inplace=True)
		return df
	 
	# create a differenced series
	def difference(dataset, interval=1):
		diff = list()
		for i in range(interval, len(dataset)):
			value = dataset[i] - dataset[i - interval]
			diff.append(value)
		return Series(diff)
	 
	# invert differenced value
	def inverse_difference(history, yhat, interval=1):
		return yhat + history[-interval]
	 
	# scale train and test data to [-1, 1]
	def scale(train, test):
		# fit scaler
		scaler = MinMaxScaler(feature_range=(-1, 1))
		scaler = scaler.fit(train)
		# transform train
		train = train.reshape(train.shape[0], train.shape[1])
		train_scaled = scaler.transform(train)
		# transform test
		test = test.reshape(test.shape[0], test.shape[1])
		test_scaled = scaler.transform(test)
		return scaler, train_scaled, test_scaled
	 
	# inverse scaling for a forecasted value
	def invert_scale(scaler, X, value):
		new_row = [x for x in X] + [value]
		array = numpy.array(new_row)
		array = array.reshape(1, len(array))
		inverted = scaler.inverse_transform(array)
		return inverted[0, -1]
	 
	# fit an LSTM network to training data
	def fit_lstm(train, batch_size, nb_epoch, neurons):
		X, y = train[:, 0:-1], train[:, -1]
		X = X.reshape(X.shape[0], 1, X.shape[1])
		model = Sequential()
		model.add(LSTM(neurons, batch_input_shape=(batch_size, X.shape[1], X.shape[2]), stateful=True))
		model.add(Dense(1))
		model.compile(loss='mean_squared_error', optimizer='adam')
		for i in range(nb_epoch):
			
			model.fit(X, y, epochs=1, batch_size=batch_size, verbose=0, shuffle=False)
			model.reset_states()
		return model
	 
	# make a one-step forecast
	def forecast_lstm(model, batch_size, X):
		X = X.reshape(1, 1, len(X))
		yhat = model.predict(X, batch_size=batch_size)
		return yhat[0,0]




	# transform data to be stationary
	raw_values = ts.values
	diff_values = difference(raw_values, 1)
	 
	# transform data to be supervised learning
	supervised = timeseries_to_supervised(diff_values, 1)
	supervised_values = supervised.values
	 
	# split data into train and test-sets
	train, test = supervised_values[1:train_size], supervised_values[train_size:]
	 
	# transform the scale of the data
	scaler, train_scaled, test_scaled = scale(train, test)
	 
	# fit the model
	lstm_model = fit_lstm(train_scaled, 1,200, 4)
	# forecast the entire training dataset to build up state for forecasting
	train_reshaped = train_scaled[:, 0].reshape(len(train_scaled), 1, 1)
	lstm_model.predict(train_reshaped, batch_size=1)
	 
	# walk-forward validation on the test data
	predictions = list()
	for i in range(len(test_scaled)):
		# make one-step forecast
		X, y = test_scaled[i, 0:-1], test_scaled[i, -1]
		yhat = forecast_lstm(lstm_model, 1, X)
		# invert scaling
		yhat = invert_scale(scaler, X, yhat)
		# invert differencing
		yhat = inverse_difference(raw_values, yhat, len(test_scaled)+1-i)
		# store forecast
		predictions.append(yhat)
		expected = raw_values[len(train) + i + 1]
	 
	# report performance
	rmse = sqrt(mean_squared_error(raw_values[train_size+1:], predictions))
	# line plot of observed vs predicted
	pyplot.plot(raw_values[train_size:])
	pyplot.plot(predictions)
	pyplot.show()


	predictions = list()
	next_hour = 0
	for i in range(6):
	    X = test_scaled[10,-1:] #(my last observation)
	    yhat = forecast_lstm(lstm_model, 1, X)
	    yhat = invert_scale(scaler, X, yhat)
	    yhat = inverse_difference(raw_values, yhat, 1)
	    predictions.append(yhat)
	    next_hour = yhat	    
	return next_hour

city='Delhi'
location='Anand%20Vihar'
url = 'https://api.openaq.org/v1/measurements?city='+city+'&location='+location+'&parameter=pm10'
result = requests.get(url).content
result = json.loads(result)
print predict(result)





