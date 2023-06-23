from VideoState import VideoState
import random
import numpy as np
import rlserverConfig
import estimateGMSD

class VideoEnv:
    def __init__(self, num_of_quality=4, client_num=25):
        self._log = "[VideoEnv]"

        self.videoState = VideoState(MAX_CLIENT_NUM=client_num, use_gmsd_estimation=True,
            subDir=rlserverConfig.subDir_in_DDQN_training)
        # input size of server state: n x m x 3
        #   n is a variable (number of files),
        #   m is a variable (number of time slot)
        #   3 is a number of server state information
        # input size of client state: n x 5 x m x 6
        #   n is a variable (number of files),
        #   m is a variable (number of time slot)
        #   5 is a number of clients.
        #   6 -> 7 is a number of client state information
        #       (bitrate, bufferLevel, SSIM, player resolution(screen resolution), stalling, 
        #           bitrate switching, rx)
        # 221006
        #   7 -> 6 is a number of client state information (exclude player resolution)
        #       (bitrate, bufferLevel, SSIM, stalling, 
        #           bitrate switching, rx)
        # n, m of server state is equal to client's
        # 221006
        #   6 -> 6 is a number of client state information (exclude player resolution)
        #       (bitrate, bufferLevel, SSIM, stalling, 
        #           bitrate switching, throughput)
        # n, m of server state is equal to client's

        # output size is a number of clients
        #   range of 0 to 3 (0 is very low, 3 is very high that is original)

        # Total input size is 303
        # server: 3
        # server size change tx to tx+rx.
        # client: 300
        # client size exclude tx.
        self._SERVER_SIZE = 3
        self._CLIENT_SIZE = 6
        # client size exclude rx. cause very low receive rate data
        # self._CLIENT_SIZE = 6

        self.INPUT_SIZE = self._SERVER_SIZE + self._CLIENT_SIZE * client_num
        self.OUTPUT_SIZE = num_of_quality + 1 # number of action space + None (means all clients don't play the video)
        self.MAX_EPISODES = len(self.videoState.server_throughput)

        self.ENOUGH_CLIENT_BUFFER_SIZE = rlserverConfig.ENOUGH_CLIENT_BUFFER_SIZE

        # keep: model_07_28_28_01
        # self.W1_SSIM = 1.2
        # self.W2_bitrate = 1.5
        # self.W3_switching = 2.2
        # self.W4_fairness = 0.7
        # self.W5_stalling = 0.6
        # self.W6_buffer = 1.1

        # keep: 'dmodel_01_100_50_02', 120M
        # self.W1_GMSD = 1.2
        # self.W2_bitrate = 1.3
        # self.W3_switching = 0.8
        # self.W4_fairness = 0.9
        # self.W5_stalling = 0.8
        # self.W6_buffer = 0.8

        self.W1_GMSD = 1.3
        self.W2_bitrate = 1.4
        self.W3_switching = 0.8
        self.W4_fairness = 0.9
        self.W5_stalling = 1
        self.W6_buffer = 0.9

        # [reward coefficient]  #
        self.reward_calibration_factor = 1

        self.reward_calibration_factor = self.W1_GMSD + self.W2_bitrate + self.W3_switching + \
                                        self.W4_fairness + self.W5_stalling + self.W6_buffer
        self.reward_calibration_factor = 1 / self.reward_calibration_factor
        #########################

        # num_of_quality is a number of video qualities.
        # current quality resolutions are 240, 360, 480, 720 each other (total is 4)
        self.QUALITY_NUM = [i+1 for i in range(num_of_quality)]
        self.ACTION_BITRATE = [0, 400, 800, 1401, 2000]
        # based on calculate first frame bitween target and original video
        # self.MAX_SSIM = [0, 0.83532, 0.94629, 0.97547, 1.0]
        self.MAX_GMSD = [0, 0.91456, 0.96609, 0.98147, 1.0]

        # 0 means 'not provide quality'
        self.CLIENT_NUM = client_num
        self.action_space = [0 for i in range(self.CLIENT_NUM)]

        # penaly value, deprecated
        # self.PENALTY_GMSD = 0.15

    def getMaxTimeSlot(self, episode):
        return len(self.videoState.server_throughput[episode])

    def getState(self, episode, time_slot):
        return self._transformStatetoDict(episode, time_slot)

    # n is episode
    # m is time slot
    def _transformStatetoDict(self, n, m):
        state = {}
        server_state = [0 for i in range(3)]
        client_state = [{} for i in range(self.CLIENT_NUM)]
        state['server'] = server_state
        state['client'] = client_state

        server_state[0] = self.videoState.server_capacity
        server_state[1] = self.videoState.server_throughput[n][m]
        server_state[2] = self.videoState.server_connected_player[n][m]

        for i in range(self.CLIENT_NUM):
            client_state[i]['bitrate'] = self.videoState.client_bitrate[n][i][m]
            client_state[i]['bufferLevel'] = self.videoState.client_bufferLevel[n][i][m]
            client_state[i]['GMSD'] = float(self.videoState.client_GMSD[n][i][m])
            # if self.videoState.client_bitrate[n][i][m] == 0:
            #     client_state[i]['player_resolution'] = 0
            # else:
            #     client_state[i]['player_resolution'] = self.videoState.client_player_resolution[n][i]
            client_state[i]['stalling'] = self.videoState.client_stalling[n][i][m]
            client_state[i]['bitrate_switching'] = self.videoState.client_bitrate_switching[n][i][m]
            # client_state[i]['tx'] = self.videoState.client_tx[n][i][m]
            client_state[i]['throughput'] = self.videoState.client_throughput[n][i][m]

        return state

    def action_sample(self, current_state):
        # bitrate is a list maybe
        # current_state change to bitrate
        clients_states = current_state['client']
        # action_space = []

        # for i in range(self.CLIENT_NUM):
        #     if clients_states[i]['bitrate'] == 0:
        #         action_space.append(0)
        #     else:
        #         action_space.append(random.choice(self.QUALITY_NUM))

        for i in range(self.CLIENT_NUM):
            if clients_states[i]['bitrate'] == 0:
                action = 0
            else:
                action = random.choice(self.QUALITY_NUM)
                break

        return action

    def reward(self, state):
        server_state = state['server']
        client_state = state['client']

        client_num = 0
        for i in range(self.CLIENT_NUM):
            if client_state[i]['bitrate'] == 0:
                continue
            client_num += 1

        if client_num == 0:
            reward = -500
            return reward
        # plan 1: bitrate / server_capacity
        # plan 2: bitrate / avg_bitrate
        # plan 3: softmax(bitrate)
        # conclusion: (sigma(bitrate) / client_num) / max_bitrate
        bitrate = 0
        for i in range(self.CLIENT_NUM):
            bitrate += client_state[i]['bitrate'] / self.ACTION_BITRATE[-1]
            # bitrate += client_state[i]['bitrate'] * \
            #     (client_state[i]['bitrate'] / self.ACTION_BITRATE[-1])
        avg_bitrate = bitrate / client_num
        # r_bitrate = avg_bitrate / self.ACTION_BITRATE[-1]
        r_bitrate = avg_bitrate

        r_server_usage = 0
        if self.ACTION_BITRATE[-1] * self.CLIENT_NUM >= server_state[0]:
            pass
        else:
            r_server_usage -= (server_state[0] - bitrate)

        # conclustion: sigma(GMSD) / client_num
        GMSD = 0
        for i in range(self.CLIENT_NUM):
            if client_state[i]['GMSD'] > 1:
                GMSD += 1
            else:
                GMSD += client_state[i]['GMSD']
        r_GMSD = GMSD / client_num

        # plan 1: bitrate_switching
        # plan 2: cumulative bitrate_switching
        # conclusion: cumulative bitrate_switching
        bitrate_switching = 0
        for i in range(self.CLIENT_NUM):
            bitrate_switching += client_state[i]['bitrate_switching']
        r_switching = bitrate_switching / client_num

        # plan 1: stalling
        # plan 2: cumulative stalling
        # conclusion: cumulative stalling
        stalling = 0
        for i in range(self.CLIENT_NUM):
            stalling += client_state[i]['stalling']
        r_stalling = stalling / client_num

        # plan 1: bitrate_fairness
        # plan 2: cumulative bitrate_fairness
        # conclusion: jain's fairness index
        n_fairness = 0
        d_fairness = 0
        for i in range(self.CLIENT_NUM):
            n_fairness += client_state[i]['bitrate']
        n_fairness = n_fairness ** 2
        
        for i in range(self.CLIENT_NUM):
            d_fairness += client_state[i]['bitrate'] ** 2
        d_fairness = d_fairness * client_num

        r_fairness = n_fairness / d_fairness

        bufferLevel = 0
        for i in range(self.CLIENT_NUM):
            bl = client_state[i]['bufferLevel']
            if bl > self.ENOUGH_CLIENT_BUFFER_SIZE:
                bl = self.ENOUGH_CLIENT_BUFFER_SIZE
            bufferLevel += bl
        avg_bufferLevel = bufferLevel / client_num
        r_bufferLevel = avg_bufferLevel / self.ENOUGH_CLIENT_BUFFER_SIZE

        # reward function: polynomial function
        reward = self.W1_GMSD*r_GMSD + \
            self.W2_bitrate*r_bitrate + \
            self.W3_switching*(1 - r_switching) + \
            self.W5_stalling*(1 - r_stalling) + \
            self.W4_fairness*r_fairness + \
            self.W6_buffer*r_bufferLevel

        # reward = self.W1_GMSD*r_GMSD - \
        #     (self.W3_switching*r_switching + self.W5_stalling*r_stalling) + \
        #     self.W4_fairness*r_fairness + self.W6_buffer*r_bufferLevel


        ############
        # n_reward = self.W1_GMSD*r_GMSD + \
        #     self.W2_bitrate*r_bitrate + \
        #     self.W4_fairness*r_fairness + \
        #     self.W6_buffer*r_bufferLevel

        # d_reward = 1 + \
        #     self.W3_switching*r_switching + \
        #     self.W5_stalling*r_stalling

        # reward = n_reward / d_reward
        ###########

        # reward = reward * self.reward_calibration_factor + r_server_usage/10
        reward = reward * self.reward_calibration_factor

        return reward

    # predict next state if doing an action on the current state
    def step(self, current_state, action):
        next_state = {}
        current_server = current_state['server']
        current_client = current_state['client']

        next_server = [0 for i in range(3)]
        next_client = [{} for i in range(self.CLIENT_NUM)]
        next_state['server'] = next_server
        next_state['client'] = next_client

        next_server[0] = current_server[0] # server_capacity
        next_server[1] = current_server[1] # server_throughput
        next_server[2] = current_server[2] # server_connected_player

        # client side state
        # print(f'{self._log} action is {action}')

        for i in range(self.CLIENT_NUM):
            if current_client[i]['bitrate'] == 0:
                next_client[i]['bitrate'] = 0
                next_client[i]['bufferLevel'] = 0
                next_client[i]['GMSD'] = 0
                # next_client[i]['player_resolution'] = 0
                next_client[i]['stalling'] = 0
                next_client[i]['bitrate_switching'] = 0
                # next_client[i]['tx'] = 0
                next_client[i]['throughput'] = 0
            else:
                next_client[i]['bitrate'] = self.ACTION_BITRATE[action]
                # next_client[i]['player_resolution'] = current_client[i]['player_resolution']
                
                # decide low quality
                if current_client[i]['bitrate'] > self.ACTION_BITRATE[action]:
                    # TO DO
                    # next_server_throughput -= self.ACTION_BITRATE[action[i]]
                    next_client[i]['throughput'] = current_client[i]['throughput'] - \
                        (current_client[i]['bitrate'] - self.ACTION_BITRATE[action])
                    next_server[1] -= (current_client[i]['bitrate'] - self.ACTION_BITRATE[action]) / 8
                    if next_client[i]['throughput'] < 0:
                        next_client[i]['throughput'] = 0

                    next_client[i]['GMSD'] = self.MAX_GMSD[action]
                    next_client[i]['bufferLevel'] = current_client[i]['bufferLevel'] + 1
                    next_client[i]['stalling'] = 0
                    next_client[i]['bitrate_switching'] = 1

                # decide high quality
                elif current_client[i]['bitrate'] < self.ACTION_BITRATE[action]:
                    # TO DO
                    # next_server_throughput += self.ACTION_BITRATE[action[i]]
                    next_client[i]['throughput'] = current_client[i]['throughput'] + \
                        (self.ACTION_BITRATE[action] - current_client[i]['bitrate'])
                    next_server[1] += (self.ACTION_BITRATE[action]- current_client[i]['bitrate']) / 8

                    # next_client[i]['SSIM'] = current_client[i]['SSIM']
                    next_client[i]['bufferLevel'] = current_client[i]['bufferLevel'] - 1
                    if next_client[i]['bufferLevel'] < 0:
                        next_client[i]['bufferLevel'] = 0

                    next_client[i]['bitrate_switching'] = 1

                    if current_client[i]['bufferLevel'] <= 1:
                        next_client[i]['stalling'] = 1
                        # next_client[i]['SSIM'] = current_client[i]['SSIM'] - self.PENALTY_SSIM
                    else:
                        # next_client[i]['stalling'] = current_client[i]['stalling']
                        next_client[i]['stalling'] = 0
                        # if current_client[i]['stalling'] == 1:
                        #     next_client[i]['SSIM'] = current_client[i]['SSIM']
                        # else:
                        #     next_client[i]['SSIM'] = self.MAX_SSIM[action[i]]
                    next_client[i]['GMSD'] = self.MAX_GMSD[action]
                # decide previous quality
                else:
                    # next_client[i]['SSIM'] = current_client[i]['SSIM']
                    next_client[i]['GMSD'] = self.MAX_GMSD[action]
                    next_client[i]['bufferLevel'] = current_client[i]['bufferLevel']
                    next_client[i]['stalling'] = current_client[i]['stalling']
                    next_client[i]['bitrate_switching'] = 0
                    # next_client[i]['tx'] = current_client[i]['tx']
                    next_client[i]['throughput'] = current_client[i]['throughput']

        if next_server[1] > self.videoState.server_capacity:
            next_server[1] = self.videoState.server_capacity

        reward = self.reward(next_state)

        return next_state, reward

