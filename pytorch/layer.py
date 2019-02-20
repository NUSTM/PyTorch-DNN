#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Some common layers for deep neural network
Ubuntu 16.04 & PyTorch 1.0
Last update: KzXuan, 2019.02.19
"""
import math
import torch
import numpy as np
import torch.nn as nn
import torch.utils.data as Data
import torch.nn.functional as F


def embedding_layer(emb_matrix, emb_type='const'):
    """
    Initialize embedding place
    * emb_matrix [np.array]: embedding matrix with size (num, dim)
    * emb_type [str]: use None/'const'/'variable'/'random'
    - emb_mat [Module]: embedding query module
    """
    if emb_type == 'const':
        emb_mat = nn.Embedding.from_pretrained(torch.FloatTensor(emb_matrix))
    elif emb_type == 'variable':
        emb_mat = nn.Embedding.from_pretrained(torch.FloatTensor(emb_matrix))
        emb_mat.weight.requires_grad = True
    elif emb_type == 'random':
        emb_mat = nn.Embedding(emb_matrix.shape[0], emb_matrix.shape[1])
    else:
        emb_mat = None
    return emb_mat


def get_mask(inputs, seq_len, max_seq_len=None):
    """
    Get mask matrix
    * inputs [tensor]: tensor corresponding to seq_len (batch_size * max_seq_len * input_size)
    * seq_len [tensor]: sequence length vector
    * max_seq_len [int]: max sequence length
    - mask [tensor]: mask matrix for each sample (batch_size * max_seq_len)
    """
    seq_len = seq_len.type_as(inputs.data)
    max_seq_len = inputs.size(1) if max_seq_len is None else max_seq_len
    query = torch.arange(0, max_seq_len, device=inputs.device).unsqueeze(1).float()
    mask = torch.lt(query, seq_len.unsqueeze(0)).float().transpose(0, 1)
    return mask


class positional_embedding_layer(nn.Module):
    def __init__(self, emb_dim, max_len=512):
        """
        Generate positional embedding
        * emb_dim [int]: embedding dimension of the output
        * max_len [int]: max length to generate
        """
        assert emb_dim % 2 == 0, "! Embedding must be even."
        super(positional_embedding_layer, self).__init__()

        pe = torch.zeros(max_len, emb_dim).float()
        pe.require_grad = False

        position = torch.arange(0, max_len).float().unsqueeze(1)
        div_term = (torch.arange(0, emb_dim, 2).float() * -(math.log(10000.0) / emb_dim)).exp()

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, inputs):
        """
        Forward calculation of the layer
        * inputs [tensor]: input tensor (batch_size * max_seq_len * emb_dim)
        - outputs [tensor]: the same shape of positional embedding (max_seq_len * emb_dim)
        """
        outputs = self.pe[:, :inputs.size(1)]
        return outputs


class self_attention_layer(nn.Module):
    def __init__(self, n_hidden):
        """
        Self-attention layer
        * n_hidden [int]: hidden layer number (equal to 2*n_hidden if bi-direction)
        """
        super(self_attention_layer, self).__init__()
        self.attention = nn.Sequential(
            nn.Linear(n_hidden, n_hidden),
            nn.Tanh(),
            nn.Linear(n_hidden, 1)
        )

    def init_weights(self):
        """
        Initialize all the weights and biases for this layer
        """
        for m in self.attention.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, 0.01)
                nn.init.uniform_(m.bias, -0.01, 0.01)

    def forward(self, inputs, seq_len=None):
        """
        Forward calculation of the layer
        * inputs [tensor]: input tensor (batch_size * max_seq_len * n_hidden)
        * seq_len [tensor]: sequence length (batch_size,)
        - outputs [tensor]: attention output (batch_size * n_hidden)
        """
        if inputs.dim() != 3 or (seq_len is not None and seq_len.dim() != 1):
            raise ValueError("! Wrong dimemsion of the inputs parameters.")

        now_batch_size, max_seq_len, _ = inputs.size()
        alpha = self.attention(inputs).contiguous().view(now_batch_size, 1, max_seq_len)
        exp = torch.exp(alpha)

        if seq_len is not None:
            mask = get_mask(inputs, seq_len)
            mask = mask.contiguous().view(now_batch_size, 1, max_seq_len)
            exp = exp * mask

        sum_exp = exp.sum(-1, True) + 1e-9
        softmax_exp = exp / sum_exp.expand_as(exp).contiguous().view(now_batch_size, 1, max_seq_len)
        outputs = torch.bmm(softmax_exp, inputs).squeeze()
        return outputs


class CNN_layer(nn.Module):
    def __init__(self, input_size, in_channels, out_channels, kernel_width, stride=1):
        """
        CNN layer
        * input_size [int]: embedding dim or the last dim of the input
        * in_channels [int]: number of channels for inputs
        * out_channels [int]: number of channels for outputs
        * kernel_width [int]: the width on sequence for the first dim of kernel
        * stride [int]: controls the stride for the windows
        """
        super(CNN_layer, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_width = kernel_width

        self.conv = nn.Conv2d(in_channels, out_channels, (kernel_width, input_size), stride)
        self.ac_fun = nn.ReLU()

    def init_weights(self):
        """
        Initialize all the weights and biases for this layer
        """
        nn.init.xavier_uniform_(self.conv.weight, 0.01)
        nn.init.uniform_(self.conv.bias, -0.01, 0.01)

    def forward(self, inputs, seq_len=None, out_type='max'):
        """
        Forward calculation of the layer
        * inputs [tensor]: input tensor (batch_size * in_channels * max_seq_len * input_size)
        * seq_len [tensor]: sequence length (batch_size,)
        * out_type [str]: use 'max'/'mean'/'all' to choose
        - outputs [tensor]: outputs after max-pooling (batch_size * out_channels)
        """
        if inputs.dim() == 3:
            inputs = torch.unsqueeze(inputs, 1)
            inputs = inputs.repeat(1, self.in_channels, 1, 1)
        if inputs.dim() != 4 or (seq_len is not None and seq_len.dim() != 1):
            raise ValueError("! Wrong dimemsion of the inputs parameters.")

        now_batch_size, _, max_seq_len, _ = inputs.size()
        left_len = max_seq_len - self.kernel_width + 1
        outputs = self.conv(inputs)
        outputs = torch.reshape(outputs, [-1, self.out_channels, left_len])

        if seq_len is not None:
            mask = get_mask(inputs, seq_len - self.kernel_width + 1, left_len)
            mask = mask.contiguous().view(now_batch_size, 1, left_len)
            outputs = outputs * mask

        outputs = self.ac_fun(outputs)
        if out_type == 'max':
            outputs = F.max_pool1d(outputs, left_len).contiguous().view(-1, self.out_channels)
        elif out_type == 'mean':
            outputs = F.avg_pool1d(outputs, left_len).contiguous().view(-1, self.out_channels)
        elif out_type == 'all':
            outputs = outputs.transpose(1, 2)  # batch_size * left_len * n_hidden
        else:
            raise ValueError("! Wrong value of parameter 'out-type', accepts 'max'/'mean'/'all' only.")
        return outputs


class LSTM_layer(nn.Module):
    def __init__(self, input_size, n_hidden, n_layer, drop_prob,
                 bi_direction=True, GRU_enable=False):
        """
        LSTM layer
        * input_size [int]: embedding dim or the last dim of the input
        * n_hidden [int]: number of hidden layer nodes
        * n_layer [int]: number of classify layers
        * n_hidden [int]: number of hidden layer nodes
        * drop_prob [float]: drop out ratio
        * bi_direction [bool]: use bi-direction model or not
        * GRU_enable [bool]: use LSTM or GRU model
        """
        super(LSTM_layer, self).__init__()
        self.n_hidden = n_hidden
        self.n_layer = n_layer
        self.bi_direction_num = 2 if bi_direction else 1
        self.GRU_enable = GRU_enable
        model = nn.GRU if GRU_enable else nn.LSTM
        self.rnn = model(
            input_size=input_size,
            hidden_size=n_hidden,
            num_layers=n_layer,
            bias=True,
            batch_first=True,
            dropout=drop_prob if n_layer > 1 else 0,
            bidirectional=bi_direction
        )

    def init_weights(self):
        """
        Initialize all the weights and biases for this layer
        """
        for layer_p in self.rnn._all_weights:
            for p in layer_p:
                if 'weight' in p:
                    nn.init.xavier_uniform_(self.rnn.__getattr__(p), 0.01)
                elif 'bias' in p:
                    nn.init.uniform_(self.rnn.__getattr__(p), -0.01, 0.01)

    def forward(self, inputs, seq_len=None, out_type='all'):
        """
        Forward calculation of the layer
        * inputs [tensor]: input tensor (batch_size * max_seq_len * input_size)
        * seq_len [tensor]: sequence length (batch_size,)
        * out_type [str]: use 'all'/'last' to choose
        - outputs [tensor]: the last layer (batch_size * max_seq_len * (bi_direction*n_hidden))
        - h_last [tensor]: the last time step of the last layer (batch_size * (bi_direction*n_hidden))
        """
        if inputs.dim() != 3 or (seq_len is not None and seq_len.dim() != 1):
            raise ValueError("! Wrong dimemsion of the inputs parameters.")

        now_batch_size, max_seq_len, _ = inputs.size()
        if seq_len is not None:
            sort_seq_len, sort_index = torch.sort(seq_len, descending=True)  # sort seq_len
            _, unsort_index = torch.sort(sort_index, dim=0, descending=False)  # get back index
            sort_seq_len = torch.index_select(sort_seq_len, 0, torch.nonzero(sort_seq_len).contiguous().view(-1))
            n_pad = sort_index.size(0) - sort_seq_len.size(0)
            inputs = torch.index_select(inputs, 0, sort_index[:sort_seq_len.size(0)])
            now_batch_size, max_seq_len, _ = inputs.size()
            inputs = nn.utils.rnn.pack_padded_sequence(inputs, sort_seq_len, batch_first=True)

        self.rnn.flatten_parameters()
        if self.GRU_enable:
            outputs, h_last = self.rnn(inputs)  # h_last: (n_layer*bi_direction) * batch_size * n_hidden
        else:
            outputs, (h_last, _) = self.rnn(inputs)  # h_last: (n_layer*bi_direction) * batch_size * n_hidden
        if out_type == 'all':
            if seq_len is not None:
                outputs, _ = nn.utils.rnn.pad_packed_sequence(
                    outputs, batch_first=True, total_length=max_seq_len  # batch_size * seq_len * (2)n_hidden
                )
                outputs = F.pad(outputs, (0, 0, 0, 0, 0, n_pad))
                outputs = torch.index_select(outputs, 0, unsort_index)
            return outputs
        elif out_type == 'last':
            h_last = h_last.contiguous().view(
                self.n_layer, self.bi_direction_num, now_batch_size, self.n_hidden
            )  # n_layer * bi_direction * batch_size * n_hidden
            h_last = torch.reshape(
                h_last[-1].transpose(0, 1),
                [now_batch_size, self.bi_direction_num * self.n_hidden]
            )  # batch_size * (bi_direction*n_hidden)
            if seq_len is not None:
                h_last = F.pad(h_last, (0, 0, 0, n_pad))
                h_last = torch.index_select(h_last, 0, unsort_index)
            return h_last
        else:
            raise ValueError("! Wrong value of parameter 'out-type', accepts 'all'/'last' only.")


class softmax_layer(nn.Module):
    def __init__(self, n_in, n_out):
        """
        Softmax layer / Full connected layer
        * n_in [int]: number of input nodes
        * n_out [int]: number of output nodes
        """
        super(softmax_layer, self).__init__()
        self.connector = nn.Sequential(
            nn.Linear(n_in, n_out),
            nn.Softmax(-1)
        )

    def init_weights(self):
        """
        Initialize all the weights and biases for this layer
        """
        for m in self.connector.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, 0.01)
                nn.init.uniform_(m.bias, -0.01, 0.01)

    def forward(self, inputs):
        """
        Forward calculation of the layer
        * inputs [tensor]: inputs of a full connected layer
        """
        outputs = self.connector(inputs)
        return outputs


class multi_head_attention_layer(nn.Module):
    def __init__(self, input_size, n_hidden, n_head):
        """
        The multi-head attention operation in transformer
        * input_size [list]: input sizes for query & key & value
        * n_hidden [int]: number of hidden weight matrix nodes
        * n_head [int]: number of context attentions
        """
        super(multi_head_attention_layer, self).__init__()
        assert len(input_size) == 3, "! Need three values for 'input_size'."

        self.input_size = input_size
        self.n_hidden = n_hidden
        self.n_head = n_head
        self.attention = nn.ModuleList(
            [nn.Linear(isize, n_hidden * n_head, bias=False) for isize in input_size]
        )
        self.gather = nn.Linear(n_hidden * n_head, input_size[-1], bias=False)

    def forward(self, inputs):
        """
        Forward calculation of the layer
        * inputs [list]: query & key & value tensor (batch_size * max_seq_len * input_size)
        - outputs [tensor]: expression after attention (batch_size * max_seq_len * input_size)
        """
        assert len(inputs) == 3, "! Need three tensors for 'inputs'."

        batch_size = inputs[0].size(0)
        query, key, value = [
            torch.reshape(
                self.attention[i](inputs[i]),
                [batch_size, -1, self.n_head, self.n_hidden]
            ).transpose(1, 2) for i in range(3)
        ]
        score = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(query.size(-1))
        sum_score = score.sum(-1, True) + 1e-9
        score = score / sum_score.expand_as(score)
        outputs = torch.matmul(score, value)
        outputs = outputs.transpose(1, 2).contiguous().view(batch_size, -1, self.n_head * self.n_hidden)
        outputs = self.gather(outputs)
        return outputs


class transformer_layer(nn.Module):
    def __init__(self, input_size, n_hidden, n_head):
        """
        The whole transformer layer
        * input_size [int/list]: input sizes for query & key & value (give an int when all are equal)
        * n_hidden [int]: number of hidden weight matrix nodes
        * n_head [int]: number of attentions
        """
        super(transformer_layer, self).__init__()
        if type(input_size).__name__[:3] == 'int':
            input_size = [input_size] * 3
        elif type(input_size).__name__[:4] == 'list':
            assert len(input_size) == 3, "! Need three values for 'input_size'."

        self.attention = multi_head_attention_layer(input_size, n_hidden, n_head)
        self.norm_1 = nn.LayerNorm(input_size[-1])
        self.feed_forward = nn.Sequential(
            nn.Linear(input_size[-1], input_size[-1]),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(input_size[-1], input_size[-1]),
        )
        self.norm_2 = nn.LayerNorm(input_size[-1])

    def forward(self, inputs, seq_len=None, get_index=None):
        """
        Forward calculation of the layer
        * inputs [tensor/list]: input tensor (batch_size * max_seq_len * input_size)
                                give a list if not query == key == value
        * seq_len [tensor]: sequence length (batch_size,)
        * get_index [int/list/tuple]: give only the value of the index (None means all)
        - outputs [tensor]: attention output (batch_size * max_seq_len * input_size)
        """
        if type(inputs).__name__[:6] == 'Tensor':
            inputs = [inputs] * 3
        elif type(inputs).__name__[:4] == 'list':
            assert len(inputs) == 3, "! Need three tensors for 'inputs'."

        now_batch_size, max_seq_len, _ = inputs[0].size()
        outputs = self.norm_1(self.attention(inputs) + inputs[-1])
        outputs = self.norm_2(self.feed_forward(outputs) + outputs)

        if seq_len is not None:
            mask = get_mask(inputs[-1], seq_len)
            mask = mask.contiguous().view(now_batch_size, max_seq_len, 1)
            outputs = outputs * mask

        if get_index is not None:
            outputs = outputs[:, get_index, :]

        return outputs
