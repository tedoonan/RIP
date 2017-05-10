import socket
import select
from RoutingEntry import RoutingTableRow
from RoutingTable import RoutingTable
import parser
from random import randint
import time
import sys

filename = sys.argv[1]

class RoutingDaemon:

    def __init__(self, routerId, inputPorts, outputPorts):
        self.routerId = routerId
        self.inputPorts = inputPorts
        self.outputPorts = outputPorts
        self.IPAddress = "127.0.0.1"
        
        self.periodicTimer = RoutingDaemon.periodicInterval 
        self.myRoutingTable = RoutingTable(self.routerId)
        self.triggeredTimer = None

        self.mainLoop()


    def bindSockets(self):
        inputSockets = []
        
        for port in self.inputPorts:
            mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mySocket.bind((self.IPAddress, port))
            inputSockets.append(mySocket)

        return inputSockets
    

    def sendRoutingTableToNeighbours(self, routingTableToSend, socket):
        packetBuffer = []
        
        for port in self.outputPorts:
            routingTable = routingTableToSend.copyTable()
            routeToMyself = RoutingTableRow(self.routerId, self.routerId, None, 0, self.routerId)
            routingTable.addRow(routeToMyself)
            routingTable.poisonRowMetrics(port.routerId)
            
            ripPacket = self.createRipPacket(routingTable)
            packetBuffer.append(ripPacket)
            socket.sendto(ripPacket, ("127.0.0.1", port.portNumber))
            
            
    def processReceivedTable(self, receivedRoutingTable):
        receivedFromRouterId = receivedRoutingTable.getRouterId()

        for receivedRoute in receivedRoutingTable.getRows():
            if receivedRoute.destRouterId == self.routerId: #is route to itself
                continue
            if receivedRoute.metric < 0 or receivedRoute.metric > 16:
                continue
            if receivedRoute.destRouterId < 1:
                continue
            
            for port in self.outputPorts:
                if port.routerId == receivedRoutingTable.routerId:
                    costToRouter = port.metric
                    
            receivedRoute.metric = min(receivedRoute.metric + costToRouter, 16)
            
            #checking if route is in our table
            myRoute = self.myRoutingTable.tryGetRow(receivedRoute.destRouterId)
            
            if myRoute:
                if myRoute.nextHopRouterId == receivedFromRouterId:
                    #if existing and received metric both equal infinity, do not reset timers
                    if myRoute.metric != 16 or receivedRoute.metric != 16:
                        myRoute.timeoutTimer = myRoute.timeoutInterval
                        myRoute.garbageTimer = None
                    if myRoute.metric != receivedRoute.metric:
                        self.adoptRoute(myRoute, receivedRoute, receivedFromRouterId)
                else:
                    if receivedRoute.metric < myRoute.metric:
                        self.adoptRoute(myRoute, receivedRoute, receivedFromRouterId)
                        
            else: 
                if receivedRoute.metric < 16: #add route to our routing table
                    newRoute = RoutingTableRow(receivedRoute.destRouterId, receivedFromRouterId, 
                                               self.getPortNumberFromRouterId(receivedFromRouterId),
                                               receivedRoute.metric, receivedFromRouterId)
                    self.myRoutingTable.addRow(newRoute)

                               
    def adoptRoute(self, myRoute, receivedRoute, receivedFromRouterId):
        myRoute.metric = receivedRoute.metric
        myRoute.nextHopRouterId = receivedFromRouterId 
        myRoute.nextHopPortNumber = self.getPortNumberFromRouterId(receivedFromRouterId)
        
        if myRoute.metric == 16: #delete route
            myRoute.timeoutTimer = 0 #So checkTimersAndReact picks it up
            myRoute.routeChanged = True
        else:
            myRoute.timeoutTimer = myRoute.timeoutInterval
            myRoute.garbageTimer = None
            

    def sendTriggeredUpdate(self, socket):
        routeAdded = False
        routingTable = RoutingTable(self.routerId)
        
        for route in self.myRoutingTable.getRows():
            if route.routeChanged:
                routingTable.addRow(route)
                route.routeChanged = False
                routeAdded = True
        
        if routeAdded:
            self.sendRoutingTableToNeighbours(routingTable, socket)

            interval = randint(1, 5)
            self.triggeredTimer = interval
            routeAdded = False


    def createRipPacket(self, routingTable):
        packet = bytearray([0] * 4)
        packet[0] = 2 #response
        packet[1] = 1 #version
        packet[3] = routingTable.routerId
        
        for route in routingTable.getRows():
            packet = packet + self.createBinaryFromRoute(route)

        return bytes(packet)
    

    def createBinaryFromRoute(self, route):
        entry = bytearray([0]*20)
        entry[1] = 2
        entry[7] = route.destRouterId
        entry[19] = route.metric
        
        return bytes(entry)
    

    def getRoutingTableFromPacket(self, packet):
        packet = bytearray(packet)
        receivedRouterId = packet[3]
        if packet[0] != 2 or packet[1] != 1:
            return None
        receivedRoutingTable = RoutingTable(receivedRouterId)
        
        for i in range(4, len(packet), 20): #iterate through routes
            receivedRoute = self.getRouteFromBinary(packet[i:i+20], receivedRouterId)
            if receivedRoute:
                receivedRoutingTable.addRow(receivedRoute)

        return receivedRoutingTable
    

    def getRouteFromBinary(self, binaryRoute, receivedRouterId): #adds portnum  
        binaryRoute = bytearray(binaryRoute)
        if binaryRoute[1] != 2:
            return None
        
        destRouterId = binaryRoute[7]
        metric = binaryRoute[19]
        nextHopPortNumber = self.getPortNumberFromRouterId(receivedRouterId)
        
        return RoutingTableRow(destRouterId, destRouterId, nextHopPortNumber,
                                metric, receivedRouterId)
        
        
    def getPortNumberFromRouterId(self, routerId):
        for port in self.outputPorts:
            if port.routerId == routerId:
                return port.metric
            
        raise Exception("Port not found")
    

    def getSmallestTimer(self):
        smallestTimer = self.periodicTimer
        
        if self.triggeredTimer and self.triggeredTimer < smallestTimer:
            smallestTimer = self.triggeredTimer
            
        for route in self.myRoutingTable.getRows():
            timeoutTimer = route.timeoutTimer
            if timeoutTimer and timeoutTimer < smallestTimer:
                smallestTimer = timeoutTimer
            if route.garbageTimer and route.garbageTimer < smallestTimer:
                smallestTimer = route.garbageTimer
                
        if smallestTimer < 0:
            smallestTimer = 0;
            
        return smallestTimer
    

    def checkTimersAndReact(self, elapsedTime, socket):
        shouldSendTriggered = False
        self.periodicTimer = self.periodicTimer - elapsedTime
        
        if self.periodicTimer < 0:
            self.periodicTimer += self.periodicInterval
            self.sendRoutingTableToNeighbours(self.myRoutingTable, socket)
        
        for route in self.myRoutingTable.getRows():
            if route.timeoutTimer is not None: #timeout timer is active
                route.timeoutTimer -= elapsedTime
                
                if route.timeoutTimer <= 0:
                    route.routeChanged = True
                    route.metric = 16
                    shouldSendTriggered = True
                    route.timeoutTimer = None #disable timeout timer
                    route.garbageTimer = route.garbageInterval #enable garbage timer
                    
            elif route.garbageTimer is not None: #garbage timer is active
                route.garbageTimer -= elapsedTime
                if route.garbageTimer <= 0:
                    self.myRoutingTable.removeRow(route)
                
        if self.triggeredTimer is not None: #if triggered update timer is active
            self.triggeredTimer -= elapsedTime
            if self.triggeredTimer <= 0:
                self.triggeredTimer = None #disable triggeredTimer
                shouldSendTriggered = True

            else:
                shouldSendTriggered = False #triggeredTimer is active so don't send
        if shouldSendTriggered:
            self.sendTriggeredUpdate(socket)
            

    def mainLoop(self):
        self.myRoutingTable.populateFromConfig(self.outputPorts)
        inputSockets = self.bindSockets()
        outputs = []

        self.sendRoutingTableToNeighbours(self.myRoutingTable, inputSockets[0])
    
        beforeTime = time.time()

        while True:
            smallestTimer = self.getSmallestTimer()
            if smallestTimer > 0:
                readable, writable, exceptional = select.select(inputSockets,
                                                            outputs, inputSockets,
                                                            smallestTimer)
            
            if len(readable) > 0:
                for sock in readable:
                    received = sock.recv(1024)
                    receivedRoutingTable = self.getRoutingTableFromPacket(received)
                    if receivedRoutingTable:
                        self.processReceivedTable(receivedRoutingTable)
                        print (self.myRoutingTable.toString())

            elapsedTime = time.time() - beforeTime
            beforeTime = time.time()
            
            self.checkTimersAndReact(elapsedTime, inputSockets[0])
        

def main():
    myParser = parser.Parser()
    myParser.parseConfigFile(filename)
    RoutingTableRow.timeoutInterval = myParser.timeoutVal
    RoutingTableRow.garbageInterval = myParser.garbageVal
    RoutingDaemon.periodicInterval = myParser.periodicVal
        
    myRoutingDaemon = RoutingDaemon(myParser.routerId, myParser.inputPorts,
                                    myParser.outputPorts)


main()



        
    
