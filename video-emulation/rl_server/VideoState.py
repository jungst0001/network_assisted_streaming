import os
import csv
import math
import copy
import traceback
import numpy as np
from ClientStateData import ClientState, ServerState
import estimateGMSD
import rlserverConfig

SERVER_CAPACITY = rlserverConfig.SERVER_CAPACITY #Mbit/s
MAX_CLIENT_NUM = rlserverConfig.rl_client_num

class VideoState:
    def __init__(self, MAX_CLIENT_NUM=MAX_CLIENT_NUM, capacity=SERVER_CAPACITY, 
        use_gmsd_estimation=False, subDir=None, preprocessing=True):
        self._log = "[VideoState]"

        # self._subDir = 'ST-DYN/1000Mbit/'
        if subDir is not None:
            self._subDir = subDir
        else:
            self._subDir = 'ST-DYN/300Mbit/'

        self._subDir_buff = ['Bf15', 'Bf30', 'Bf45', 'Bf60']

        self.MAX_CLIENT_NUM = MAX_CLIENT_NUM

        self._gmsd_model = None
        self._is_gmsd_model = False

        ## main state for rl
        # use gmsd model
        if use_gmsd_estimation is True:
            try:
                self._gmsd_model = estimateGMSD.loadLinearModel()
                self._is_gmsd_model = True
            except Exception:
                pass

        # server side state
        self.server_capacity = capacity * 1024 # Mbit to kbit
        self.server_throughput = []
        self.server_connected_player = []
        self.server_live_time = []

        # client side state
        self.client_bitrate = []
        self.client_bufferLevel = []
        self.client_GMSD = []
        # self.client_player_resolution = [] # only insert player height

        self.client_throughput = []

        # client QoE problem
        self.client_stalling = []
        self.client_bitrate_switching = []
        ################################

        # preprocessing Data
        self.states = []
        self.states_raw = []

        file_list = self._checkDataStorage(self._subDir)

        if preprocessing is True:
            print(f'{self._log} Start data preprocessing')
        else:
            print(f'{self._log} Data no preprocessing')

        isError = False
        self.errorList = []
        timeErrorList = []
        clientNumErrorList = []
        self.isTimeError = False

        for bf in self._subDir_buff:
            for filename in file_list[bf]:
                try:
                    state = (ServerState(), []) # serverState, clientStates(list)

                    self._readObservation(state, int(bf[-2:]), filename, subDir=self._subDir)

                    if len(state[1]) != self.MAX_CLIENT_NUM:
                        # print(f'{self._log} clientnum error, client num: {len(state[1])}')
                        clientNumErrorList.append((filename[-22:], bf))
                        del self.states[-1]
                        del self.states_raw[-1]

                        continue

                    if preprocessing is True:
                        first_index, last_index = self._findSlicingIndex(state)
                        # Server data preprocessing
                        self._preprocessServerData(state[0], first_index, last_index)
                        self._preprocessClientsData(state, first_index, last_index)
                        # Clients data preprocessing
                        # self._preprocesseClientsData()
                        self._insertStateData(state, first_index, last_index)

                except Exception as err:
                    if self.isTimeError:
                        timeErrorList.append((filename[-22:], bf))
                        self.isTimeError = False
                        continue

                    print(f'{self._log} Error occurs when processing: {filename[-22:]}')
                    self.errorList.append((filename[-22:], bf))
                    print(traceback.format_exc())
                    isError =True

        if isError:
            print(f'Exit caused by data error:')
            print(f'file names: {self.errorList}')
            print(f'Total number of files: {len(self.errorList)}')
            exit(0)

        self._printError(clientNumErrorList, timeErrorList)
            # exit(0)

        self.printStatistics()

        if preprocessing is True:
            print(f'{self._log} Completed data preprocessing')

    def getClientStatistic(self):
        # initiation
        clientStatistic = {}
        for bf in self._subDir_buff:
            clientStatistic[bf] = {}
            clientStatistic[bf]['bitrate'] = []
            clientStatistic[bf]['GMSD'] = []
            clientStatistic[bf]['bitrateSwitch'] = []
            clientStatistic[bf]['stalling'] = []
            clientStatistic[bf]['stallingTime'] = []
            clientStatistic[bf]['bufferLevel'] = []
            clientStatistic[bf]['throughput'] = []
            clientStatistic[bf]['startupDelay'] = []
            clientStatistic[bf]['fnum'] = 0
        
        for state in self.states:
            css = state[1]
            bf = None
            for cs in css:
                bf = 'Bf' + f'{cs.MAX_BUFFER_LEVEL}'
                clientStatistic[bf]['bitrate'].extend(cs.bitrate)
                clientStatistic[bf]['GMSD'].extend(cs.GMSD)
                clientStatistic[bf]['bitrateSwitch'].extend(cs.bitrateSwitch)
                clientStatistic[bf]['stalling'].extend(cs.stalling)
                clientStatistic[bf]['stallingTime'].extend(cs.stallingTime)
                clientStatistic[bf]['bufferLevel'].extend(cs.bufferLevel)
                clientStatistic[bf]['throughput'].extend(cs.throughput)
                clientStatistic[bf]['startupDelay'].append(cs.startupDelay)
            clientStatistic[bf]['fnum'] += 1

        return clientStatistic

    def printClientStatistic(self, clientStatistic):
        for bf in self._subDir_buff:
            clientStatistic[bf]['bitrate'] = np.array(clientStatistic[bf]['bitrate'])
            clientStatistic[bf]['GMSD'] = np.array(clientStatistic[bf]['GMSD'])
            clientStatistic[bf]['bitrateSwitch'] = np.array(clientStatistic[bf]['bitrateSwitch'])
            clientStatistic[bf]['stalling'] = np.array(clientStatistic[bf]['stalling'])
            clientStatistic[bf]['stallingTime'] = np.array(clientStatistic[bf]['stallingTime'])
            clientStatistic[bf]['bufferLevel'] = np.array(clientStatistic[bf]['bufferLevel'])
            clientStatistic[bf]['throughput'] = np.array(clientStatistic[bf]['throughput'])
            clientStatistic[bf]['startupDelay'] = np.array(clientStatistic[bf]['startupDelay'])

            clientStatistic[bf]['GMSD'] = clientStatistic[bf]['GMSD'].astype('float')
            clientStatistic[bf]['GMSD'][clientStatistic[bf]['GMSD'] == 0.7] = np.nan

            print(f'========bf: {bf}')
            print(f'avg bitrate: {np.round(np.mean(clientStatistic[bf]["bitrate"]), 2)}')
            print(f'avg GMSD: {np.round(np.nanmean(clientStatistic[bf]["GMSD"]), 5)}')
            print(f'avg bufferLevel: {np.round(np.mean(clientStatistic[bf]["bufferLevel"]), 2)}')
            print(f'avg stalling: {np.round(np.sum(clientStatistic[bf]["stalling"]) / clientStatistic[bf]["fnum"], 4)}')
            print(f'total stalling: {np.sum(clientStatistic[bf]["stalling"])}')
            print(f'avg bitrateSwitch: {np.round(np.sum(clientStatistic[bf]["bitrateSwitch"]) / clientStatistic[bf]["fnum"], 4)}')
            print(f'total bitrateSwitch: {np.sum(clientStatistic[bf]["bitrateSwitch"])}')
            print(f'========')

    def getEstimatedGMSD(self, variable):
        var = {}
        var['bitrate'] = variable

        if self._is_gmsd_model is True:
            pred = estimateGMSD.predictLinearModel(self._gmsd_model, var)
        else:
            print(f'{self._log} No estimated GMSD model')
            pred = 0

        return pred

    def printStatistics(self, isPrint=True):
        bf15 = bf30 = bf45 = bf60 = 0

        for state in self.states:
            css = state[1]
            if css[0].MAX_BUFFER_LEVEL == 15:
                bf15 += 1
            elif css[0].MAX_BUFFER_LEVEL == 30:
                bf30 += 1
            elif css[0].MAX_BUFFER_LEVEL == 45:
                bf45 += 1
            elif css[0].MAX_BUFFER_LEVEL == 60:
                bf60 += 1

        if isPrint:
            print(f'Total recorded file num: {len(self.states)}')
            print(f'bf15 num of files: {bf15}')
            print(f'bf30 num of files: {bf30}')
            print(f'bf45 num of files: {bf45}')
            print(f'bf60 num of files: {bf60}')

        return (bf15, bf30, bf45, bf60)

    def _printError(self, clientNumErrorList, timeErrorList):
        if len(clientNumErrorList) != 0:
            print(f'This files have less client num:')
            print(f'file names: {[clientNum[0] for clientNum in clientNumErrorList]}')
            print(f'Total number of files: {len(clientNumErrorList)}')
            typeList = self._countType(clientNumErrorList)
            print(f'bf15 num of files: {len(typeList["Bf15"])}')
            print(f'bf30 num of files: {len(typeList["Bf30"])}')
            print(f'bf45 num of files: {len(typeList["Bf45"])}')
            print(f'bf60 num of files: {len(typeList["Bf60"])}')

        if len(timeErrorList) != 0:
            print(f'This files have time outlier:')
            print(f'file names: {[timeError[0] for timeError in timeErrorList]}')
            print(f'Total number of files: {len(timeErrorList)}')
            typeList = self._countType(timeErrorList)
            print(f'bf15 num of files: {len(typeList["Bf15"])}')
            print(f'bf30 num of files: {len(typeList["Bf30"])}')
            print(f'bf45 num of files: {len(typeList["Bf45"])}')
            print(f'bf60 num of files: {len(typeList["Bf60"])}')

    def _countType(self, countList):
        typeList = {}

        for df in self._subDir_buff:
            typeList[df] = []

        for df in self._subDir_buff:
            for cl in countList:
                if cl[1] in df:
                    typeList[df].append(cl[0])

        return typeList

    def _preprocessServerData(self, serverState, first_index, last_index):
        fi = first_index
        li = last_index
        data_index_len = li - fi

        ss = serverState

        # list 0 is live_time
        # list 1 is connected player
        # list 2 is throughput
        processedServerData = [ [] for i in range(3) ]
        cutted_live_time = ss.live_time[fi:li]
        cutted_connected_player = ss.connected_player[fi:li]
        cutted_throughput = ss.throughput[fi:li]

        rounddown_live_time = [math.trunc(i) for i in cutted_live_time]
        # print(rounddown_live_time)

        i = 0
        while i < len(cutted_live_time):
            # check current time for duplicate
            duplicated_current_time = rounddown_live_time.count(rounddown_live_time[i])
            # check next index exists and blank time
            if i + 1 < len(cutted_live_time):
                blank_slot = rounddown_live_time[i+1] - rounddown_live_time[i]
            else:
                blank_slot = -1

            # delete(skip) duplicate index. default blank is 1
            if blank_slot <= 1:
                # if duplicated_current_time > 1:
                #     # print(f'i {i}')
                #     print(f'blank_slot {blank_slot}')
                # print(f'rounddown_live_time {rounddown_live_time[i]}')
                processedServerData[0].append(cutted_live_time[i])
                processedServerData[1].append(cutted_connected_player[i])
                processedServerData[2].append(cutted_throughput[i])
                
                if duplicated_current_time > 1:
                    # print(f'i {i}')
                    for j in range(duplicated_current_time - 1):
                        if i >= len(cutted_live_time):
                            break
                        i += 1

            # check black time between current time and next time
            # this case means blank_slot > 1
            else:
                duplicated_next_time = rounddown_live_time.count(rounddown_live_time[i+1])
                copy_current_state_num = blank_slot - duplicated_next_time
                # print(f'rounddown_live_time {rounddown_live_time[i]}')
                # print(f'blank_slot {blank_slot}')

                # this means that the blank are is broad enough to copy next time
                if copy_current_state_num >= 0:
                    # copy current state
                    for j in range(copy_current_state_num + 1):
                        processedServerData[0].append(cutted_live_time[i])
                        processedServerData[1].append(cutted_connected_player[i])
                        processedServerData[2].append(cutted_throughput[i])

                    # pull down next state
                    # always duplicated_next_time is over 1
                    for j in range(duplicated_next_time - 1):
                        processedServerData[0].append(cutted_live_time[i+j+1])
                        processedServerData[1].append(cutted_connected_player[i+j+1])
                        processedServerData[2].append(cutted_throughput[i+j+1])

                    i = i + duplicated_next_time - 1
                # this means that the blank is too narrow to copy next time
                # so, pull down only size of blank time from next duplicate time
                else:
                    processedServerData[0].append(cutted_live_time[i])
                    processedServerData[1].append(cutted_connected_player[i])
                    processedServerData[2].append(cutted_throughput[i])

                    for j in range(blank_slot - 1):
                        processedServerData[0].append(cutted_live_time[i+j+1])
                        processedServerData[1].append(cutted_connected_player[i+j+1])
                        processedServerData[2].append(cutted_throughput[i+j+1])

                    i = i + blank_slot

            i += 1

        ss.live_time = processedServerData[0]
        ss.connected_player = processedServerData[1]
        ss.throughput = processedServerData[2]

        # print('##### Server Data  #####')
        # print(f'cutted_live_time {cutted_live_time}')
        # print()
        # print(f'live_time {ss.live_time}')
        # print()
        # print(f'live_time {len(ss.live_time)}')
        # print(f'cutted_live_time {len(cutted_live_time)}')
        # print()

    def _insertStateData(self, state, fi, li):
        ss = state[0]
        css = state[1]

        # insert server data in the main state
        self.server_throughput.append(ss.throughput)
        self.server_connected_player.append(ss.connected_player)
        self.server_live_time.append(ss.live_time)

        tmp_bitrate = []
        tmp_bufferLevel = []
        tmp_GMSD = []
        tmp_throughput = []
        tmp_stalling = []
        tmp_bitrate_switching = []

        ## order sorting ip asending order
        for i in range(self.MAX_CLIENT_NUM):
            for cs in css:
                post_ip = cs.getIP().split('.')[-1]
                if i == int(post_ip) - 1:
                    # insert client data in main state
                    tmp_bitrate.append(cs.bitrate)
                    tmp_bufferLevel.append(cs.bufferLevel)
                    tmp_GMSD.append(cs.GMSD)
                    # self.client_player_resolution.append(cs.player_height for cs in css)

                    tmp_throughput.append(cs.throughput)

                    tmp_stalling.append(cs.stalling)
                    tmp_bitrate_switching.append(cs.bitrateSwitch)

                    break

        self.client_bitrate.append(tmp_bitrate)
        self.client_bufferLevel.append(tmp_bufferLevel)
        self.client_GMSD.append(tmp_GMSD)
        # self.client_player_resolution.append(cs.player_height for cs in css)

        self.client_throughput.append(tmp_throughput)

        self.client_stalling.append(tmp_stalling)
        self.client_bitrate_switching.append(tmp_bitrate_switching)

        # tmp = [cs.bitrate for cs in css]
        # print(len(tmp), len(self.client_bitrate))
        # print(tmp[0])
        # print(self.client_bitrate[0])
        # print(len(tmp[0]), len(self.client_bitrate[0]))
        # exit()

        ######
        # insert client data in main state
        # self.client_bitrate.append([cs.bitrate for cs in css])
        # self.client_bufferLevel.append([cs.bufferLevel for cs in css])
        # self.client_GMSD.append([cs.GMSD for cs in css])
        # # self.client_player_resolution.append([cs.player_height for cs in css])

        # self.client_throughput.append([cs.throughput for cs in css])

        # self.client_stalling.append([cs.stalling for cs in css])
        # self.client_bitrate_switching.append([cs.bitrateSwitch for cs in css])
        ######

    def _findSlicingIndex(self, state):
        ss = state[0]
        css = state[1]

        # based on the live time
        first_index = 0
        last_index = len(ss.live_time)

        client_time_list = []
        for cs in css:
            client_time_list.append(cs.time)
        
        ctl_min_list = []
        ctl_max_list = []
        for i in range(len(css)):
            ctl_min_list.append(last_index if client_time_list[i] is None else client_time_list[i][0] - css[i].startupDelay)
            ctl_max_list.append(first_index if client_time_list[i] is None else client_time_list[i][-1])

        for i in range(len(ss.live_time)):
            if ss.live_time[i] > min(ctl_min_list):
                first_index = i
                break

        for i in reversed(range(len(ss.live_time))):
            if ss.live_time[i] < max(ctl_max_list):
                last_index = i + 1
                break

        # print(f'first index: {first_index}')
        # print(f'last index: {last_index}')

        return first_index, last_index

    def _preprocessClientsData(self, state, fi, li):
        # find positions of matching time with first_index (fi) and last_index (li)
        # zero padding in the blank parts
        ss = state[0]
        css = state[1]

        # zero padding client data list
        for cs in css:
            client_head = 0
            client_tail = len(ss.live_time)
            prepadding = 0
            postpadding = len(ss.live_time)

            # print(f'index number: {len(ss.live_time)}')
            
            if cs.time is not None:
                for i in range(len(ss.live_time)):
                    if ss.live_time[i] > cs.time[0] - cs.startupDelay:
                        # print(f'ss.live_time: {ss.live_time[i]}')
                        # print(f'cs.time: {cs.time[0]}')
                        # print(f'cs.startupDelay: {cs.startupDelay}')
                        client_head = i
                        break
                # print(f'client_head: {client_head}')
                prepadding = client_head
                if prepadding < 0:
                    prepadding = 0

                for i in reversed(range(len(ss.live_time))):
                    if ss.live_time[i] < cs.time[-1]:
                        # print(f'ss.live_time: {ss.live_time[i]}')
                        # print(f'cs.time: {cs.time[-1]}')
                        client_tail = i + 1
                        break
                # print(f'client_tail: {client_tail}')
                postpadding = len(ss.live_time) - client_tail

            # print(f'client\' time slot number: {len(cs.time)}')
            # print(f'prepadding: {prepadding}, postpadding: {postpadding}')
            # print()

            required_list_len = len(ss.live_time)

            cs.preprocessClientData(ss.live_time)
            cs.zeroPadding(prepadding, postpadding, required_list_len)

    def _checkDataStorage(self, subDir=None):
        if subDir is None:
            # rootDir = os.listdir('DataStorage/')
            rootDir = ('./DataStorage/')
        else:
            # rootDir = os.listdir('DataStorage/' + subDir)
            rootDir = ('./DataStorage/' + subDir)

        file_list = {}
        for bf in self._subDir_buff:
            file_list[bf] = []

        # print(rootDir)

        num = 0
        for (root, subdirs, files) in os.walk(rootDir):
            for bf in self._subDir_buff:
                if bf in root:
                    file_list[bf].extend([(root + '/' + file) for file in files if file.endswith(".csv")])
        
        for bf in self._subDir_buff:
            num += len(file_list[bf])

        print(f'Total num of fileList: {num}')

        return file_list

    def _searchClientState(self, clientStates, ip):
        for clientState in clientStates:
            if ip == clientState.getIP():
                print(f'{self._log} client IP duplication is occurs')
                return None

        cs = ClientState(ip)
        clientStates.append(cs)

        return cs

    def _readObservation(self, state, max_buffer_level, filename, subDir=None):
        # if subDir is None:
        #     f = open('DataStorage/' + filename, 'r')
        # else:
        #     f = open('DataStorage/' + subDir + filename, 'r')
        f = open(filename, 'r')

        while True:
            line = f.readline()
            if not line: break
            line = line.split('\n')[0].split(',')

            if line[0] == "Server Info":
                self._readServerInfo(state[0], f)
                continue
            elif line[0] == "IP":
                self._readClientInfo(state[1], line[1], f, max_buffer_level)
                continue

        f.close()

        self.states.append(state)

        states_raw = copy.deepcopy(state)
        self.states_raw.append(states_raw)

    def _readServerInfo(self, serverState, f):
        ss = serverState

        while True:
            line = f.readline().split('\n')[0]
            if len(line) == 0: break

            line = line.split(',')

            if line[0] == "Player Connected":
                ss.connected_player = line[1:]
                ss.connected_player = [int (i) for i in ss.connected_player]
                continue
            elif line[0] == "TX + RX (Kbps)": # consider TX + RX
                ss.throughput = line[1:]
                # it is not kbps (KBps * 8). so it is divided by 8
                # ss.throughput = [round(float (i) / 8, 3) for i in ss.throughput]
                ss.throughput = [round(float (i), 3) for i in ss.throughput]
                continue
            elif line[0] == "time":
                ss.live_time = line[1:]
                ss.live_time = [float (i) for i in ss.live_time]
                continue

        ss.saveServerState()

    def _readClientInfo(self, clientStates, ip, f, max_buffer_level):
        cs = self._searchClientState(clientStates, ip)
        if cs is None:
            print(f'{self._log} read file has a problem. pass this file')
            self.errorList.append(f.name)
            f.close()

            return

        cs.MAX_BUFFER_LEVEL = max_buffer_level

        while True:
            line = f.readline().split('\n')[0]
            if len(line) == 0: break

            line = line.split(',')

            if line[0] == "player width":
                cs.player_width = line[1:][0]
                cs.player_width = int(cs.player_width)
                continue
            elif line[0] == "player height":
                cs.player_height = line[1:][0]
                cs.player_height = int(cs.player_height)
                continue
            elif line[0] == "bitrate":
                cs.bitrate = line[1:]
                cs.bitrate = [float (i) for i in cs.bitrate]
                continue
            elif line[0] == "GMSD":
                cs.GMSD = line[1:]
                cs.GMSD = [float (i) for i in cs.GMSD]
                if self._is_gmsd_model is True:
                    tmp = []
                    for i in range(len(cs.GMSD)):
                        if cs.GMSD[i] < 0.7:
                            tmp.append(self.getEstimatedGMSD(cs.bitrate[i]))
                        else:
                            tmp.append(cs.GMSD[i])

                    cs.GMSD = tmp
                else:
                    cs.GMSD = [i if i > 0.7 else 0.7 for i in cs.GMSD]
                continue
            elif line[0] == "bitrateSwitch":
                cs.bitrateSwitch = line[1:]
                cs.bitrateSwitch = [int (i) for i in cs.bitrateSwitch]
                continue
            elif line[0] == "stalling":
                cs.stalling = line[1:]
                cs.stalling = [int (i) for i in cs.stalling]
                continue
            elif line[0] == "stallingTime (sec)":
                cs.stallingTime = line[1:]
                cs.stallingTime = [int (i) for i in cs.stallingTime]
                continue
            elif line[0] == "bufferLevel":
                cs.bufferLevel = line[1:]
                cs.bufferLevel = [float (i) for i in cs.bufferLevel]
                continue
            elif line[0] == "startupDelay":
                cs.startupDelay = line[1:][0]
                cs.startupDelay = float(cs.startupDelay) / 1000
                continue
            elif line[0] == "time":
                cs.time = line[1:]
                cs.time = [float (i) for i in cs.time]
                for i in range(len(cs.time)-1):
                    if cs.time[i+1] - cs.time[i] > 15:
                        self.isTimeError = True
                        raise Exception('client time error when reading csv file')
                continue
            # elif line[0] == "TX (KBps)":
            #     cs.tx = line[1:]
            #     cs.tx = [float (i) for i in cs.tx]
            #     continue
            # elif line[0] == "RX (KBps)":
            #     cs.rx = line[1:]
            #     cs.rx = [float (i) for i in cs.rx]
            #     continue
            elif line[0] == "Throughput (Kbps)":
                cs.throughput = line[1:]
                cs.throughput = [int (i) for i in cs.throughput]
                continue


        cs.saveClientState()

