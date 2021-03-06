# -*- coding: utf-8 -*-
"""Kmean.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1aJoak9PAHOdj-9jYzFHVahrOdCOBPtT5

### Setup

Let's setup Spark on your Colab environment.  Run the cell below!
"""

!pip install pyspark
!pip install -U -q PyDrive
!apt install openjdk-8-jdk-headless -qq
import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"

"""Now we import some of the libraries usually needed by our workload.




"""

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# %matplotlib inline

import pyspark
from pyspark.sql import *
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark import SparkContext, SparkConf

"""Let's initialize the Spark context."""

# create the session
conf = SparkConf().set("spark.ui.port", "4050")

# create the context
sc = pyspark.SparkContext(conf=conf)
spark = SparkSession.builder.getOrCreate()

"""You can easily check the current version and get the link of the web interface. In the Spark UI, you can monitor the progress of your job and debug the performance bottlenecks (if your Colab is running with a **local runtime**)."""

spark

"""### Data Preprocessing

In this Colab, rather than downloading a file from Google Drive, we will load a famous machine learning dataset, the [Breast Cancer Wisconsin dataset](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html), using the ```scikit-learn``` datasets loader.
"""

from sklearn.datasets import load_breast_cancer
breast_cancer = load_breast_cancer()

"""For convenience, given that the dataset is small, we first construct a Pandas dataframe, tune the schema, and then convert it into a Spark dataframe."""

pd_df = pd.DataFrame(breast_cancer.data, columns=breast_cancer.feature_names)
df = spark.createDataFrame(pd_df)

def set_df_columns_nullable(spark, df, column_list, nullable=False):
    for struct_field in df.schema:
        if struct_field.name in column_list:
            struct_field.nullable = nullable
    df_mod = spark.createDataFrame(df.rdd, df.schema)
    return df_mod

df = set_df_columns_nullable(spark, df, df.columns)
df = df.withColumn('features', array(df.columns))
vectors = df.rdd.map(lambda row: Vectors.dense(row.features))

df.printSchema()

print(len(df.columns))

"""With the next cell, we build the two datastructures that we will be using throughout this Colab:


*   ```features```, a dataframe of Dense vectors, containing all the original features in the dataset;
*   ```labels```, a series of binary labels indicating if the corresponding set of features belongs to a subject with breast cancer, or not.


"""

from pyspark.ml.linalg import Vectors
features = spark.createDataFrame(vectors.map(Row), ["features"])
labels = pd.Series(breast_cancer.target)

features.head(2)

type(features)

labels.max()

labels.value_counts()

"""#**Question01:**

If you run successfully the Setup and Data Preprocessing stages, you are now ready to cluster the data with the [K-means](https://spark.apache.org/docs/latest/ml-clustering.html) algorithm included in MLlib (Spark's Machine Learning library).
Set the ```k``` parameter to **2**, fit the model, and the compute the [Silhouette score](https://en.wikipedia.org/wiki/Silhouette_(clustering)) (i.e., a measure of quality of the obtained clustering).  

**IMPORTANT:** use the MLlib implementation of the Silhouette score (via ```ClusteringEvaluator```).
"""

from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

kmeans = KMeans().setK(2).setSeed(1)
model = kmeans.fit(features)

prediction = model.transform(features)

# Evaluate clustering by computing Silhouette score
evaluator = ClusteringEvaluator()

silhouette = evaluator.evaluate(prediction)
print("Silhouette with squared euclidean distance = " + str(silhouette))

"""###Silhouette score = 0.8342"""

centers = model.clusterCenters()
print("Cluster Centers: ")
for center in centers:
    print(center)

k = range(2,11)
sil_list = []
for i in k:
  kmeans = KMeans().setK(i).setSeed(1)
  models = kmeans.fit(features)
  predictions = models.transform(features)

# Evaluate clustering by computing Silhouette score
  evaluator = ClusteringEvaluator()

  silhouette = evaluator.evaluate(predictions)
  sil_list.append(silhouette)

