# -*- coding: utf-8 -*-
"""text_classifier.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1grLKlOOuOznlQveX8llHDOg_qxmBZkdb
"""

import numpy as np
import math
import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
from sklearn.utils import resample
import warnings
import seaborn as sns
import matplotlib.pyplot as plt
import string
import json
import requests
import pickle
warnings.filterwarnings("ignore")
nltk.download('punkt')
nltk.download('wordnet')
nltk.download("stopwords")
nltk.download('omw-1.4')

# Preprocessing step

def clean_review(review):
    '''
    Input:
        review: a string containing a review.
    Output:
        review_cleaned: a processed review.

    '''
    # converting to lower case
    review = review.lower()
    # removing the links that begin with http and www
    review = re.sub(r'https?://\S+', '', review)
    review = re.sub(r'[^\w\s]', '', review)
    #Removing punctuations
    review = "".join([char for char in review if char not in string.punctuation])
    #Removing stopwords
    predefined_stopword_list = nltk.corpus.stopwords.words('english')
    review = " ".join([word for word in re.split('\W+', review) if word not in predefined_stopword_list])
    #Tokenizing using the word tokenizer function
    review = word_tokenize(review)
    # Lemmatizing input
    lemmatizer = WordNetLemmatizer()
    review_cleaned =" ".join([lemmatizer.lemmatize(w) for w in review])

    return review_cleaned

#Model creation step
def model_creation():
    ## Reading the data and removing columns that are not important.
    df = pd.read_csv("movie_reviews.csv", sep = ',', encoding = 'latin-1', usecols = lambda col: col not in ["Unnamed: 2", "Unnamed: 3", "Unnamed: 4"])
    df_majority = df[df['sentiment'] == 'positive']
    df_minority = df[df['sentiment'] == 'negative']

    negative_upsample = resample(df_minority, replace = True,
                        n_samples = df_majority.shape[0],
                        random_state = 101)

    df_upsampled = pd.concat([df_majority, negative_upsample])
    # concat two data frames i,e majority class data set and upsampled minority class data set
    df_upsampled = df_upsampled.sample(frac = 1)

    ## Considering 10000 positive and 10000 negative data points
    negative_data_points_train = df_upsampled[df_upsampled['sentiment'] == 'negative'].iloc[:10000]
    positive_data_points_train = df_upsampled[df_upsampled['sentiment'] == 'positive'].iloc[:10000]

    ## Considering the remaining data points for test
    negative_data_points_test = df_upsampled[df_upsampled['sentiment'] == 'negative'].iloc[10000:]
    positive_data_points_test = df_upsampled[df_upsampled['sentiment'] == 'positive'].iloc[10000:]

    ## Concatenate the training positive and negative reviews
    X_train = pd.concat([positive_data_points_train['review'], negative_data_points_train['review']])
    ## Concatenating the training positive and negative outputs
    y_train = pd.concat([positive_data_points_train['sentiment'], negative_data_points_train['sentiment']])

    ## Concatenating the test positive and negative reviews
    X_test = pd.concat([positive_data_points_test['review'], negative_data_points_test['review']])
    ## Concatenating the test positive and negative outputs
    y_test = pd.concat([positive_data_points_test['sentiment'], negative_data_points_test['sentiment']])

    def find_occurrence(frequency, word, label):
        '''
        Params:
            frequency: a dictionary with the frequency of each pair (or tuple)
            word: the word to look up
            label: the label corresponding to the word
        Return:
            n: the number of times the word with its corresponding label appears.
        '''
        n = 0
        if (word, label) in frequency:
          n = frequency[(word, label)]

        return n


    output_map = {'positive': 0, 'negative': 1}
    y_train = y_train.map(output_map)
    y_test = y_test.map(output_map)

    def review_counter(output_occurrence, reviews, positive_or_negative):
        '''
        Params:
            output_occurrence: a dictionary that will be used to map each pair to its frequency
            reviews: a list of reviews
            positive_or_negative: a list corresponding to the sentiment of each review (either 0 or 1)
        Return:
            output: a dictionary mapping each pair to its frequency
        '''
        ## Steps :
        # define the key, which is the word and label tuple
        for label, review in zip(positive_or_negative, reviews):
          split_review = clean_review(review).split()
          for word in split_review:
            # key contains the word and label tuple
            key = (word, label)
            # If the key exists in the dictionary, increment the count
            if key in output_occurrence:
                output_occurrence[key] += 1
            # Else, add it to the dictionary and set the count to 1
            else:
                output_occurrence[key] = 1

        return output_occurrence

    freqs = review_counter({}, X_train, y_train)

    def train_naive_bayes(freqs, train_x, train_y):
        '''
        Input:
            freqs: dictionary from (word, label) to how often the word appears
            train_x: a list of reviews
            train_y: a list of labels correponding to the reviews (0,1)
        Output:
            logprior: the log prior. (equation 3 above)
            loglikelihood: the log likelihood of you Naive bayes equation. (equation 6 above)
        '''
        loglikelihood = {}
        logprior = 0


        # calculate V, the number of unique words in the vocabulary
        vocab = set([pair[0] for pair in freqs.keys()])
        V = len(vocab)

        # calculate num_pos and num_neg - the total number of positive and negative words for all documents
        num_pos = num_neg = 0
        for pair in freqs.keys():
            # if the label is positive (greater than zero)
            if pair[1] == 0:

                # Increment the number of positive words by the count for this (word, label) pair
                num_pos = num_pos + freqs[pair]

            # else, the label is negative
            else:

                  # increment the number of negative words by the count for this (word,label) pair
                  num_neg = num_neg + freqs[pair]

        # Calculate num_doc, the number of documents
        num_doc = len(train_y)

        # Calculate D_pos, the number of positive documents
        pos_num_docs = train_y.value_counts()[0]

        # Calculate D_neg, the number of negative documents
        neg_num_docs = train_y.value_counts()[1]

        # Calculate logprior
        logprior = np.log(pos_num_docs) - np.log(neg_num_docs)

        # For each word in the vocabulary...
        for word in vocab:
            # get the positive and negative frequency of the word
            freq_pos = freqs.get((word, 0), 0)
            freq_neg = freqs.get((word, 1), 0)

            # calculate the probability that each word is positive, and negative
            p_w_pos = (1 + freq_pos) / ((1*V) + num_pos)
            p_w_neg = (1 + freq_neg) / ((1*V) + num_neg)

            # calculate the log likelihood of the word
            loglikelihood[word] = np.log(p_w_pos/p_w_neg)

        return logprior, loglikelihood


    logprior, loglikelihood = train_naive_bayes(freqs, X_train, y_train)
    with open('args.pkl', 'wb') as f:
        pickle.dump((freqs, logprior, loglikelihood), f)


