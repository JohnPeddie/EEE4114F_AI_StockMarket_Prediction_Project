    #Initially fetch all requirements:
#requirements:
from ApiKeyFetcher import getKey #homebrew solution to import the api key so it doesnt get shared on github
from pandas_datareader import data
import matplotlib.pyplot as plt
import pandas as pd
import datetime as dt
import urllib.request, json
import os
import numpy as np
import tensorflow as tf #TensorFlow 1.6
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime


#==========================================================================

#Functions:

def fetchData(dataSource, stockTicker):
    """Fetches the data for a specific ticker from either kaggle or alpha Vantage

    Params:
    dataSource: alphavantage or whatever for Kaggle
    stockTicker: the ticker for the stock eg: ABC

    Returns: dataframe of the data requested"""

    if dataSource == 'alphavantage':
        api_key = getKey("Alpha_Vantage_Api")
        ticker = stockTicker
        #form string for api request:
        urlString = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=%s&outputsize=full&apikey=%s"%(ticker,api_key)
        #choose a file to save fetched data to
        savedFile = 'stock_market_data-%s.csv'%ticker

        #check if file already exists:
        if not os.path.exists(savedFile):
            #build a pandas dataframe of the dataset
            with urllib.request.urlopen(urlString) as url:
                data = json.loads(url.read().decode())
                # extract stock market data
                data = data['Time Series (Daily)']
                df = pd.DataFrame(columns=['Date','Low','High','Close','Open'])
                for k,v in data.items():
                    date = dt.datetime.strptime(k, '%Y-%m-%d')
                    data_row = [date.date(),float(v['3. low']),float(v['2. high']),
                                float(v['4. close']),float(v['1. open'])]
                    df.loc[-1,:] = data_row
                    df.index = df.index + 1
            print('Data saved to : %s'%savedFile)
            df.to_csv(savedFile)
        #if file already exists than just load the already downloaded CSV
        else:
            print('File already exists. Loading data from CSV')
            df = pd.read_csv(savedFile)
    #if dataSource not alphavantage then use kaggle instad
    else:
        df = pd.read_csv(os.path.join('Stocks','%s.us.txt'%stockTicker),delimiter=',',usecols=['Date','Open','High','Low','Close'])
        print('Loaded data from the Kaggle repository')
    return(df) #return the final DataFrame

#dataframe plotting function:
def plotDataFrame(df):
    """Plots a curve from the provided dataframe using the mid price

    Params:
    df: a generated dataframa generated by fetchData

    Returns: n/a it just plots"""
    df.head()
    plt.figure(figsize = (18,9))
    plt.plot(range(df.shape[0]),(df['Low']+df['High'])/2.0)
    plt.xticks(range(0,df.shape[0],500),df['Date'].loc[::500],rotation=45)
    plt.xlabel('Date',fontsize=18)
    plt.ylabel('Mid Price of Stock (USD)',fontsize=18)
    plt.show()

#fetch the midpoces from the high low prices for data that doesnt contain mid_prices
def getMidPrices(df):
    """Gets the mid prices for a df based on the high and low _prices

    params:
    df: a dataframe containing high and low prices

    returns:
    midPrices: a matrix of the mid prices"""

    highPrices = df.loc[:,'High'].as_matrix()
    lowPrices = df.loc[:,'Low'].as_matrix()
    midPrices = (highPrices+lowPrices)/2.0
    return midPrices
#===============================================================================
#Classes:
#===============================================================================
#This class contains its own functions and is the work of Thushan Ganegedara and jaungiers
#-> https://github.com/jaungiers/LSTM-Neural-Network-for-Time-Series-Prediction


class DataGeneratorSeq(object):

    def __init__(self,prices,batch_size,num_unroll):
        self._prices = prices
        self._prices_length = len(self._prices) - num_unroll
        self._batch_size = batch_size
        self._num_unroll = num_unroll
        self._segments = self._prices_length //self._batch_size
        self._cursor = [offset * self._segments for offset in range(self._batch_size)]

    def next_batch(self):

        batch_data = np.zeros((self._batch_size),dtype=np.float32)
        batch_labels = np.zeros((self._batch_size),dtype=np.float32)

        for b in range(self._batch_size):
            if self._cursor[b]+1>=self._prices_length:
                #self._cursor[b] = b * self._segments
                self._cursor[b] = np.random.randint(0,(b+1)*self._segments)

            batch_data[b] = self._prices[self._cursor[b]]
            batch_labels[b]= self._prices[self._cursor[b]+np.random.randint(1,5)]

            self._cursor[b] = (self._cursor[b]+1)%self._prices_length

        return batch_data,batch_labels

    def unroll_batches(self):

        unroll_data,unroll_labels = [],[]
        init_data, init_label = None,None
        for ui in range(self._num_unroll):

            data, labels = self.next_batch()

            unroll_data.append(data)
            unroll_labels.append(labels)

        return unroll_data, unroll_labels

    def reset_indices(self):
        for b in range(self._batch_size):
            self._cursor[b] = np.random.randint(0,min((b+1)*self._segments,self._prices_length-1))