def main():
    # videoState = VideoState()
    print("######### MAIN ##########")
    # videoState.printStatistics()
    
    # print(len(videoState.server_connected_player[0]))
    # print(len(videoState.client_bitrate[0][0]))
    # print(len(videoState.client_SSIM[0][0]))
    # print(len(videoState.client_bitrate[0][1]))
    # print(len(videoState.client_SSIM[0][1]))
    # print(len(videoState.client_bitrate[0][2]))
    # print(len(videoState.client_SSIM[0][2]))

    # # This code is for verifying preprocessing data
    # for i in range(len(videoState.server_throughput)):
    #     slen = len(videoState.server_connected_player[i])
    #     clen = len(videoState.client_bitrate[i][0])

    #     # print(len(videoState.server_connected_player[i]))
    #     # print(len(videoState.client_bitrate[i][0]))

    #     # print(len(videoState.client_throughput[0]))

    #     if slen != clen:
    #         print(f'False case when running index {i}')

    # print(videoState.client_bitrate[0][0])


    # videoState = VideoState(MAX_CLIENT_NUM=rlserverConfig.rl_client_num, preprocessing=False,
    #         subDir=rlserverConfig.subDir_in_DDQN_training)

    # cstat = videoState.getClientStatistic()
    # videoState.printClientStatistic(cstat)

    videoState = VideoState(MAX_CLIENT_NUM=rlserverConfig.rl_client_num, preprocessing=False,
            subDir=rlserverConfig.subDir_in_DDQN_testing)

    cstat = videoState.getClientStatistic()
    videoState.printClientStatistic(cstat)

if __name__ == "__main__":
    main()
