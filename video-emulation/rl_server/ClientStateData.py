import copy
import math

class ClientState:
    def __init__(self, ip):
        self._log = "ClientState"

        self._ip = ip

        self.player_width = 0
        self.player_height = 0
        self.bitrate = None
        self.startupDelay = 0
        self.bitrateSwitch = None
        self.stalling = None
        self.stallingTime = None
        self.bufferLevel = None
        self.time = None

        self.MAX_BUFFER_LEVEL = None
        self.throughput = None
        self.GMSD = None

        self._isSaved = False

    def getIP(self):
        return self._ip
    
    def saveClientState(self):
        self._isSaved = True
        
    # Deprecated
    def resetClientState(self):
        self.player_width = 0
        self.player_height = 0
        self.bitrate = None
        self.startupDelay = 0
        self.GMSD = None
        self.bitrateSwitch = None
        self.stalling = None
        self.stallingTime = None
        self.bufferLevel = None
        self.time = None

        self.throughput = None

        self._isSaved = False

    def _saveTempClientData(self, data, index, time_delta=0):
        data['time'].append(self.time[index] + time_delta)
        data['bitrate'].append(self.bitrate[index])
        data['GMSD'].append(self.GMSD[index])
        data['bitrateSwitch'].append(self.bitrateSwitch[index])
        data['stalling'].append(self.stalling[index])
        data['stallingTime'].append(self.stallingTime[index])
        data['bufferLevel'].append(self.bufferLevel[index])
        data['throughput'].append(self.throughput[index])

    def _saveClientData(self, data):
        self.time = data['time']
        self.bitrate = data['bitrate']
        self.GMSD = data['GMSD']
        self.bitrateSwitch = data['bitrateSwitch']
        self.stalling = data['stalling']
        self.stallingTime = data['stallingTime']
        self.bufferLevel = data['bufferLevel']
        self.throughput = data['throughput']

    def preprocessClientData(self, server_time_slot):
        s_tslot = server_time_slot

        # data initializing
        data = {}
        data['time'] = []
        data['bitrate'] = []
        data['GMSD'] = []
        data['bitrateSwitch'] = []
        data['stalling'] = []
        data['stallingTime'] = []
        data['bufferLevel'] = [] 
        data['throughput'] = []

        rounddown_client_time = [math.trunc(i) for i in self.time]
        # print(f'round time: {rounddown_client_time}')

        st_skip = 0
        st_copy = 0
        st_move = 0

        i = 0
        while i < len(self.time):
            # check current time for duplicate
            duplicated_current_time = rounddown_client_time.count(rounddown_client_time[i])
            # check next index exists
            if i + 1 < len(self.time):
                blank_slot = rounddown_client_time[i+1] - rounddown_client_time[i]
            else:
                blank_slot = -1

            # delete(skip) duplicate index. default blank is 1
            if blank_slot <= 1:
                # if duplicated_current_time == 1:
                #     self._saveTempClientData(data, i)
                # else:
                #     for j in range(duplicated_current_time - 1): 
                #         if i + 1 >= len(self.time):
                #             break

                #         if rounddown_client_time[i+1] != rounddown_client_time[i]:
                #             self._saveTempClientData(data, i)
                #         st_skip += 1
                #         i += 1
                #         # print(i)
                #     continue
                self._saveTempClientData(data, i)

                if duplicated_current_time > 1:
                    for j in range(duplicated_current_time - 1):
                        if i >= len(self.time):
                            break
                        i += 1

            # check black time between current time and next time
            # this case means blank_slot > 1
            else:
                duplicated_next_time = rounddown_client_time.count(rounddown_client_time[i+1])
                copy_current_state_num = blank_slot - duplicated_next_time
                # print(f'rounddown_client_time {rounddown_client_time[i]}')
                # print(f'blank_slot {blank_slot}')

                # this means that the blank are is broad enough to copy next time
                if copy_current_state_num >= 0:
                    # copy current state
                    for j in range(copy_current_state_num + 1):
                        self._saveTempClientData(data, i, j)
                        st_copy += 1
                    st_copy = st_copy - 1

                    # move down next state
                    for j in range(duplicated_next_time - 1):
                        self._saveTempClientData(data, i+j+1, j -(duplicated_next_time-1))
                        st_move += 1

                    i = i + duplicated_next_time - 1
                    # i = i + copy_current_state_num
                # this means that the blank is too narrow to copy next time
                # so, move down only size of blank time from next duplicate time
                else:
                    self._saveTempClientData(data, i)

                    for j in range(blank_slot - 1):
                        self._saveTempClientData(data, i+j+1, j - (blank_slot-1))
                        st_move += 1

                    st_skip = st_skip - copy_current_state_num
                    # i = i + duplicated_next_time - 1
                    i = i + blank_slot

            i += 1

        # statistics for debugging below
        # print(f'time {[math.trunc(i) for i in data["time"]]}')
        # print(f'length time {len(data["time"])}')
        # print(f'required length {math.trunc(data["time"][-1]) - math.trunc(data["time"][0]) + 1}')
        # print(f'length pre-time {len(self.time)}')
        # print(f'st_copy {st_copy}')
        # print(f'st_move {st_move}')
        # print(f'st_skip {st_skip}')

        self._saveClientData(data)

    def zeroPadding(self, prepadding, postpadding, required_length):
        # if this ip is not connected
        if self.time is None:
            self.bitrate = [0 for i in range(required_length)]
            self.GMSD = [0 for i in range(required_length)]
            self.bitrateSwitch = [0 for i in range(required_length)]
            self.stalling = [0 for i in range(required_length)]
            self.stallingTime = [0 for i in range(required_length)]
            self.bufferLevel = [0 for i in range(required_length)]
            self.throughput = [0 for i in range(required_length)]
            
            return

        # print(f'length time {len(self.time)}')
        # print(f'required length {required_length}')

        for i in range(prepadding):
            self.bitrate.insert(0, 0)
            self.GMSD.insert(0, 0)
            self.bitrateSwitch.insert(0, 0)
            self.stalling.insert(0, 0)
            self.stallingTime.insert(0, 0)
            self.bufferLevel.insert(0, 0)
            self.throughput.insert(0, 0)

        postpadding = required_length - len(self.bitrate)

        for i in range(postpadding):
            self.bitrate.insert(len(self.bitrate), 0)
            self.GMSD.insert(len(self.GMSD), 0)
            self.bitrateSwitch.insert(len(self.bitrateSwitch), 0)
            self.stalling.insert(len(self.stalling), 0)
            self.stallingTime.insert(len(self.stallingTime), 0)
            self.bufferLevel.insert(len(self.bufferLevel), 0)
            self.throughput.insert(len(self.throughput), 0)

        prunning_end = len(self.bitrate) - required_length
        if prunning_end > 0:
            for i in range(prunning_end):
                del self.bitrate[-1]
                del self.GMSD[-1]
                del self.bitrateSwitch[-1]
                del self.stalling[-1]
                del self.stallingTime[-1]
                del self.bufferLevel[-1]
                del self.throughput[-1]

class ServerState:
    def __init__(self):
        self.connected_player = None
        self.throughput = None
        self.live_time = None

        self.raw_connected_player = None
        self.raw_throughput = None
        self.raw_live_time = None

        self._isSaved = False

    def saveServerState(self):
        self.raw_connected_player = copy.deepcopy(self.connected_player)
        self.raw_throughput = copy.deepcopy(self.throughput)
        self.raw_live_time = copy.deepcopy(self.live_time)

        self._isSaved = True

    def resetServerState(self):
        self.connected_player = None
        self.throughput = None
        self.live_time = None

        self.raw_connected_player = None
        self.raw_throughput = None
        self.raw_live_time = None

        self._isSaved = False