#===============================================================================
#MAIN BODY: This is spit into sections with comments to gain a better understanding of the process
#===============================================================================

#Fetch data and format it for the rest of the program
df = fetchData('kaggle', 'ge') #fetch the necessary data
df = df.sort_values('Date') #sorts the dataframe by date

#plot the dataframe do see a visualization:
plotDataFrame(df)

#Prepare the data for training:
midPrices = getMidPrices(df)

#demonstrate unsmoothed
plt.figure(figsize = (18,9))
plt.plot(range(df.shape[0]),midPrices,color='b',label='True')
plt.xlabel('Date')
plt.ylabel('Unsmoothed Mid Price')
plt.show()


print("length of mid prices: " +str(len(midPrices)))
trainData = midPrices[:11000] #use the first 11000 datapoints to train
testData = midPrices[11000:] #use the remainder to test

#scale datases to a value between 0 and 1
scaler = MinMaxScaler()
trainData = trainData.reshape(-1,1)
testData = testData.reshape(-1,1)

#train the scaling system with the traininf data and attempt to smooth the datases
smoothingWindowSize = 2500
for di in range(0,10000,smoothingWindowSize):
    scaler.fit(trainData[di:di+smoothingWindowSize,:])
    trainData[di:di+smoothingWindowSize,:] = scaler.transform(trainData[di:di+smoothingWindowSize,:])

# normalize remaining data
scaler.fit(trainData[di+smoothingWindowSize:,:])
trainData[di+smoothingWindowSize:,:] = scaler.transform(trainData[di+smoothingWindowSize:,:])

#reshape the training data
trainData = trainData.reshape(-1)

#normalize test data WRT the original scalar
testData = scaler.transform(testData).reshape(-1)

#data can now be smoothed using exponential moving average:
EMA = 0.0#initial exponential moving average
gamma = 0.1
for ti in range(11000):
    EMA = gamma*trainData[ti] + (1-gamma)*EMA
    trainData[ti] = EMA

#for visualization and testing the mid data is all concatinated together
allMidpointData = np.concatenate([trainData,testData],axis=0)

plt.figure(figsize = (18,9))
plt.plot(range(df.shape[0]),allMidpointData,color='b',label='True')
plt.xlabel('Date')
plt.ylabel('Smoothed Mid Price')
plt.show()

#the data is now prepared and attempts at prediction can now be made
#===============================================================================
#First attempt using standard averaging
#===============================================================================
windowSize = 100
N = trainData.size
stdAvgPredictions = []
stdAvgX = []
mseErrors = []

for predIdx in range(windowSize,N):

    if predIdx >= N:
        date = dt.datetime.strptime(k, '%Y-%m-%d').date() + dt.timedelta(days=1)
    else:
        date = df.loc[predIdx,'Date']

    stdAvgPredictions.append(np.mean(trainData[predIdx-windowSize:predIdx]))
    mseErrors.append((stdAvgPredictions[-1]-trainData[predIdx])**2)
    stdAvgX.append(date)

print('MSE error for standard averaging: %.5f'%(0.5*np.mean(mseErrors)))


plt.figure(figsize = (18,9))
plt.plot(range(df.shape[0]),allMidpointData,color='b',label='True')
plt.plot(range(windowSize,N),stdAvgPredictions,color='orange',label='Prediction')
plt.xlabel('Date')
plt.ylabel('Mid Price')
plt.legend(fontsize=18)
plt.show()

#===============================================================================
#second attempt using EMA avaeraging (exponential moving average)
#===============================================================================
windowSizeEMA = 100
NEMA = trainData.size

runAvgPredictions = []
runAvg_x = []

mseErrors = []

runningMean = 0.0
runAvgPredictions.append(runningMean)

decay = 0.5