def transformStatetoList(state: dict, use_in_rlserver=False):
    state_list = []

    # insert min-max algorithm
    state = _min_max_scaler(state)

    server_state = state['server']
    client_state = state['client']

    for i in range(len(server_state)):
        state_list.append(server_state[i])

    if use_in_rlserver is True:
        gmsd_model = None
        try:
            gmsd_model = estimateGMSD.loadLinearModel()
        except:
            gmsd_model = None

    # result is 5 x 6 -> 5 x 8
    client_values = []
    for cs in client_state:
        if use_in_rlserver is True:
            tmp = []
            for key, value in cs.items():
                if key in 'GMSD':
                    pred = [0.7]
                    if value == 0:
                        pred = [0.7]
                    if gmsd_model is not None:
                        pred = estimateGMSD.predictLinearModel(gmsd_model, cs)
                    tmp.append(float(pred[0]))
                else:
                    tmp.append(float(value))

            client_values.append(tmp)
        else:
            client_values.append([float(value) for value in cs.values()])

    # reshape (nxm) -> (mxn) but all columns data make row data
    for i in range(len(client_values[0])):
        for j in range(len(client_values)):
            state_list.append(client_values[j][i])

    return state_list

def _min_max_scaler(state: dict):
    server_state = state['server']

    ## server state scaling
    server_capacity = server_state[0] # server_capacity
    server_state[0] = server_state[0] / server_capacity

    server_throughput = server_state[1] # server_throughput
    server_state[1] = server_state[1] / server_capacity
    if server_state[1] > 1:
        server_state[1] = 1

    server_connected_player = server_state[2] # server_connected_player
    server_state[2] = server_state[2] / rlserverConfig.rl_client_num

    ## clients state scaling
    client_state = state['client']

    for cs in client_state:
        for key, value in cs.items():
            if key == 'GMSD': # already [0,1]
                pass
            elif key == 'bitrate':
                cs[key] = cs[key] / rlserverConfig.MAX_BITRATE
            elif key == 'bitrate_switching': # already [0,1]
                pass
            elif key == 'stalling': # already [0,1]
                pass
            elif key == 'throughput':
                cs[key] = cs[key] / server_capacity
                if cs[key] > 1:
                    cs[key] = 1
            elif key == 'bufferLevel':
                cs[key] = cs[key] / rlserverConfig.ENOUGH_CLIENT_BUFFER_SIZE

    return state

def main():
    env = VideoEnv(client_num=rlserverConfig.rl_client_num)
    state = env.getState(0, 100)
    # print(f'client 0\'s SSIM: {state}')
    print(f'client 0\'s GMSD: {state["client"][0]["GMSD"]}')
    action = env.action_sample(state)
    print(f'action: {action}')
    next_state, reward = env.step(state, action)
    print(f'reward: {reward}')

    sl = transformStatetoList(state)
    print(f'state_list: {sl}')
    print(f'state_list length: {len(sl)}')

    print(f'MAX EPISODES: {env.MAX_EPISODES}')
    print(f'server throughput: {env.videoState.server_throughput[0]}')

    # MAX_EPISODES = env.MAX_EPISODES
    # for episode in range(MAX_EPISODES):
    #     MAX_TIMESLOT = env.getMaxTimeSlot(episode)
    #     for timeslot in range(MAX_TIMESLOT):
    #         state = env.getState(episode, timeslot)
    #         action = env.action_sample(state)
    #         next_state, reward = env.step(state, action)




if __name__ == "__main__":
    main()