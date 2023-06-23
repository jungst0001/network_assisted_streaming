import pandas as pd
from pandas.plotting import scatter_matrix
import numpy as np
import matplotlib.pyplot as plt
import asyncio
import seaborn as sns

# plt.rcParams['figure.figsize'] = [12, 8] # setting figure size

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLSResults

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

import rlserverConfig

MAX_BITRATE = rlserverConfig.MAX_BITRATE

def _scaleVarMinMax(variables:dict):
	x = dict()

	if variables['bitrate'] > 0 and variables['bitrate'] < 1:
		# already scaled
		x['bitrate'] = variables['bitrate']
	else:
		x['bitrate'] = variables['bitrate'] / MAX_BITRATE
	# x['bufferLevel'] = variables['bufferLevel'] / variables['MAX_BUFFER_LEVEL']

	return x['bitrate']

def predictLinearModel(result, variables):
	X = _scaleVarMinMax(variables)
	
	const = 1
	X = np.column_stack((const, X, np.power(X, 2), np.power(X, 3)))

	params = np.array(result.params)

	pred_y = np.dot(X, params)

	return pred_y

def loadLinearModel():
	result = OLSResults.load(rlserverConfig.linear_model_dir + rlserverConfig.linear_model_name)

	return result

def saveLinearModel(result):
	result.save(rlserverConfig.linear_model_dir + rlserverConfig.linear_model_name)

def getTrendLine(df):
	df.plot(kind='scatter', x='bitrate', y='GMSD')

def getCorrScatterPlot(df):
	plt.matshow(df.corr())
	plt.show()

def getVariables(clientStates):
	variables = dict()
	variables['GMSD'] = []
	variables['bitrate'] = []
	variables['startupDelay'] = []
	variables['bitrateSwitch'] = []
	variables['bufferLevel'] = []
	variables['MAX_BUFFER_LEVEL'] = []
	variables['throughput']  = []
	variables['stalling'] = []

	for clientState in clientStates:
		for oneState in clientState:
			for i in range(len(oneState.GMSD)):
				if oneState.GMSD[i] != 0.7 and oneState.throughput[i] != 0:
					variables['GMSD'].append(oneState.GMSD[i])
					variables['bitrate'].append(oneState.bitrate[i])
					variables['startupDelay'].append(oneState.startupDelay)
					variables['bitrateSwitch'].append(oneState.bitrateSwitch[i])
					variables['bufferLevel'].append(oneState.bufferLevel[i])
					variables['MAX_BUFFER_LEVEL'].append(oneState.MAX_BUFFER_LEVEL)
					variables['throughput'].append(oneState.throughput[i])
					variables['stalling'].append(oneState.stalling[i])

	return variables

def divdeTrainTestData(clientStates, states_bf_ratio, divide_ratio=(9, 1)):
	states_bf_ratio = np.asarray(states_bf_ratio)
	divide_ratio = np.asarray(divide_ratio)
	
	train_num = (states_bf_ratio*divide_ratio[0])//sum(divide_ratio) +\
				 (states_bf_ratio*divide_ratio[0])%sum(divide_ratio)

	test_num = (states_bf_ratio*divide_ratio[1])//sum(divide_ratio)

	train_states = []
	test_states = []

	for state in clientStates:
		if state.MAX_BUFFER_LEVEL == 15:
			if states_bf_ratio[0] > 0:
				train_states.append(state)
				states_bf_ratio[0] -= 1
			else:
				test_states.append(state)
		elif state.MAX_BUFFER_LEVEL == 30:
			if states_bf_ratio[1] > 0:
				train_states.append(state)
				states_bf_ratio[1] -= 1
			else:
				test_states.append(state)
		elif state.MAX_BUFFER_LEVEL == 45:
			if states_bf_ratio[2] > 0:
				train_states.append(state)
				states_bf_ratio[2] -= 1
			else:
				test_states.append(state)
		elif state.MAX_BUFFER_LEVEL == 60:
			if states_bf_ratio[3] > 0:
				train_states.append(state)
				states_bf_ratio[3] -= 1
			else:
				test_states.append(state)

	print(f'len all state: {len(states)}')
	print(f'len train state: {len(train_states)}')
	print(f'len train state: {len(test_states)}')

	return train_states, test_states