for predIdx in range(1,NEMA):

    runningMean = runningMean*decay + (1.0-decay)*trainData[predIdx-1]
    runAvgPredictions.append(runningMean)
    mseErrors.append((runAvgPredictions[-1]-trainData[predIdx])**2)
    runAvg_x.append(date)

print('MSE error for EMA averaging: %.5f'%(0.5*np.mean(mseErrors)))

plt.figure(figsize = (18,9))
plt.plot(range(df.shape[0]),allMidpointData,color='b',label='True')
plt.plot(range(0,N),runAvgPredictions,color='orange', label='Prediction')
#plt.xticks(range(0,df.shape[0],50),df['Date'].loc[::50],rotation=45)
plt.xlabel('Date')
plt.ylabel('Mid Price')
plt.legend(fontsize=18)
plt.show()


#==============================================================================
#Actual ML using TensorFlow
#==============================================================================

#preperation variables (Can Be changed)
dataGen = DataGeneratorSeq(trainData,5,5)
unrolledData, unrolledLabels = dataGen.unroll_batches()

for ui,(dat,lbl) in enumerate(zip(unrolledData,unrolledLabels)):
    print('\n\nUnrolled index %d'%ui)
    datInd = dat
    lblInd = lbl
    print('\tInputs: ',dat )
    print('\n\tOutput:',lbl)

D = 1 #Dimensionality of the data, 1d dataset means D=1
futurePredictions = 100 #number of samples to look into the futurePredictions
batchSize = 500 #number of samples in a batchSize
numHiddenNodes = [200,200,200] #number of hidden nodes in each lyer of the LSTM
numLayers = len(numHiddenNodes)# number of total layers
dropout = 0.2 #dropout ammount
tf.reset_default_graph()#solves issues of running mulstiple times

#input Data:
trainInputs, trainOutputs = [],[]

#Prediction for each time step
for ui in range(futurePredictions):
    trainInputs.append(tf.placeholder(tf.float32, shape=[batchSize,D],name='trainInputs_%d'%ui))
    trainOutputs.append(tf.placeholder(tf.float32, shape=[batchSize,1], name = 'trainOutputs_%d'%ui))

#create LSTM Cells
lstmCells = [
    tf.contrib.rnn.LSTMCell(num_units=numHiddenNodes[li],state_is_tuple=True,initializer= tf.contrib.layers.xavier_initializer())
for li in range(numLayers)]

#dropout
dropLstmCells = [tf.contrib.rnn.DropoutWrapper(
    lstm, input_keep_prob=1.0,output_keep_prob=1.0-dropout, state_keep_prob=1.0-dropout
) for lstm in lstmCells]
dropMultiCell = tf.contrib.rnn.MultiRNNCell(dropLstmCells)
multiCell = tf.contrib.rnn.MultiRNNCell(lstmCells)

w = tf.get_variable('w',shape=[numHiddenNodes[-1], 1], initializer=tf.contrib.layers.xavier_initializer())
b = tf.get_variable('b',initializer=tf.random_uniform([1],-0.1,0.1))


#creation of cell states and hidden layer state variables
c, h = [],[]
initialState = []

for li in range(numLayers):
    c.append(tf.Variable(tf.zeros([batchSize, numHiddenNodes[li]]), trainable=False))
    h.append(tf.Variable(tf.zeros([batchSize, numHiddenNodes[li]]), trainable=False))
    initialState.append(tf.contrib.rnn.LSTMStateTuple(c[li], h[li]))

#dynamic_rnn function requires output to be in a specific format, therefore transformations are required: https://www.tensorflow.org/api_docs/python/tf/nn/dynamic_rnn
allInputs = tf.concat([tf.expand_dims(t,0) for t in trainInputs],axis=0)

# allOutputs is [seq_length, batch_size, num_nodes]
allLstmOutputs, state = tf.nn.dynamic_rnn(
    dropMultiCell, allInputs, initial_state=tuple(initialState),
    time_major = True, dtype=tf.float32)

allLstmOutputs = tf.reshape(allLstmOutputs, [batchSize*futurePredictions,numHiddenNodes[-1]])

allOutputs = tf.nn.xw_plus_b(allLstmOutputs,w,b)

splitOutputs = tf.split(allOutputs,futurePredictions,axis=0)

#===============================================================================
#Begin training, Optimization and predictions
#===============================================================================

#training losses
print("Defining the training loss")
loss = 0.0
with tf.control_dependencies([tf.assign(c[li], state[li][0]) for li in range(numLayers)]+
                             [tf.assign(h[li], state[li][1]) for li in range(numLayers)]):
    for ui in range(futurePredictions):
        loss += tf.reduce_mean(0.5*(splitOutputs[ui]-trainOutputs[ui])**2)