def naive_bayes_predict(review, logprior, loglikelihood):
    '''
    Params:
        review: a string
        logprior: a number
        loglikelihood: a dictionary of words mapping to numbers
    Return:
        total_prob: the sum of all the loglikelihoods of each word in the review (if found in the dictionary) + logprior (a number)

    '''

    # process the review to get a list of words
    word_l = clean_review(review).split()

    # initialize probability to zero
    total_prob = 0

    # add the logprior
    total_prob = total_prob + logprior

    for word in word_l:

        # check if the word exists in the loglikelihood dictionary
        if word in loglikelihood:
            # add the log likelihood of that word to the probability
            total_prob = total_prob + loglikelihood[word]


    return 1 if total_prob < 0 else 0

def load_file():
    try:
        with open('args.pkl', 'rb') as f:
            freqs, logprior, loglikelihood = pickle.load(f)
            print("Loading parameters\n")
            return freqs, logprior, loglikelihood
    except FileNotFoundError:
        print('The file does not exist. Please wait for a while, the model is being created!')
        model_creation()
        return None

if __name__ == "__main__":

    return_value = load_file()
    if return_value is not None:
        freqs, logprior, loglikelihood = return_value

    load_fail = False

    if not return_value:
        freqs, logprior, loglikelihood = load_file()

    while True:
        # Take user input
        user_input = input("Enter a sentence (or 'X' to exit): ")

        # Check if user wants to quit
        if user_input.strip().upper() == 'X':
            break

        # Perform sentiment classification
        pred = naive_bayes_predict(user_input,logprior, loglikelihood)

        # Print results
        print("Sentiment: ")

        if pred == 0:
            print("Positive review")
        else:
            print("Negative review")

        print("---------------------")

        print("Let's go again!")