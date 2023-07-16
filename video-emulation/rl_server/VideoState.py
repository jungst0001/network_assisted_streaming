import os
import csv
import math
import copy
import traceback
import numpy as np
from scipy import stats
from ClientStateData import ClientState, ServerState
import estimateGMSD
import rlserverConfig

SERVER_CAPACITY = rlserverConfig.SERVER_CAPACITY #Mbit/s
# MAX_CLIENT_NUM = rlserverConfig.rl_client_num
MAX_CLIENT_NUM = 25

class VideoState:
    def __init__(self, MAX_CLIENT_NUM=MAX_CLIENT_NUM, capacity=SERVER_CAPACITY, 
        use_gmsd_estimation=False, subDir=None, preprocessing=False):
        self._log = "[VideoState]"

        # self._subDir = 'ST-DYN/1000Mbit/'
        if subDir is not None:
            self._subDir = subDir
        else:
            self._subDir = 'demo'

        # self._subDir_buff = ['Bf15', 'Bf30', 'Bf45', 'Bf60']
        self.net_abr_pair = [('FCC', 'Rate'), ('4G', 'Rate'), ('FCC', 'BOLA'), ('4G', 'BOLA')]

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
        # self.server_capacity = capacity * 1024 # Mbit to kbit
        self.server_bandwidth = []
        self.server_throughput = []
        self.server_connected_player = []
        self.server_live_time = []

        # client side state
        self.client_bitrate = []
        # self.client_bufferLevel = []
        self.client_GMSD = []
        # self.client_player_resolution = [] # only insert player height

        self.client_throughput = []

        # client QoE problem
        self.client_latency = []
        self.client_stalling = []
        self.client_chunkSkip = []
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

        for net, abr in self.net_abr_pair:
            for filename in file_list[net][abr]:
                try:
                    state = (ServerState(), []) # serverState, clientStates(list)

                    self._readObservation(state, (net, abr), filename, subDir=self._subDir)

                    if len(state[1]) != self.MAX_CLIENT_NUM:
                        # print(f'{self._log} clientnum error, client num: {len(state[1])}')
                        clientNumErrorList.append((filename[-20:], (net, abr)))
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
                        timeErrorList.append((filename[-20:], (net, abr)))
                        self.isTimeError = False
                        continue

                    print(f'{self._log} Error occurs when processing: {filename[-20:]}')
                    self.errorList.append((filename[-20:], (net, abr)))
                    print(traceback.format_exc())
                    isError =True

        if isError:
            print(f'Exit caused by data error:')
            print(f'file names: {self.errorList}')
            print(f'Total number of files: {len(self.errorList)}')
            exit(0)

        self._printError(clientNumErrorList, timeErrorList)
            # exit(0)

        # self.printStatistics()

        if preprocessing is True:
            print(f'{self._log} Completed data preprocessing')

    def getClientStatistic(self):
        # initiation
        clientStatistic = {}

        for net, abr in self.net_abr_pair:
            if clientStatistic.get(net) is None:
                clientStatistic[net] = {}
                clientStatistic[net][abr] = {}
                continue

            if clientStatistic[net].get(abr) is None:
                clientStatistic[net][abr] = {}
                continue

        for net, abr in self.net_abr_pair:
            clientStatistic[net][abr]['bitrate'] = []
            clientStatistic[net][abr]['GMSD'] = []
            clientStatistic[net][abr]['bitrateSwitch'] = []
            clientStatistic[net][abr]['stalling'] = []
            clientStatistic[net][abr]['totalStallingEvent'] = []
            clientStatistic[net][abr]['chunkSkip'] = []
            clientStatistic[net][abr]['totalChunkSkipEvent'] = []
            clientStatistic[net][abr]['bufferLevel'] = []
            clientStatistic[net][abr]['throughput'] = []
            clientStatistic[net][abr]['latency'] = []
            clientStatistic[net][abr]['fnum'] = 0
        
        for state in self.states:
            css = state[1]
            bf = None
            for cs in css:
                # bf = 'Bf' + f'{cs.MAX_BUFFER_LEVEL}'
                net = cs.net
                abr = cs.abr

                clientStatistic[net][abr]['bitrate'].extend(cs.bitrate)
                clientStatistic[net][abr]['GMSD'].extend(cs.GMSD)
                clientStatistic[net][abr]['bitrateSwitch'].extend(cs.bitrateSwitch)
                clientStatistic[net][abr]['stalling'].extend(cs.stalling)
                clientStatistic[net][abr]['totalStallingEvent'].extend(cs.totalStallingEvent)
                clientStatistic[net][abr]['chunkSkip'].extend(cs.chunkSkip)
                clientStatistic[net][abr]['totalChunkSkipEvent'].extend(cs.totalChunkSkipEvent)
                clientStatistic[net][abr]['latency'].extend(cs.latency)
                clientStatistic[net][abr]['throughput'].extend(cs.throughput)
                # clientStatistic[net][abr]['startupDelay'].append(cs.startupDelay)
            clientStatistic[net][abr]['fnum'] += 1

        return clientStatistic

    def distributeClusterInClientState(self, clientStates):
        cluster = {}
        cluster['FHD'] = []
        cluster['HD'] = []
        cluster['SD'] = []

        for cs in clientStates:
            if cs.attribute == 'FHD':
                cluster['FHD'].append(cs)
            elif cs.attribute == 'HD':
                cluster['HD'].append(cs)
            elif cs.attribute == 'SD':
                cluster['SD'].append(cs)

        return cluster

    def chooseSampleClientState(self, clientStates):
        cluster = self.distributeClusterInClientState(clientStates)

        ipListInCI = {}
        ciList = {}

        for key in cluster.keys():
            css = cluster[key]
            ipListInCI[key] = []
            ciList[key] = {}

            bitrate = []
            GMSD = []
            bitrateSwitch =[]
            stalling = []
            chunkSkip = []
            latency = []

            for cs in css:
                GMSD.extend(cs.GMSD)
                bitrate.extend(cs.bitrate)
                bitrateSwitch.extend(cs.bitrateSwitch)
                stalling.extend(cs.stalling)
                chunkSkip.extend(cs.chunkSkip)
                latency.extend(cs.latency)

            ciList[key]['bitrate'] = self.get_Confidence_Interval(bitrate) # mean, ci_min, ci_max
            ciList[key]['bitrateSwitch'] = self.get_Confidence_Interval(bitrateSwitch)
            ciList[key]['stalling'] = self.get_Confidence_Interval(stalling)
            ciList[key]['chunkSkip'] = self.get_Confidence_Interval(chunkSkip)
            ciList[key]['latency'] = self.get_Confidence_Interval(latency)
            ciList[key]['GMSD'] = self.get_Confidence_Interval(GMSD)

        for key in cluster.keys():
            css = cluster[key]

            for cs in css:
                if self.checkDatainCI(cs.bitrate, ciList[key]['bitrate'][0], ciList[key]['bitrate'][1], ciList[key]['bitrate'][2]) and\
                    self.checkDatainCI(cs.bitrateSwitch, ciList[key]['bitrateSwitch'][0], ciList[key]['bitrateSwitch'][1], ciList[key]['bitrateSwitch'][2]) and\
                    self.checkDatainCI(cs.stalling, ciList[key]['stalling'][0], ciList[key]['stalling'][1], ciList[key]['stalling'][2]) and\
                    self.checkDatainCI(cs.chunkSkip, ciList[key]['chunkSkip'][0], ciList[key]['chunkSkip'][1], ciList[key]['chunkSkip'][2]) and\
                    self.checkDatainCI(cs.latency, ciList[key]['latency'][0], ciList[key]['latency'][1], ciList[key]['latency'][2]) and\
                    self.checkDatainCI(cs.GMSD, ciList[key]['GMSD'][0], ciList[key]['GMSD'][1], ciList[key]['GMSD'][2]):
                    pass
                else:
                    continue

            ipListInCI[key].append(cs.ip)

        return ipListInCI

    def checkDatainCI(self, oneline_data, mean, ci_min, ci_max):
        if type(oneline_data) != list:
            if oneline_data > ci_min and oneline_data < ci_max:
                return True
            else:
                return False
        elif:
            for a_data in oneline_data:
                if oneline_data > ci_min and oneline_data < ci_max:
                    continue
                else:
                    return False

    def get_Confidence_Interval(data, confidence = 0.95):
        data = np.array(data)
        mean = np.mean(data)
        n = len(data)

        stderr = stats.sem(data)

        interval = stderr - stats.t.ppf( (1 + confidence) / 2, n-1)

        return mean, mean-interval, mean+interval

    def printClientStatistic(self, clientStatistic):
        for net, abr in self.net_abr_pair:
            clientStatistic[net][abr]['bitrate'] = np.array(clientStatistic[net][abr]['bitrate'])
            clientStatistic[net][abr]['GMSD'] = np.array(clientStatistic[net][abr]['GMSD'])
            clientStatistic[net][abr]['bitrateSwitch'] = np.array(clientStatistic[net][abr]['bitrateSwitch'])
            clientStatistic[net][abr]['stalling'] = np.array(clientStatistic[net][abr]['stalling'])
            clientStatistic[net][abr]['totalStallingEvent'] = np.array(clientStatistic[net][abr]['totalStallingEvent'])
            clientStatistic[net][abr]['chunkSkip'] = np.array(clientStatistic[net][abr]['chunkSkip'])
            clientStatistic[net][abr]['totalChunkSkipEvent'] = np.array(clientStatistic[net][abr]['totalChunkSkipEvent'])
            clientStatistic[net][abr]['latency'] = np.array(clientStatistic[net][abr]['latency'])
            clientStatistic[net][abr]['throughput'] = np.array(clientStatistic[net][abr]['throughput'])
            # clientStatistic[net][abr]['startupDelay'] = np.array(clientStatistic[net][abr]['startupDelay'])

            clientStatistic[net][abr]['GMSD'] = clientStatistic[net][abr]['GMSD'].astype('float')
            clientStatistic[net][abr]['GMSD'][clientStatistic[net][abr]['GMSD'] == 0.7] = np.nan

            print(f'========{net}-{abr}')
            print(f'avg bitrate: {np.round(np.mean(clientStatistic[net][abr]["bitrate"]), 2)}')
            print(f'avg GMSD: {np.round(np.nanmean(clientStatistic[net][abr]["GMSD"]), 5)}')
            print(f'avg latency: {np.round(np.mean(clientStatistic[net][abr]["latency"]), 2)}')
            print(f'avg stalling: {np.round(np.sum(clientStatistic[net][abr]["stalling"]) / (clientStatistic[net][abr]["fnum"] * self.MAX_CLIENT_NUM), 4)}')
            print(f'total stalling: {np.sum(clientStatistic[net][abr]["stalling"])}')
            print(f'avg chunkSkip: {np.round(np.sum(clientStatistic[net][abr]["chunkSkip"]) / (clientStatistic[net][abr]["fnum"] * self.MAX_CLIENT_NUM), 4)}')
            print(f'total chunkSkip: {np.sum(clientStatistic[net][abr]["chunkSkip"])}')
            print(f'avg bitrateSwitch: {np.round(np.sum(clientStatistic[net][abr]["bitrateSwitch"]) / (clientStatistic[net][abr]["fnum"] * self.MAX_CLIENT_NUM), 4)}')
            print(f'total bitrateSwitch: {np.sum(clientStatistic[net][abr]["bitrateSwitch"])}')
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

            for net, abr in self.net_abr_pair:
                print(f'{net}-{abr} num of files: {len(typeList[net][abr])}')

        if len(timeErrorList) != 0:
            print(f'This files have time outlier:')
            print(f'file names: {[timeError[0] for timeError in timeErrorList]}')
            print(f'Total number of files: {len(timeErrorList)}')
            typeList = self._countType(timeErrorList)

            for net, abr in self.net_abr_pair:
                print(f'{net}-{abr} num of files: {len(typeList[net][abr])}')

    def _countType(self, countList):
        typeList = {}

        for net, abr in self.net_abr_pair:
            if typeList.get(net) is None:
                typeList[net] = {}
                typeList[net][abr] = []
                continue

            if typeList[net].get(abr) is None:
                typeList[net][abr] = []
                continue

        for net, abr in self.net_abr_pair:
            for cl in countList:
                if net == cl[1][0] and abr == cl[1][1]:
                    typeList[net][abr].append(cl[0])

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
        for net, abr in self.net_abr_pair:
            if file_list.get(net) is None:
                file_list[net] = {}
                file_list[net][abr] = []
                continue

            if file_list[net].get(abr) is None:
                file_list[net][abr] = []
                continue

        # print(rootDir)

        num = 0
        # for (root, subdirs, files) in os.walk(rootDir):
        #     for bf in self._subDir_buff:
        #         if bf in root:
        #             file_list[bf].extend([(root + '/' + file) for file in files if file.endswith(".csv")])
        
        # for bf in self._subDir_buff:
        #     num += len(file_list[bf])

        # print(f'Total num of fileList: {num}')

        for (root, subdirs, files) in os.walk(rootDir):
            # print(root, files)
            for net, abr in self.net_abr_pair:
                if net in root and abr in root:
                    file_list[net][abr].extend([(root + '/' + file) for file in files if file.endswith(".csv")])

        for net, abr in self.net_abr_pair:
            num += len(file_list[net][abr])

        print(f'Total num of fileList: {num}')

        return file_list

    # def _setMaxMinFlaginClientState(self, clientStates):
    #     for clientState in clientStates:

    def _searchClientState(self, clientStates, ip):
        for clientState in clientStates:
            if ip == clientState.getIP():
                print(f'{self._log} client IP duplication is occurs')
                return None

        cs = ClientState(ip)
        clientStates.append(cs)

        return cs

    def _readObservation(self, state, net_abr_pair, filename, subDir=None):
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
                self._readClientInfo(state[1], line[1], f, net_abr_pair)
                continue

        f.close()

        # self._setMaxMinFlaginClientState(state[1])

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
            elif line[0] == "Throughput (KB/s)":
                ss.throughput = line[1:]
                # it is not kbps (KBps * 8). so it is divided by 8
                # ss.throughput = [round(float (i) / 8, 3) for i in ss.throughput]
                ss.throughput = [round(float (i), 3) for i in ss.throughput]
                continue
            elif line[0] == "Bandwidth (KB/s)":
                ss.bandwidth = line[1:]
                # it is not kbps (KBps * 8). so it is divided by 8
                # ss.throughput = [round(float (i) / 8, 3) for i in ss.throughput]
                ss.bandwidth = [round(float (i), 3) for i in ss.bandwidth]
                continue
            elif line[0] == "time":
                ss.live_time = line[1:]
                ss.live_time = [float (i) for i in ss.live_time]
                continue

        ss.saveServerState()

    def _readClientInfo(self, clientStates, ip, f, net_abr_pair):
        cs = self._searchClientState(clientStates, ip)
        if cs is None:
            print(f'{self._log} read file has a problem. pass this file')
            self.errorList.append(f.name)
            f.close()

            return

        cs.net = net_abr_pair[0]
        cs.abr = net_abr_pair[1]

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
            elif line[0] == "Attribute":
                cs.attribute = line[1:][0].split('.')[1]
                continue
            elif line[0] == "Subscription Plan":
                cs.plan = line[1:][0].split('.')[1]
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
            elif line[0] == "totalStallingEvent":
                cs.totalStallingEvent = line[1:]
                cs.totalStallingEvent = [int (i) for i in cs.totalStallingEvent]
                continue
            # elif line[0] == "bufferLevel":
            #     cs.bufferLevel = line[1:]
            #     cs.bufferLevel = [float (i) for i in cs.bufferLevel]
            #     continue
            # elif line[0] == "startupDelay":
            #     cs.startupDelay = line[1:][0]
            #     cs.startupDelay = float(cs.startupDelay) / 1000
            #     continue
            elif line[0] == "time":
                cs.time = line[1:]
                cs.time = [float (i) for i in cs.time]
                # for i in range(len(cs.time)-1):
                #     if cs.time[i+1] - cs.time[i] > 15:
                #         self.isTimeError = True
                #         raise Exception('client time error when reading csv file')
                continue
            # elif line[0] == "TX (KBps)":
            #     cs.tx = line[1:]
            #     cs.tx = [float (i) for i in cs.tx]
            #     continue
            # elif line[0] == "RX (KBps)":
            #     cs.rx = line[1:]
            #     cs.rx = [float (i) for i in cs.rx]
            #     continue
            elif line[0] == "QoE":
                cs.QoE = line[1:]
                cs.QoE = [float (i) for i in cs.QoE]
                continue
            elif line[0] == "Latency":
                cs.latency = line[1:]
                cs.latency = [int (i) for i in cs.latency]
                continue
            elif line[0] == "chunkSkip":
                cs.chunkSkip = line[1:]
                cs.chunkSkip = [int (i) for i in cs.chunkSkip]
                continue
            elif line[0] == "totalChunkSkipEvent":
                cs.totalChunkSkipEvent = line[1:]
                cs.totalChunkSkipEvent = [int (i) for i in cs.totalChunkSkipEvent]
                continue
            elif line[0] == "Throughput (KB/s)":
                cs.throughput = line[1:]
                cs.throughput = [round(float (i), 3) for i in cs.throughput]
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

    videoState = VideoState(MAX_CLIENT_NUM=MAX_CLIENT_NUM, preprocessing=False,
            subDir=None)

    cstat = videoState.getClientStatistic()
    videoState.printClientStatistic(cstat)

if __name__ == "__main__":
    main()