#learning decay
print("Currently performing learning rate operations")
globalStep = tf.Variable(0, trainable=False)
incGStep = tf.assign(globalStep,globalStep + 1)
tfLearningRate = tf.placeholder(shape=None,dtype=tf.float32)
tfMinLearningRate = tf.placeholder(shape=None,dtype=tf.float32)

learningRate = tf.maximum(
    tf.train.exponential_decay(tfLearningRate, globalStep, decay_steps=1, decay_rate=0.5, staircase=True),
    tfMinLearningRate)

# Optimizer.
print('Currently Performing TF Optimization Operations')
optimizer = tf.train.AdamOptimizer(learningRate)
gradients, v = zip(*optimizer.compute_gradients(loss))
gradients, _ = tf.clip_by_global_norm(gradients, 5.0)
optimizer = optimizer.apply_gradients(
    zip(gradients, v))

print('Currently defining prediction related TF functions')

sampleInputs = tf.placeholder(tf.float32, shape=[1,D])

# Maintaining LSTM state for prediction stage
sampleC, sampleH, initialSampleState = [],[],[]
for li in range(numLayers):
    sampleC.append(tf.Variable(tf.zeros([1, numHiddenNodes[li]]), trainable=False))
    sampleH.append(tf.Variable(tf.zeros([1, numHiddenNodes[li]]), trainable=False))
    initialSampleState.append(tf.contrib.rnn.LSTMStateTuple(sampleC[li],sampleH[li]))

resetSampleStates = tf.group(*[tf.assign(sampleC[li],tf.zeros([1, numHiddenNodes[li]])) for li in range(numLayers)],
                               *[tf.assign(sampleH[li],tf.zeros([1, numHiddenNodes[li]])) for li in range(numLayers)])

sampleOutputs, sampleState = tf.nn.dynamic_rnn(multiCell, tf.expand_dims(sampleInputs,0),
                                                 initial_state=tuple(initialSampleState),
                                                 time_major = True,
                                                 dtype=tf.float32)

with tf.control_dependencies([tf.assign(sampleC[li],sampleState[li][0]) for li in range(numLayers)]+
                             [tf.assign(sampleH[li],sampleState[li][1]) for li in range(numLayers)]):
    samplePrediction = tf.nn.xw_plus_b(tf.reshape(sampleOutputs,[1,-1]), w, b)


print('\tTraining, optimizing and prediction prerparation complete')

#===============================================================================
#Actiual ML LSTM part
#===============================================================================

#define states/operations/constants
epochs = 10 #number of runs
validSummary = 1 # test predictions interval
numPredictContinous = 100 # Number of steps to continously predict for

trainSeqLength = trainData.size # Full length of the training data

trainMseOt = [] # Accumulate Train losses
testMseOt = [] # Accumulate Test loss
predictionsOverTime = [] # Accumulate predictions

session = tf.InteractiveSession()

tf.global_variables_initializer().run()

# Used for decaying learning rate
lossNondecreaseCount = 0
lossNondecreaseThreshold = 2 # If the test error hasn't increased in this many steps, decrease learning rate

print('LSTM Training and Epochs Initialized')
averageLoss = 0

# Define data generator
dataGen = DataGeneratorSeq(trainData,batchSize,futurePredictions)

xAxisSeq = []

# points to start predictions from
testPointsSeq = np.arange(11000,12000,50).tolist()
mseArray =[]
times =[]

