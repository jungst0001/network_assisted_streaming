
# use rl parameter
rl_client_num = 50
SERVER_CAPACITY = 300 #Mbit/s
ENOUGH_CLIENT_BUFFER_SIZE = 15 #sec
MAX_BITRATE = 2000

linear_model_dir = 'linear_model/'
linear_model_name = 'linear_model2.ols'

linear_model_old_list = ['linear_model.ols']

subDir_in_DDQN_training = 'ST-DYN/300Mbit/'

# test rl data
subDir_in_DDQN_testing = 'testing_300M_cl50'

# rl model name
model_name = ['dmodel_01_100_50_01', 'dmodel_01_100_50_01', 'dmodel_01_100_50_02', 'dmodel_01_100_50_03']

# use in estimateGMSD only
client_num_in_estimated_gmsd = 25
subDir_in_estimated_gmsd = 'cl25/unlimited/'

# use in RLServer only
rlserver_ip = '192.168.122.1'
rlserver_port = 8889