"""DQN Class

DQN(NIPS-2013)
"Playing Atari with Deep Reinforcement Learning"
https://www.cs.toronto.edu/~vmnih/docs/dqn.pdf

DQN(Nature-2015)
"Human-level control through deep reinforcement learning"
http://web.stanford.edu/class/psych209/Readings/MnihEtAlHassibis15NatureControlDeepRL.pdf
"""
import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()


class DQN:
    def __init__(self, session: tf.compat.v1.Session, input_size: int, output_size: int, 
        name: str="main", h_size=50) -> None:
        """DQN Agent can

        1) Build network
        2) Predict Q_value given state
        3) Train parameters

        Args:
            session (tf.Session): Tensorflow session
            input_size (int): Input dimension
            output_size (int): Number of discrete actions
            name (str, optional): TF Graph will be built under this name scope
        """
        self.session = session
        self.input_size = input_size
        self.output_size = output_size
        self.net_name = name

        # print(f'[dqn.py] input size is {input_size}')
        # print(f'[dqn.py] output size is {output_size}')

        self._build_network(h_size=h_size)

    def _build_network(self, h_size=16, l_rate=0.001) -> None:
        """DQN Network architecture (simple MLP)

        Args:
            h_size (int, optional): Hidden layer dimension
            l_rate (float, optional): Learning rate
        """
        with tf.device("/gpu:0"):
            with tf.compat.v1.variable_scope(self.net_name):
                self._X = tf.placeholder(tf.float32, [None, self.input_size], name="input_x")
                net = self._X

                # matmul self._X and h_size (hidden layer) and activation func is relu
                net = tf.layers.dense(net, h_size, activation=tf.nn.relu)
                # matmul net and output
                net = tf.layers.dense(net, self.output_size, name="Q_pred")
                self._Qpred = net
                # so, _Qpred = self._X * net(relu) * output_size

                self._Y = tf.placeholder(tf.float32, shape=[None, self.output_size])
                self._loss = tf.losses.mean_squared_error(self._Y, self._Qpred)

                optimizer = tf.train.AdamOptimizer(learning_rate=l_rate)
                self._train = optimizer.minimize(self._loss)

    def predict(self, state: np.ndarray) -> np.ndarray:
        """Returns Q(s, a)

        Args:
            state (np.ndarray): State array, shape (n, input_dim)

        Returns:
            np.ndarray: Q value array, shape (n, output_dim)
        """
        # print(f'[dqn.py] state is {state}')
        # print(f'[dqn.py] len state is {len(state)}')
        # print(f'[dqn] input_size: {self.input_size}')
        # print(f'[dqn] state len: {len(state)}')
        x = np.reshape(state, [-1, self.input_size])

        # print(f'[dqn.py] x is {x}')
        # print(f'[dqn.py] x len is {len(x)}')
        # print(f'[dqn.py] x[0] is {x[0]}')
        # print(f'[dqn.py] x[0] len is {len(x[0])}')
        # print(f'[dqn.py] predicting state....')

        return self.session.run(self._Qpred, feed_dict={self._X: x})

    def update(self, x_stack: np.ndarray, y_stack: np.ndarray) -> list:
        """Performs updates on given X and y and returns a result

        Args:
            x_stack (np.ndarray): State array, shape (n, input_dim)
            y_stack (np.ndarray): Target Q array, shape (n, output_dim)

        Returns:
            list: First element is loss, second element is a result from train step
        """
        feed = {
            self._X: x_stack,
            self._Y: y_stack
        }
        return self.session.run([self._loss, self._train], feed)