#===============================================================================
#LSTM based on the work of Thushan Ganegedara and jaungiers
#-> https://github.com/jaungiers/LSTM-Neural-Network-for-Time-Series-Prediction
#===============================================================================
for ep in range(epochs):
    now = datetime.now()#used for timing each epoch to work out total time remaining
    # ========================= Training =====================================
    for step in range(trainSeqLength//batchSize):

        uData, uLabels = dataGen.unroll_batches()

        feedDict = {}
        for ui,(dat,lbl) in enumerate(zip(uData,uLabels)):
            feedDict[trainInputs[ui]] = dat.reshape(-1,1)
            feedDict[trainOutputs[ui]] = lbl.reshape(-1,1)

        feedDict.update({tfLearningRate: 0.0001, tfMinLearningRate:0.000001})

        _, l = session.run([optimizer, loss], feed_dict=feedDict)

        averageLoss += l

    # ============================ Validation ==============================
    if (ep+1) % validSummary == 0:

        averageLoss = averageLoss/(validSummary*(trainSeqLength//batchSize))

        # The average loss
        if (ep+1)%validSummary==0:
            print('Average loss at step %d: %f' % (ep+1, averageLoss))

        trainMseOt.append(averageLoss)

        averageLoss = 0 # reset loss

        predictionsSeq = []

        mseTestLossSeq = []

        # ===================== Updating State and Making Predicitons ========================
        for w_i in testPointsSeq:
            mseTestLoss = 0.0
            ourPredictions = []

            if (ep+1)-validSummary==0:
                # Only calculate x_axis values in the first validation epoch
                xAxis=[]

            # Feed in the recent past behavior of stock prices
            # to make predictions from that point onwards
            for tr_i in range(w_i-futurePredictions+1,w_i-1):
                currentPrice = allMidpointData[tr_i]
                feedDict[sampleInputs] = np.array(currentPrice).reshape(1,1)
                _ = session.run(samplePrediction,feed_dict=feedDict)

            feedDict = {}

            currentPrice = allMidpointData[w_i-1]

            feedDict[sampleInputs] = np.array(currentPrice).reshape(1,1)

            # Make predictions for this many steps
            # Each prediction uses previous prediciton as it's current input
            for pred_i in range(numPredictContinous):

                pred = session.run(samplePrediction,feed_dict=feedDict)

                ourPredictions.append(np.asscalar(pred))

                feedDict[sampleInputs] = np.asarray(pred).reshape(-1,1)

                if (ep+1)-validSummary==0:
                    # Only calculate x_axis values in the first validation epoch
                    xAxis.append(w_i+pred_i)

                mseTestLoss += 0.5*(pred-allMidpointData[w_i+pred_i])**2

            session.run(resetSampleStates)

            predictionsSeq.append(np.array(ourPredictions))

            mseTestLoss /= numPredictContinous
            mseTestLossSeq.append(mseTestLoss)

            if (ep+1)-validSummary==0:
                xAxisSeq.append(xAxis)

        currentTestMse = np.mean(mseTestLossSeq)

        # Learning rate decay logic
        if len(testMseOt)>0 and currentTestMse > min(testMseOt):
            lossNondecreaseCount += 1
        else:
            lossNondecreaseCount = 0

        if lossNondecreaseCount > lossNondecreaseThreshold :
            session.run(incGStep)
            lossNondecreaseCount = 0
            print('\tDecreasing learning rate by 0.5')

        testMseOt.append(currentTestMse)
        print('\tTest MSE: %.5f'%np.mean(mseTestLossSeq))
        mseArray.append(mseTestLossSeq)
        predictionsOverTime.append(predictionsSeq)
        elapsedTime = (datetime.now()-now)
        times.append(elapsedTime)
        timeRemaining = np.mean(times)*(epochs-(ep+1))
        print('\tFinished Predictions, elapsed time: '+ str(elapsedTime) + ' And time remaining: ' + str(timeRemaining))

#===============================================================================
#plotting data and showing Evolution
#===============================================================================

bestIndex = mseArray.index(min(mseArray))
bestPredictionEpoch = 9# replace with best epoch
print("best epoch: "+str(bestPredictionEpoch))
plt.figure(figsize = (18,18))
plt.subplot(2,1,1)
plt.plot(range(df.shape[0]),allMidpointData,color='b')

# Plotting how the predictions change over time
# Plot older predictions with low alpha and newer predictions with high alpha
startAlpha = 0.25
alpha  = np.arange(startAlpha,1.1,(1.0-startAlpha)/len(predictionsOverTime[::3]))
for p_i,p in enumerate(predictionsOverTime[::3]):
    for xval,yval in zip(xAxisSeq,p):
        plt.plot(xval,yval,color='r',alpha=alpha[p_i])

plt.title('Evolution of Test Predictions Over Time',fontsize=18)
plt.xlabel('Date',fontsize=18)
plt.ylabel('Mid Price',fontsize=18)
plt.xlim(11000,12500)

plt.subplot(2,1,2)

# Predicting the best test prediction you got
plt.plot(range(df.shape[0]),allMidpointData,color='b')
for xval,yval in zip(xAxisSeq,predictionsOverTime[bestPredictionEpoch]):
    plt.plot(xval,yval,color='r')

plt.title('Best Test Predictions Over Time',fontsize=18)
plt.xlabel('Date',fontsize=18)
plt.ylabel('Mid Price',fontsize=18)
plt.xlim(11000,12500)
plt.show()
