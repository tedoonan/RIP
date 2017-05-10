class RoutingTableRow:

    def __init__(self, destRouterId, nextHopRouterId, nextHopPortNumber, 
                 metric, learnedFrom):
        self.destRouterId = destRouterId
        self.nextHopRouterId = nextHopRouterId
        self.nextHopPortNumber = nextHopPortNumber
        self.metric = metric
        self.learnedFrom = learnedFrom
        
        self.routeChanged = False
        self.timeoutTimer = RoutingTableRow.timeoutInterval       
        self.garbageTimer = None

    def setMetric(self, newMetric):
        self.metric = newMetric
