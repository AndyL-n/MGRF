"""
author: L
date: 2021/8/25 14:06
"""

import numpy as np
import scipy.sparse as sp
import random
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from tqdm import tqdm
import pandas as pd
from time import time

def sparseFeature(feat, feat_num, embed_dim=8):
    """
    create dictionary for sparse feature
    :param feat: feature name
    :param feat_num: the total number of sparse features that do not repeat
    :param embed_dim: embedding dimension
    :return:
    """
    return {'feat': feat, 'feat_num': feat_num, 'embed_dim': embed_dim}

def load_data(file, embed_dim=32, path='Data_loo/'):
    """
    :param file: A string. dataset name.
    :param embed_dim: A scalar. latent factor.
    :return: user_num, item_num, train_df, test_df
    """
    print('============Load Dateset====================')
    print('loading:\t' + file)
    train_file = path + file + '/train.txt'
    val_file = path + file + '/val.txt'
    test_file = path + file + '/test.txt'
    train_dict = pd.read_table(train_file, header=None, sep=' ', names=['user','pos','neg'])
    val_dict = pd.read_table(val_file, header=None, sep=' ', names=['user','pos','neg'])
    test_dict = pd.read_table(test_file, header=None, sep=' ', names=['user', 'pos'] + ['neg' + str(i) for i in range(1,101)])
    del test_dict['neg100']
    user_num, item_num = train_dict['user'].max() + 1, max(train_dict['neg'].max(), train_dict['pos'].max()) + 1
    train_num, val_num, test_num = train_dict.shape[0], val_dict.shape[0], test_dict.shape[0]

    print('user_num: ' + str(user_num) + ',item_num：' + str(item_num) + ',interactions：' + str(train_num + val_num + test_num))
    print('train_num：' + str(train_num) + ',val_num：' + str(val_num) + ',test_num：' + str(test_num))

    print('============Create Norm Adj=================')
    adj_mat = sp.load_npz('Data/' + file + '/adj_mat.npz')
    norm_adj_mat = sp.load_npz('Data/' + file + '/adj_norm_mat.npz')
    mean_adj_mat = sp.load_npz('Data/' + file + '/adj_mean_mat.npz')
    pre_adj_mat = sp.load_npz('Data/' + file + '/adj_pre_mat.npz')
    R = sp.dok_matrix((user_num, item_num), dtype=np.float32)
    with open(train_file) as f_train:
        for line in tqdm(f_train.readlines()):
            line = [int(x) for x in line.strip('\n').split(' ')]
            R[line[0], line[1]] = 1

    R = R.tocsr()
    user_sim = sp.dok_matrix((user_num, user_num), dtype=np.float32)
    user_sim[:, :] = cosine_similarity(R)[:, :]
    R = R.T
    # # print(R.shape)
    item_sim = sp.dok_matrix((item_num, item_num), dtype=np.float32)
    item_sim[:, :] = cosine_similarity(R)[:, :]
    R = R.T
    # print(item_sim[10000].argsort()[-1])
    # print(item_sim[40979].argsort()[::-1])
    # print(item_sim[40980].argsort()[::-1])
    # R = R.T
    def create_adj_mat(R, n_users, n_items):
        t1 = time()
        adj_mat = sp.dok_matrix((n_users + n_items, n_users + n_items), dtype=np.float32)
        adj_mat = adj_mat.tolil()
        R = R.tolil()
        print(R.shape)
        # prevent memory from overflowing
        for i in range(5):
            adj_mat[int(n_users * i / 5.0):int(n_users * (i + 1.0) / 5), n_users:] = \
                R[int(n_users * i / 5.0):int(n_users * (i + 1.0) / 5)]
            adj_mat[n_users:, int(n_users * i / 5.0):int(n_users * (i + 1.0) / 5)] = \
                R[int(n_users * i / 5.0):int(n_users * (i + 1.0) / 5)].T
        adj_mat = adj_mat.todok()
        print('already create adjacency matrix', adj_mat.shape, time() - t1)

        t2 = time()

        def normalized_adj_single(adj):
            rowsum = np.array(adj.sum(1))
            d_inv = np.power(rowsum, -1).flatten()
            d_inv[np.isinf(d_inv)] = 0.
            d_mat_inv = sp.diags(d_inv)

            norm_adj = d_mat_inv.dot(adj)
            print('generate single-normalized adjacency matrix.')
            return norm_adj.tocoo()

        def check_adj_if_equal(adj):
            dense_A = np.array(adj.todense())
            degree = np.sum(dense_A, axis=1, keepdims=False)

            temp = np.dot(np.diag(np.power(degree, -1)), dense_A)
            print('check normalized adjacency matrix whether equal to this laplacian matrix.')
            return temp

        print(adj_mat.shape)
        norm_adj_mat = normalized_adj_single(adj_mat + sp.eye(adj_mat.shape[0]))
        mean_adj_mat = normalized_adj_single(adj_mat)

        print('already normalize adjacency matrix', time() - t2)
        return adj_mat.tocsr(), norm_adj_mat.tocsr(), mean_adj_mat.tocsr()

    adj_mat, norm_adj_mat, mean_adj_mat = create_adj_mat(R, user_num, item_num)
    sp.save_npz('Data/' + file + '/adj_mat.npz', adj_mat)
    sp.save_npz('Data/' + file + '/adj_norm_mat.npz', norm_adj_mat)
    sp.save_npz('Data/' + file + '/adj_mean_mat.npz', mean_adj_mat)
    adj_mat = adj_mat
    rowsum = np.array(adj_mat.sum(1))
    d_inv = np.power(rowsum, -0.5).flatten()
    d_inv[np.isinf(d_inv)] = 0.
    d_mat_inv = sp.diags(d_inv)
    norm_adj = d_mat_inv.dot(adj_mat)
    norm_adj = norm_adj.dot(d_mat_inv)
    print('generate pre adjacency matrix.')
    pre_adj_mat = norm_adj.tocsr()
    sp.save_npz('Data/' + file + '/adj_pre_mat.npz', norm_adj)











    print('============Create Test Data================')
    feat_col = [sparseFeature('user_id', user_num, embed_dim), sparseFeature('item_id', item_num, embed_dim)]
    # shuffle 随机排序列表
    train_dict = train_dict.sample(frac=1).reset_index(drop=True)
    val_dict = val_dict.sample(frac=1).reset_index(drop=True)
    all_user = np.array([i for i in range(user_num)], dtype=int)
    all_item = np.array([i for i in range(item_num)], dtype=int)

    train = [np.array(train_dict['user']), np.array(train_dict['pos']), np.array(train_dict['neg'])]
             # np.array([all_user for _ in range(len(train_dict['user']))]), \
             # np.array([all_item for _ in range(len(train_dict['user']))])]
    val = [np.array(val_dict['user']), np.array(val_dict['pos']), np.array(val_dict['neg'])]
           # np.array([all_user for _ in range(len(val_dict['user']))]), \
           # np.array([all_item for _ in range(len(val_dict['user']))])]

    test_data = defaultdict(list)
    with open(test_file) as f_test:
        for line in tqdm(f_test.readlines()):
            line = [int(x) for x in line.strip('\n').split(' ')[:101]]
            test_data['user'].append(line[0])
            test_data['pos'].append(line[1])
            test_data['neg'].append(np.array(line[2:]))

    test = [np.array(test_data['user']), np.array(test_data['pos']), np.array(test_data['neg'])]
    print('============Data Preprocess End=============')
    #
    # return feat_col, train, val, test, user_sim, item_sim
    return feat_col, train, val ,test, norm_adj_mat


#
files = ['ml-100k']
for file in files:
    feat_col, train, val, test, norm_adj_mat = load_data(file)
    print(train)