def preprocessData(df):
	tmp_df_400 = df.loc[(df['bitrate'] == 400) & (df['GMSD'] < 0.91)]
	tmp_df_800 = df.loc[(df['bitrate'] == 800) & (df['GMSD'] < 0.97) & (df['GMSD'] > 0.89)]
	tmp_df_1401 = df.loc[(df['bitrate'] == 1401) & (df['GMSD'] < 0.96) & (df['GMSD'] > 0.89)]
	tmp_df_2000 = df.loc[(df['bitrate'] == 2000) & (df['GMSD'] > 0.92)]

	prep_df = pd.concat([tmp_df_400, tmp_df_800, tmp_df_1401, tmp_df_2000])

	return prep_df

def calculateVIF(df):
	from statsmodels.stats.outliers_influence import variance_inflation_factor

	# calculte VIF value.
	# if VIF value is bigger than 10, the values have multicollinearity.
	vif = pd.DataFrame()
	df = df[['bitrate', 'startupDelay', 'bitrateSwitch', 
		'bufferLevel', 'MAX_BUFFER_LEVEL', 'throughput', 'stalling']]
	vif['VIF Factor'] = [variance_inflation_factor(
		df.values, i) for i in range(df.shape[1])]
	vif['features'] = df.columns

	print(vif)

def min_max_scaler(df):
	df_bit = df['bitrate']
	df_bit = np.array(df_bit)

	df_bit = (df_bit - 0) / (max(df_bit) - 0)

	df['bitrate'] = df_bit

	df_throughput = df['throughput']
	df_throughput = np.array(df_throughput)

	df_throughput = (df_throughput - min(df_throughput)) / (max(df_throughput) - min(df_throughput))
	df['throughput'] = df_throughput

	df_buffer = df['bufferLevel']
	df_buffer = np.array(df_buffer)

	df_buffer = (df_buffer - 0) / (np.array(df['MAX_BUFFER_LEVEL']) - 0)
	df_buffer = np.where(df_buffer > 1, 1, df_buffer)
	df['bufferLevel'] = df_buffer

	return df

def printStatistics(df):
	print(df.loc[df['bitrate'] == 400].describe())
	print(df.loc[df['bitrate'] == 800].describe())
	print(df.loc[df['bitrate'] == 1401].describe())
	print(df.loc[df['bitrate'] == 2000].describe())

def logisticRegression(videoState):
	states = videoState.states_raw
	clientStates = [state[1] for state in states]

	clientVariables = getVariables(clientStates)
	df = pd.DataFrame(clientVariables)

	prep_df = preprocessData(df)
	prep_df = sm.add_constant(prep_df, has_constant = 'add')
	print(prep_df.head())

	feature_columns = prep_df.columns.difference(['GMSD'])
	X = prep_df[feature_columns]
	y = prep_df['GMSD']

	train_x, test_x ,train_y, test_y = train_test_split(X, y, 
		train_size=0.7,test_size=0.3,random_state=1)
	print(train_x.shape, test_x.shape, train_y.shape, test_y.shape)

	full_model = sm.Logit(train_y, train_x)
	full_model_results = full_model.fit(method = "newton")

	print(full_model_results.summary())

	x_cols = ['bitrate']
	X = prep_df[x_cols] 
	y = prep_df['GMSD']

	X = sm.add_constant(X)
	train_x, test_x ,train_y, test_y = train_test_split(X, y, 
		train_size=0.7,test_size=0.3,random_state=1)
	print(train_x.shape, test_x.shape, train_y.shape, test_y.shape)

	reduced_model = sm.Logit(train_y, train_x)
	reduced_model_results = reduced_model.fit(method = "newton")

	print(reduced_model_results.summary())

