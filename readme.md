## PyTorch简单RNN模型

Version 1.7 by KzXuan

**包含了PyTorch实现的简单RNN模型（LSTM和GRU）用于NLP领域的分类及序列标注任务。**

相比TensorFlow，PyTorch拥有更为原生的Python语言写法，直接支持动态建图。



环境：

* Python 3.6/3.7
* PyTorch 0.4.1/1.0.0

超参数说明：

- cuda_enable [bool]	是否使用GPU加速
- GRU_enable [bool]	使用GRU或LSTM
-  bi_direction [bool]	双向LSTM/GRU
-  n_hierarchy [int]		RNN模型的层次数
-  n_layer [int]			每个层次的LSTM/GRU层数
-  use_attention [bool]	是否使用注意力机制（默认在每一级LSTM/GRU上添加）
-  emb_type [str]		使用None/'const'/'variable'/'random'表示Embedding模式
-  emb_dim [int]		Embedding维度（输入为特征时表示特征的维度）
-  n_class [int]			分类的目标类数
-  n_hidden [int]		LSTM/GRU的隐层节点数
-  learning_rate [float]	学习率
-  l2_reg [float]			L2正则
-  batch_size [int]		批量大小
-  iter_times [int]		迭代次数
-  display_step [int]		迭代过程中显示输出的间隔迭代次数
-  drop_prob [float]		Dropout比例
-  score_standard [str]	使用'P'/'R'/'F'/'Acc'设定模型评判标准

数据要求：

* 构建data_dict并送入模型，data_dict为数据字典，包含：
  * 'x' [np.array]		训练集输入数据
  * 'y' [np.array]		训练集标签
  * 'len' [list]		训练集序列长度，列表中元素皆为np.array，从前往后表示模型从下到上每一个序列层级的序列长度
  * 'tx' [np.array]	测试集输入数据，可选
  * 'ty' [np.array]	测试集标签，可选
  * 'tlen' [list]		测试集序列长度，可选

类及函数说明：

* default_args(data_dict=None)：

  接受data_dict作为参数，初始化所有超参数，并返回参数集。所有参数支持在命令行内直接赋值，或在得到返回值后修改。

* RNN(args)：

  基类，接受args参数集，初始化模型参数，并包含部分基本函数，集成多次运行取平均、参数网格搜索等功能。

* self_attention_model(n_hidden)：

  自注意力机制模型，接受隐层节点数n_hidden参数。

* LSTM_model(input_size, n_hidden, n_layer, drop_prob, bi_direction, GRU_enable=False, use_attention=False)：

  封装好的LSTM/GRU模型，可以独立运行，支持单/双向及注意力机制。

  调用时可选择输出模式"all"/"last"/“att"来分别得到最后一层的全部隐层输出，或最后一层的最后一个时间步的输出，或Attention后的输出。

* RNN_model(emb_matrix, args, model='classify')：

  常规RNN层次模型的封装，支持多层次的分类或序列标注，参数model可选"classify"/"sequence"，模型返回最后的预测结果。

* RNN_classify(data_dict, emb_matrix=None, args=None, class_name=None, col=None, width=None)：

  RNN分类模型的入口，使用RNN分类的导入类。

  * train_test(verbose=2)：训练-测试数据的调用函数
  * train_itself(verbose=2)：单一训练数据并使用本身进行测试的调用函数
  * cross_validation(fold=10, verbose=2)：k折交叉数据的调用函数

  参数class_name, col, width, verbose皆用以控制输出的显示内容、排版和输出内容等级。

* RNN_sequence(data_dict, emb_matrix=None, args=None, class_name=None, col=None, width=None)：

  RNN序列标注模型的入口，使用RNN序列标注的导入类。

  可调用函数同RNN_classify。



#### 模型功能及使用

* 分类

  ```python
  from model import default_args, RNN_classify
  
  emb_mat = np.array([...])
  data_dict = {...}
  args = default_args(data_dict)
  class_name = ['support', 'deny', 'query', 'comment']
  nn = RNN_classify(data_dict, emb_mat, args, class_name=class_name)
  nn.cross_validation(fold=10)
  ```

* 序列标注

  ```python
  from model import default_args, RNN_sequence
  
  emb_mat = np.array([...])
  data_dict = {...}
  args = default_args(data_dict)
  class_name = ['support', 'deny', 'query', 'comment']
  nn = RNN_sequence(data_dict, emb_mat, args, class_name=class_name)
  nn.train_test()
  ```

* 多次运行同一模型并取Accuracy的平均

  ```python
  args.score_standard = 'Acc'
  nn = RNN_classify(data_dict, emb_mat, args, class_name=class_name)
  nn.average_several_run(nn.train_test, times=5, verbose=2)
  ```

* 网格搜索调参

  ```python
  args.score_standard = 'F'
  nn = RNN_classify(data_dict, emb_mat, args, class_name=class_name)
  params_search = {"l2_reg": [1e-3, 1e-5], "batch_size": [64, 128]}
  nn.grid_search(nn.train_test, params_search=params_search)
  ```

