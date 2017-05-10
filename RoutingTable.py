from RoutingEntry import RoutingTableRow
import copy

class RoutingTable:

    
    def __init__(self, routerId):
        self.routerId = routerId
        self.Rows = list()

    def getRouterId(self):
        return self.routerId

    def setRows(self, rows):
        self.Rows = rows

    def getRows(self):
        return self.Rows

    def tryGetRow(self, destRouterId):
        for row in self.Rows:
            if row.destRouterId == destRouterId:
                return row
        
        return None #Route is not in table

    def addRow(self, row):
        self.Rows.append(row)

    def removeRow(self, route):
        self.Rows.remove(route)

    def copyTable(self):
        routingTable = RoutingTable(self.routerId)
        routingTable.setRows(copy.deepcopy(self.getRows()))
        return routingTable

    def poisonRowMetrics(self, packetDestId):
        for row in self.Rows:
            if (row.nextHopRouterId == packetDestId):
                row.metric = 16

    def populateFromConfig(self, outputPorts):
        for portInfo in outputPorts:
            row = RoutingTableRow(portInfo.routerId, portInfo.routerId,
                                  portInfo.portNumber, portInfo.metric,
                                  0)
            self.addRow(row)

    def toString(self):
        print ("Router ID: ", self.routerId)
        for row in self.getRows():
            print ("Id:", self.routerId, "dest: ", row.destRouterId, "metric:", row.metric, "changed:", row.routeChanged)
        print("done", self.routerId)
                        
        
    
