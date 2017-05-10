
class Parser:

    def __init__(self):
        self.usedRouterIds = []
        self.inputPorts = []
        self.outputPorts = [] # contains elements of type outputPortInfo
        self.usedInputPorts = [] # must these be different between all routers or just within routers?
        self.usedPeerPorts = []
        self.routerId = None

        # default vals if timing not specified
        self.periodicVal = 5
        self.timeoutVal = 30
        self.garbageVal = 20

    def parseRouterId(self, line):
        self.routerId = line.split()[1]
        
        # checking if line contains a comment
        lastEntry = self.routerId.split()
        if len(lastEntry) > 1:
            if lastEntry[1].startswith('#'):
                self.routerId = lastEntry[0]
            else:
                raise SyntaxError('Router ID is not an integer.')    

        try:
            self.routerId = int(self.routerId)
        except ValueError:
            print('Router ID is not an integer.')
            raise
        
        if self.routerId in self.usedRouterIds:
            raise ValueError('Router ID has already been used.')            
        
        if self.routerId < 1 or self.routerId > 64000:
            raise ValueError('Router ID must be an integer between 1 and 64000.')
        
        self.usedRouterIds.append(self.routerId)


    def parseInputPorts(self, line):
        line = line[12:] # get everything in string after 'input-ports '
        ports = line.split(', ')
        
        # checking if line contains a comment
        lastEntry = ports[-1].split()
        if len(lastEntry) > 1:
            if lastEntry[1].startswith('#'):
                ports = ports[:-1] + [lastEntry[0]]
            else:
                raise SyntaxError('Input Port number is not an integer.')
        
        for port in ports:
            try:
                port = int(port)
            except ValueError:
                print('Input Port number is not an integer.')
                raise
            
            if port < 1024 or port > 64000:
                raise ValueError('Input Port number must be an integer between 1024 and 64000.')
            
            if port in self.usedInputPorts:
                raise ValueError('Input Port number has already been used.')
            
            self.inputPorts.append(port)
            self.usedInputPorts.append(port)


    def parseOutputs(self, line):
        line = line[8:] # gets everything in string after 'outputs '
        outputs = line.split(', ')
        
        # checking if line contains a comment
        lastEntry = outputs[-1].split()
        if len(lastEntry) > 1:
            if lastEntry[1].startswith('#'):
                outputs = outputs[:-1] + [lastEntry[0]]
            else:
                raise SyntaxError('Each output must consist of 3 integers separated by a hyphen.')
        
        for output in outputs:
            output = output.split('-')
            if len(output) != 3:
                raise ValueError('Each output must have 3 parameters.')
            
            for i in range(3):
                try:
                    output[i] = int(output[i])
                except ValueError:
                    print('Each output must consist of 3 integers separated by a hyphen.')
                    raise
            
            peerPortNum = output[0]
            metric = output[1]
            peerRouterId = output[2]
            
            if peerPortNum < 1024 or peerPortNum > 64000:
                raise ValueError('Peer Port number must be an integer between 1024 and 64000.')
            
            if peerPortNum in self.usedPeerPorts:
                raise ValueError('Peer port number has already been used.')
            
            if peerPortNum in self.usedInputPorts:
                # what if outputs is specified before input ports? do we need to check again in input parser?
                raise ValueError('Peer port number has already been used as an input port.')
            
            if metric < 1 or metric > 15:
                raise ValueError('Metric must be between 1 and 15 inclusive.')
            
            self.usedPeerPorts.append(peerPortNum)
            self.outputPorts.append(OutputPortInfo(peerPortNum, metric, peerRouterId))


    def parsePeriodic(self, line):
        line = line[9:] # get everything in string after 'periodic '
        
        value = line.split()
        # check for comment
        if len(value) > 1:
            if value[1].startswith('#'):
                line = value[0]
            else:
                raise SyntaxError('Periodic timer value must be an integer.')
        
        try:
            self.periodicVal = int(line)
        except ValueError:
            print('Value for periodic timer is not an integer.')
            raise


    def parseTimeout(self, line):
        line = line[8:] # get everything in string after 'timeout '
        
        value = line.split()
        # check for comment
        if len(value) > 1:
            if value[1].startswith('#'):
                line = value[0]
            else:
                raise SyntaxError('Timeout value must be an integer.')
        
        try:
            self.timeoutVal = int(line)
        except ValueError:
            print('Value for timeout is not an integer.')
            raise 
        

    def parseGarbage(self, line):
        line = line[8:] # get everything in string after 'garbage '
        
        value = line.split()
        # check for comment
        if len(value) > 1:
            if value[1].startswith('#'):
                line = value[0]
            else:
                raise SyntaxError('Value for garbage collection timer must be an integer.')
        
        try:
            self.garbageVal = int(line)
        except ValueError:
            print('Value for garbage collection timer is not an integer.')
            raise    


    def parseConfigFile(self, filename):
        file = open(filename, 'r')
        
        routerIdSpecified = False
        InputPortsSpecified = False
        outpusSpecified = False
        
        for line in file:
            if line.startswith('router-id '):
                self.parseRouterId(line)
                self.routerIdSpecified = True
            
            elif line.startswith('input-ports '):
                self.parseInputPorts(line)
                self.InputPortsSpecified = True
            
            elif line.startswith('outputs '):
                self.parseOutputs(line)
                self.outpusSpecified = True
            
            elif line.startswith('periodic '):
                self.parsePeriodic(line)
            
            elif line.startswith('timeout '):
                self.parseTimeout(line)
            
            elif line.startswith('garbage '):
                self.parseGarbage(line)
            
            elif line.startswith('\n') or line.startswith('#'):
                continue
            
            else:
                raise SyntaxError('Configuration File has incorrect syntax.')
        
        if not self.routerIdSpecified:
            raise SyntaxError('Router ID not specified.')
        elif not self.InputPortsSpecified:
            raise SyntaxError('Input ports not specified.')
        elif not self.outpusSpecified:
            raise SyntaxError('Outputs not specified.')

        if (self.timeoutVal / self.periodicVal) != 6:
            raise ValueError('Ratio for timeout value vs. periodic value must be 6.')
        elif (self.garbageVal / self.periodicVal) != 4:
            raise ValueError('Ratio for garbage value vs. periodic value must be 4.')
        

class OutputPortInfo:
    def __init__(self, portNumber, metric, routerId):
        self.portNumber = portNumber
        self.metric = metric
        self.routerId = routerId
