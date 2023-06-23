"""
Double DQN (Nature 2015)
http://web.stanford.edu/class/psych209/Readings/MnihEtAlHassibis15NatureControlDeepRL.pdf

Notes:
    The difference is that now there are two DQNs (DQN & Target DQN)

    y_i = r_i + 𝛾 * max(Q(next_state, action; 𝜃_target))

    Loss: (y_i - Q(state, action; 𝜃))^2

    Every C step, 𝜃_target <- 𝜃

"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
import random
from collections import deque
import dqn2
# import gym
from typing import List

import VideoEnv
import h5py

# env = gym.make('CartPole-v0')
# env = gym.wrappers.Monitor(env, directory="gym-results/", force=True)

videoEnv = VideoEnv.VideoEnv()

# Constants defining our neural network
# INPUT_SIZE = env.observation_space.shape[0] # this is 16
# OUTPUT_SIZE = env.action_space.n # this is 4
INPUT_SIZE = videoEnv.INPUT_SIZE
OUTPUT_SIZE = videoEnv.OUTPUT_SIZE

DISCOUNT_RATE = 0.9
REPLAY_MEMORY = 5000
BATCH_SIZE = 64
TARGET_UPDATE_FREQUENCY = 5
MAX_EPISODES = videoEnv.MAX_EPISODES

HIDDEN_LAYER_SIZE = 28

# name first: version / second: hidden size / third: minor-version
MODEL_NAME = ['model_07_28_28_01', 'model_07_28_28_02']

def replay_train(mainDQN: dqn2.DQN, targetDQN: dqn2.DQN, train_batch: list) -> float:
    """Trains `mainDQN` with target Q values given by `targetDQN`

    Args:
        mainDQN (dqn.DQN): Main DQN that will be trained
        targetDQN (dqn.DQN): Target DQN that will predict Q_target
        train_batch (list): Minibatch of replay memory
            Each element is (s, a, r, s', done)
            [(state, action, reward, next_state, done), ...]

    Returns:
        float: After updating `mainDQN`, it returns a `loss`
    """
    states = np.vstack([x[0] for x in train_batch])
    actions = np.array([x[1] for x in train_batch])
    rewards = np.array([x[2] for x in train_batch])
    next_states = np.vstack([x[3] for x in train_batch])

    X = states
    # print(f'a state is: {targetDQN.predict(next_states)}')
    # print(f'len states is: {len(targetDQN.predict(next_states[0]))}')

    # Q_target should be 64x1 to 64x5
    Q_target = rewards + DISCOUNT_RATE * np.max(targetDQN.predict(next_states), axis=1)
    # print(f'Q_target is: {Q_target}')

    n_Q_target = np.zeros((len(Q_target), 5))
    states_bitrates = states[0:, 4:9]
        
    for i in range(len(states_bitrates)):
        for j in range(5): 
            if states_bitrates[i][j] != 0:
                n_Q_target[i][j] = Q_target[i]

    # Train our network using target and predicted Q values on each episode
    return mainDQN.update(X, n_Q_target)


def get_copy_var_ops(*, dest_scope_name: str, src_scope_name: str) -> List[tf.Operation]:
    """Creates TF operations that copy weights from `src_scope` to `dest_scope`

    Args:
        dest_scope_name (str): Destination weights (copy to)
        src_scope_name (str): Source weight (copy from)

    Returns:
        List[tf.Operation]: Update operations are created and returned
    """
    # Copy variables src_scope to dest_scope
    op_holder = []

    # tf.GraphKeys.TRAINABLE_VARIABLES is variables when training is going
    src_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=src_scope_name)
    dest_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=dest_scope_name)

    # assign is equal to copy
    for src_var, dest_var in zip(src_vars, dest_vars):
        # dest_var is a tensor
        op_holder.append(dest_var.assign(src_var.value()))

    return op_holder

def train_dqn_model(h_size=50):
    # store the previous observations in replay memory
    replay_buffer = deque(maxlen=REPLAY_MEMORY)

    last_100_reward = deque(maxlen=100)

    with tf.device("/gpu:0"):
        with tf.compat.v1.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
            mainDQN = dqn2.DQN(sess, INPUT_SIZE, OUTPUT_SIZE, name="main", h_size=h_size)
            targetDQN = dqn2.DQN(sess, INPUT_SIZE, OUTPUT_SIZE, name="target", h_size=h_size)
            sess.run(tf.global_variables_initializer())

            # initial copy q_net -> target_net
            # this means that 'targetDQN = mainDQN'
            copy_ops = get_copy_var_ops(dest_scope_name="target",
                                        src_scope_name="main")
            sess.run(copy_ops)

            for episode in range(MAX_EPISODES):
                e = 1. / ((episode / 10) + 1)
                # done = False
                step_count = 0
                # state = env.reset()
                MAX_TIMESLOT = videoEnv.getMaxTimeSlot(episode)

                for timeslot in range(MAX_TIMESLOT):
                    # print(f'\t[videoDQN] start timeslot is {timeslot}')
                    state = videoEnv.getState(episode, timeslot)

                    if np.random.rand() < e:
                        action = videoEnv.action_sample(state)
                        # print(f'[videoDQN] action is sampling!')
                    else:
                        # Choose an action by greedily from the Q-network
                        # print(f'[videoDQN] {mainDQN.predict(VideoEnv.transformStatetoList(state))}')
                        tmp = 0
                        actions = mainDQN.predict(VideoEnv.transformStatetoList(state))
                        if np.argmax(actions) == 0:
                            index = [0]
                            actions = np.delete(actions, index)
                            tmp = 1
                        action = np.argmax(actions) + tmp

                        action_space = []
                        for i in range(videoEnv.CLIENT_NUM):
                            if state['client'][i]['bitrate'] == 0:
                                action_space.append(0)
                            else:
                                action_space.append(action)
                        action = action_space

                        # print(f'\033[95m[videoDQN] action is {action}\033[0m')

                    # print(f'[videoDQN] state is {state}')
                    # print(f'[videoDQN] len state is {len(state)}')
                    # print(f'[videoDQN] action is {action}')

                    # Get new state and reward from environment
                    # print(f'replay buffer len is {len(replay_buffer)}')
                    next_state, reward = videoEnv.step(state, action)

                    # Save the experience to our buffer
                    # Not imediately training the results. firstly insert those in the buffer.
                    replay_buffer.append((VideoEnv.transformStatetoList(state), 
                        action, 
                        reward, 
                        VideoEnv.transformStatetoList(next_state)))

                    if len(replay_buffer) > BATCH_SIZE:
                        # when training, do sampling randomly in the buffer and training with that
                        minibatch = random.sample(replay_buffer, BATCH_SIZE)
                        loss, _ = replay_train(mainDQN, targetDQN, minibatch)
                        # print(f'result_train_step len is {len(result_train_step)}')

                    if step_count % TARGET_UPDATE_FREQUENCY == 0:
                        # Update weight of target dqn in every regular interval
                        sess.run(copy_ops)

                    step_count += 1

                    print("                                 ", end='\r', flush=True)
                    print("Episode: {}/{}  steps: {}/{}".format(episode, MAX_EPISODES-1, timeslot, MAX_TIMESLOT-1),
                    end='\r', flush=True)


                    # print(f'[videoDQN] episode is {episode}/{MAX_EPISODES-1}', end='\r', flush=True)
                    # print(f'[videoDQN] end timeslot is {timeslot}/{MAX_TIMESLOT-1}', end='\r', flush=True)
                    # print(f'replay buffer len is {len(replay_buffer)}')

                # print("Episode: {}/{}  steps: {}/{}".format(episode, MAX_EPISODES-1, timeslot, MAX_TIMESLOT-1),
                    # end='\r', flush=True)
                # print(f'replay buffer len is {len(replay_buffer)}')

                last_100_reward.append(step_count)

                if len(last_100_reward) == last_100_reward.maxlen:
                    avg_reward = np.mean(last_100_reward)

            # targetDQN.save('model/model_01')
            saver = tf.train.Saver()
            saver.save(targetDQN.session, 'model/' + MODEL_NAME[-1])

            print(f'Training is done                          ')
            target_actions = []
            # for episode in range(MAX_EPISODES):
            #     MAX_TIMESLOT = videoEnv.getMaxTimeSlot(episode)

            #     for timeslot in range(MAX_TIMESLOT):
            #         state = videoEnv.getState(episode, timeslot)

            #         t_state = VideoEnv.transformStatetoList(state)

            #         action = np.argmax(targetDQN.predict(t_state))
            #         # action = sess.run(Q_pred, feed_dict={X: t_state})

            #         action_space = []
            #         for i in range(videoEnv.CLIENT_NUM):
            #             if state['client'][i]['bitrate'] == 0:
            #                 action_space.append(0)
            #             else:
            #                 action_space.append(action)
            #         action = action_space

            #         target_actions.append(action)

                    # print(f'predicted action is: {action}')

    return target_actions

def load_model(sess: tf.compat.v1.Session, model_index):
    modelDir = 'model/'
    modelName = MODEL_NAME[model_index]

    # sess = tf.compat.v1.Session(config=tf.ConfigProto(allow_soft_placement=True))
    # sess.run(tf.global_variables_initializer())

    print(f'load model: {modelDir}{modelName}')
    saver = tf.train.import_meta_graph(modelDir + modelName + '.meta')
    # saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES), scope=modelDir+modelName)

    # saver.restore(sess, tf.train.latest_checkpoint(modelDir + '/'))
    # saver = tf.train.Saver()
    saver.restore(sess, modelDir + modelName)
    # saver.restore(sess, tf.train.latest_checkpoint(modelDir))

    # all_vars = tf.get_collection('vars')
    # for v in all_vars:
    #     v_ = sess.run(v)

    # targetDQN = dqn.DQN(sess, INPUT_SIZE, OUTPUT_SIZE, name="target")
        # saver = 
    # graph = tf.Graph()
    # print(graph.get_name_scope())
    # print(graph.get_all_collection_keys())
    vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope="target")
    # for v in zip(vars):
    #     print(v)
    h_size = len(sess.run(vars[0])[0])
    print(f'h size is: {h_size}')

    # X = graph.get_tensor_by_name("input_x:0")
    # Q_pred = graph.get_tensor_by_name("Q_pred:0")

    predDQN = dqn2.DQN(sess, INPUT_SIZE, OUTPUT_SIZE, name="pred", h_size=h_size)
    copy_ops = get_copy_var_ops(dest_scope_name="pred", src_scope_name="target")
    sess.run(copy_ops)

    return predDQN

def test_saved_model(modelDQN: dqn2.DQN=None, model_index=0):
    with tf.compat.v1.Session(graph=tf.Graph(), config=tf.ConfigProto(allow_soft_placement=True)) as sess:
        if modelDQN == None:
            modelDQN = load_model(sess, model_index)

        saved_actions = []

        for episode in range(MAX_EPISODES):
            MAX_TIMESLOT = videoEnv.getMaxTimeSlot(episode)

            for timeslot in range(MAX_TIMESLOT):
                state = videoEnv.getState(episode, timeslot)

                t_state = VideoEnv.transformStatetoList(state)

                action = np.argmax(modelDQN.predict(t_state))
                # action = sess.run(Q_pred, feed_dict={X: t_state})

                action_space = []
                for i in range(videoEnv.CLIENT_NUM):
                    if state['client'][i]['bitrate'] == 0:
                        action_space.append(0)
                    else:
                        action_space.append(action)
                action = action_space

                saved_actions.append(action)

                # print(f'predicted action is: {action}')

    return saved_actions

def run_saved_model(state, model_index=0):
    with tf.compat.v1.Session(graph=tf.Graph(), config=tf.ConfigProto(allow_soft_placement=True)) as sess:
        modelDQN = load_model(sess, model_index)
        # print('\033[95m' + f'run_saved_model state: loaded the model' + '\033[0m')
        t_state = VideoEnv.transformStatetoList(state)
        print(f'Current state: {t_state}')
        # t_state = np.array([t_state])
        # print('\033[95m' + f'run_saved_model state: {state}' + '\033[0m')
        # print('\033[95m' + f'run_saved_model t_state: {t_state}' + '\033[0m')
        # print('\033[95m' + f'run_saved_model len(t_state): {len(t_state)}' + '\033[0m')
        tmp = 0
        actions = modelDQN.predict(t_state)
        if np.argmax(actions) == 0:
            index = [0]
            actions = np.delete(actions, index)
            tmp = 1
        action = np.argmax(actions) + tmp
        print(f'Predicted action: {np.round(actions, 3)}')
        # action = sess.run(Q_pred, feed_dict={X: t_state})

        action_space = []
        for i in range(videoEnv.CLIENT_NUM):
            if state['client'][i]['bitrate'] == 0:
                action_space.append(0)
            else:
                action_space.append(action)
        action = action_space

        return action


if __name__ == "__main__":
    target_actions = train_dqn_model(HIDDEN_LAYER_SIZE)
    # saved_actions_1 = test_saved_model(model_index=0)
    # saved_actions_2 = test_saved_model(model_index=1)

    # saved_actions_1 = np.array(saved_actions_1)
    # saved_actions_2 = np.array(saved_actions_2)

    # print(f'actions equal?: {np.array_equal(saved_actions_1, saved_actions_2)}')