fig, ax = plt.subplots()
ax.plot(k, sil_list)

ax.set(xlabel='Number of clusters', ylabel='Silhouette Score',
       title='Silhouette Graph')
ax.grid()
plt.show()

"""#**Question02:**

Compute the within cluster sum of squares (WSS) using your **OWN** method in Spark. Note that the score can be be obtained using the `summary.trainingCost` method of the fitted kmeans model.
"""

k = range(2, 11)
cost_list= []
for i in k:
  kmeans = KMeans().setK(i).setSeed(1)
  model_WSS = kmeans.fit(features)
  cost = model_WSS.summary.trainingCost
  int_cost = int(cost)
  cost_list.append(int_cost)

fig, ax = plt.subplots()
ax.plot(k, cost_list)

ax.set(xlabel='Number of clusters', ylabel='WSS',
       title='WSS Error Graph')
ax.grid()
plt.show()

print("WSS error =", cost_list[0])

"""###WSS error = 779.4k

#**Question03:**

**Take** the predictions produced by K-means, and compare them with the ```labels``` variable (i.e., the ground truth from our dataset).  

Compute how many data points in the dataset have been clustered correctly (i.e., positive cases in one cluster, negative cases in the other).

*HINT*: you can use ```np.count_nonzero(series_a == series_b)``` to quickly compute the element-wise comparison of two series.

**IMPORTANT**: K-means is a clustering algorithm, so it will not output a label for each data point, but just a cluster identifier!  As such, label ```0``` does not necessarily match the cluster identifier ```0```.
"""

prediction.show(5, truncate= True)

#converting to list
prediction_lst = [int(row.prediction) for row in prediction.collect()]

print(prediction_lst[0:5])

#converting to Panda series for comparison
prediction_series = pd.Series( (v for v in prediction_lst) )

type(prediction_series)

prediction_series.value_counts()

correct_predictions = np.sum(prediction_series == labels)

print("Numbers of correctly predicted values: ", correct_predictions)

"""####The number 83 indicates that the KMeans cluster number is not consistent with actual label which mean cluster number 0 represent label 1 and cluster 1 represent label 0. Therefore inverting the prediction to make it consistent with the given lables in order to draw the comparason"""

prediction_lstI = []
for k in range(0,569):
  if (prediction_lst[k] == 0):
    prediction_lstI.append(1)
  if (prediction_lst[k] == 1):
    prediction_lstI.append(0)

prediction_seriesI = pd.Series( (v for v in prediction_lstI) )

prediction_seriesI.value_counts()

"""###Now doing comparison and visualizing"""

correct_predictions = np.count_nonzero(prediction_seriesI == labels)
print("Numbers of correctly predicted values: ", correct_predictions)

"""###Hence, correctly predicted labels = 486"""

labels_list = labels.to_list()
print(type(labels_list))

from sklearn.metrics import confusion_matrix
data = confusion_matrix(labels_list, prediction_lstI)

import seaborn as sn
df_cm = pd.DataFrame(data, columns=np.unique(labels_list), index = np.unique(labels_list))
df_cm.index.name = 'Actual'
df_cm.columns.name = 'Predicted'
plt.figure(figsize = (7,5))
sn.set(font_scale=1.4)#for label size
sn.heatmap(df_cm, cmap="Blues", annot=True, fmt="d", annot_kws={"size": 12})#

"""#**Question03:**

Now perform dimensionality reduction on the ```features``` using the [PCA](https://spark.apache.org/docs/latest/ml-features.html#pca) statistical procedure, available as well in MLlib.

Set the ```k``` parameter to **2**, effectively reducing the dataset size of a **15X** factor.
"""

from pyspark.ml.feature import PCA

pca = PCA(k=2, inputCol="features", outputCol="pcafeatures")
model = pca.fit(features)

