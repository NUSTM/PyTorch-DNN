#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use RNN classify model
Last update: KzXuan, 2019.04.11
"""
import numpy as np
import word_vector as wv
import easy_function as ef
from dir_set import dir
from step_print import slash, run_time
from dnn.pytorch.base import default_args
from dnn.pytorch.exec import RNN_classify

sl, rt = slash(), run_time("* PyTorch RNN classify model")

w2v = wv.load_word2vec(dir.W2V_GOOGLE, type='txt')
emb_mat = w2v.get_matrix()
print("- Embedding matrix size:", emb_mat.shape)

sl.start("* Load data")
data_dict = {
    'x': np.load(dir.TRAIN + "index(4519,3,30).npy"),
    'y': np.load(dir.TRAIN + "y(4519,4).npy"),
    'len': [np.load(dir.TRAIN + "len_sen(4519,3).npy"), np.load(dir.TRAIN + "len_seq(4519,).npy")],
    'tx': np.load(dir.TEST + "index(1049,3,30).npy"),
    'ty': np.load(dir.TEST + "y(1049,4).npy"),
    'tlen': [np.load(dir.TEST + "len_sen(1049,3).npy"), np.load(dir.TEST + "len_seq(1049,).npy")],
}
sl.stop()
ef.print_shape(data_dict)

args = default_args()
args.emb_type = 'const'
args.emb_dim = w2v.vector_size
args.n_class = 4
args.n_hidden = 50
args.learning_rate = 0.001
args.l2_reg = 0.0
args.batch_size = 64
args.iter_times = 20
args.display_step = 1
args.drop_porb = 0.1
args.rnn_type = 'GRU'
args.use_attention = True

class_name = ['support', 'deny', 'query', 'comment']
nn = RNN_classify(data_dict, emb_mat, args, class_name=class_name)
nn.train_test()

rt.stop()