def linearRegrssion(videoState):
	states = videoState.states_raw
	clientStates = [state[1] for state in states]

	clientVariables = getVariables(clientStates)
	df = pd.DataFrame(clientVariables)

	# print(df)
	# print(df.describe())
	# print((df['bitrate'] == 400).value_counts())
	# print((df['bitrate'] == 800).value_counts())
	# print((df['bitrate'] == 1401).value_counts())
	# print((df['bitrate'] == 2000).value_counts())
	prep_df = preprocessData(df)

	# printStatistics(prep_df)

	# print(df.corr())
	prep_df = min_max_scaler(prep_df)

	# print(minmax_df)
	print(prep_df)
	print(prep_df.corr())

	# show scatter matrix
	# scatter_matrix(prep_df, alpha=1, diagonal=None)
	# plt.show()

	# print(minmax_df.corr())
	# getCorrScatterPlot(minmax_df)

	# the result is bufferlevel and MAX_BUFFER_LEVEL are bigger than 10.
	# so, remove MAX_BUFFER_LEVEL when using OLS.
	calculateVIF(prep_df)

	y_col = ['GMSD']
	# # bitrate switch is categorical variables, and
	# # this is already dummy coded
	# x_cols = ['bitrate', 'bufferLevel', 'startupDelay', 
	# 'throughput', 'bitrateSwitch', 'stalling']

	# X = prep_df[x_cols] 
	# y = prep_df[y_col]

	# X = sm.add_constant(X)

	# train_x, test_x ,train_y, test_y = train_test_split(X, y, 
	# 	train_size=0.7,test_size=0.3,random_state=1)
	# print(train_x.shape, test_x.shape, train_y.shape, test_y.shape)

	# full_model = sm.OLS(train_y, train_x)
	# full_model_result = full_model.fit()

	# # the result that bitrateswitch and throughput have P>|t| is bigger than 0.05.
	# # so, remove upper values
	# print(full_model_result.summary())

	x_cols = ['bitrate', 'bufferLevel', 'throughput']

	X = prep_df[x_cols] 
	y = prep_df[y_col]

	# X = sm.add_constant(X)

	train_x, test_x ,train_y, test_y = train_test_split(X, y, 
		train_size=0.7,test_size=0.3,random_state=1)
	print(train_x.shape, test_x.shape, train_y.shape, test_y.shape)

	# train_y = np.log(np.divide(1.0, train_y) - 1)

	train_data = pd.concat([train_x, train_y], axis=1)
	
	print(train_data)

	# fitted_two_var_model = sm.OLS(train_y, train_x)

	train_data = sm.add_constant(train_data)
	fitted_two_var_model = sm.OLS.from_formula('GMSD ~ bitrate + np.power(bitrate, 2) + np.power(bitrate, 3)', 
		 data=train_data)
	fitted_two_var_result = fitted_two_var_model.fit()

	print(fitted_two_var_result.summary())

	params = np.array(fitted_two_var_result.params)

	print(params)

	test_x_bit = test_x['bitrate']

	newtest_x = np.column_stack((test_x_bit, np.power(test_x_bit, 2), np.power(test_x_bit, 3)))
	newtest_x = sm.add_constant(newtest_x)
	# print(test_x.shape, newtest_x.shape)
	# print(newtest_x)

	# pred_y = fitted_two_var_model.predict(newtest_x)
	pred_y = np.dot(newtest_x, params)
	print(pred_y)
	pred_y = np.array([pred_y]).T
	testModelPerformance(test_y, pred_y)
	showResidualPlot(test_y, pred_y)

	return prep_df, fitted_two_var_result

def testModelPerformance(test, pred):
	from sklearn import metrics

	mae = metrics.mean_absolute_error(test, pred)
	mse = metrics.mean_squared_error(test, pred)
	rmse = np.sqrt(metrics.mean_squared_error(test, pred))

	print(f'MAE: {mae}')
	print(f'MSE: {mse}')
	print(f'RMSE: {rmse}')

def showResidualPlot(test, pred):
	residual = test.sub(pred)

	sns.regplot(test.sample(n=300), residual.sample(n=300), lowess=True, line_kws={'color': 'red'})

	plt.plot([pred.min(), pred.max()], [0, 0], '--', color='grey')
	plt.show()

def makeLinearModel():
	from VideoState import VideoState

	videoState = VideoState(MAX_CLIENT_NUM=25, use_gmsd_estimation=False,
		subDir=rlserverConfig.subDir_in_estimated_gmsd)
	df, result = linearRegrssion(videoState)

	saveLinearModel(result)

	# x_cols = ['bitrate', 'bufferLevel']

	# X = df[x_cols] 

	# fitted = result.predict(X)

	# print(fitted)
	# showResidual(df, result)


	# load_result = loadLinearModel()
	# print(load_result.summary())

	# variables = {'bitrate': 400, 'bufferLevel': 20.324, 'MAX_BUFFER_LEVEL': 30}

	# pred = predictLinearModel(load_result, variables)

	# print(pred)

# Deprecated
def makeLogisticModel():
	from VideoState import VideoState
	videoState = VideoState(MAX_CLIENT_NUM=rlserverConfig.client_num_in_estimated_gmsd, 
		subDir=rlserverConfig.subDir_in_estimated_gmsd)
	logisticRegression(videoState)

def testLinearModel():
	load_result = loadLinearModel()
	print(load_result.summary())

	variables = {'bitrate': 400, 'bufferLevel': 20.324, 'MAX_BUFFER_LEVEL': 30}

	pred = predictLinearModel(load_result, variables)

	print(pred[0])

if __name__ == '__main__':
	# makeLinearModel()
	# makeLogisticModel()
	testLinearModel()
	