pcaFeatures = model.transform(features).select("pcafeatures")
pcaFeatures.show(5, truncate=False)

reduced_features = pcaFeatures.withColumnRenamed("pcafeatures","features")
reduced_features.show(5, truncate=False)

"""#**Question04:**

Now run K-means with the same parameters as above, but on the ```pcaFeatures``` produced by the PCA reduction you just executed.
"""

kmeans = KMeans().setK(2).setSeed(1)
new_model = kmeans.fit(reduced_features)

new_prediction = new_model.transform(reduced_features)

"""#**Question05:**

Compute the Silhouette score, as well as the number of data points that have been clustered correctly.
"""

evaluator = ClusteringEvaluator()

new_silhouette = evaluator.evaluate(new_prediction)
print("Silhouette with squared euclidean distance = " + str(new_silhouette))

"""###Silhouette score after dimensionality reduction = 0.8348"""

new_prediction.show(5, truncate=False)

#Converting to list
new_prediction_lst = [int(row.prediction) for row in new_prediction.collect()]

new_prediction_lst[0:10]

#converting to Panda series
new_prediction_series = pd.Series( (v for v in new_prediction_lst) )

new_prediction_series.value_counts()

"""###Again making the predicted cluster number consistent with the actual label output"""

new_prediction_lstI = []
for k in range(0,569):
  if (new_prediction_lst[k] == 0):
    new_prediction_lstI.append(1)
  if (new_prediction_lst[k] == 1):
    new_prediction_lstI.append(0)

new_prediction_seriesI = pd.Series( (v for v in new_prediction_lstI) )

new_prediction_seriesI.value_counts()

pca_predictions = np.count_nonzero(new_prediction_seriesI == labels)

print("Numbers of correctly predicted values: ", pca_predictions)

"""###Number of corrected predicted labels = 486.
### Visualizing
"""

import seaborn as sn
df = pd.DataFrame(list(zip(labels_list, new_prediction_lstI)), columns =['y_Actual','y_Predicted'])
confusion_matrix = pd.crosstab(df['y_Actual'], df['y_Predicted'], rownames=['Actual'], colnames=['Predicted'])

sn.heatmap(confusion_matrix, annot=True, fmt="d")
sn.set(font_scale=0.9)
plt.figure(figsize = (11,6))
plt.show()

"""#**Question06:**

Visualize the dataset by plotting a scatter plot of the two PCA components. 

You need to plot two scatter plots:

1) Highlight the two **actual** labels in the dataset

2) Highlight the two **clusters** found by K-Means in the dataset

##For actual labels in dataset
"""

reduced_features.show(5, truncate = False)

reduced_list = [list(row.features) for row in reduced_features.collect()]

nd_array = np.array(reduced_list)

labels_lst = labels.tolist()

labels_array = np.array(labels_lst)

plt.scatter(nd_array[:, 0], nd_array[:, 1], c=labels_array)
plt.title("Actual Label output")

"""##For KMean clusters (PCA)"""

new_prediction_array = np.array(new_prediction_lst)

plt.scatter(nd_array[:, 0], nd_array[:, 1], c=new_prediction_array)
plt.title("KMean Clustreing (PCA)")

df_predictionN = new_prediction.toPandas()

df_predictionN.head(5)

"""#**Question07:**

Repeat the process of Question01 for K = 1 to 10. **Plot** separately

1) the Sihouette score for each K

2) the within cluster sum of squares (WSS) for each K

##For Sihouetter score
"""

fig, ax = plt.subplots()
ax.plot(k, sil_list)

ax.set(xlabel='Number of clusters', ylabel='Silhouette Score',
       title='Silhouette Graph')
ax.grid()
plt.show()

"""##WSS for each K"""

fig, ax = plt.subplots()
ax.plot(k, cost_list)

ax.set(xlabel='Number of clusters', ylabel='WSS',
       title='WSS Error Graph')
ax.grid()
plt.show()