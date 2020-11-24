import statistics
import time

#
# based on theo moving up or down
#
# another iteration would be
# buy when theo > ask
# sell when theo < ask

class BuyTheo:
    EDGE = 2.00
    
    MIN_QUANTITY = 0.01

    def __init__(self):
        self.held_price = 0.0
        self.held_quantity = 0.0
        self.price_log = open('price_theo.log', 'w')

    def on_price_update(self, bid, offer):
        theo = self.calc_theo(bid, offer)

        print("Theo = %f" % theo)

        self.on_theo(theo, bid, offer)

    def on_theo(self, theo, bid, offer):
        best_bid = None
        best_offer = None
        for level in offer:
            best_offer = level
        for level in bid:
            if best_bid is None:
                best_bid = level

        if self.held_quantity > 0:
            if best_bid is not None and float(best_bid) > (self.held_price + self.EDGE):
                self.price_log.write('SELL, %f, %f, %f\n' % (time.time(), best_bid, self.held_quantity))
                self.held_price = 0.0
                self.held_quantity = 0.0
        else:
            if best_offer is not None and float(best_offer) < theo:
                self.price_log.write('BUY, %f, %f, %f\n' % (time.time(), best_offer, self.MIN_QUANTITY))
                self.held_price = float(best_offer)
                self.held_quantity = float(self.MIN_QUANTITY)
                        
        self.price_log.flush()
        
        
    def calc_theo(self, bid, offer):

        weighted_price = 0.0
        total_volume = 0.0

        for level in bid:
            weighted_price += float(level[0])*float(level[1])
            total_volume += float(level[1])
        
        for level in offer:
            weighted_price += float(level[0])*float(level[1])
            total_volume += float(level[1])

        vwap = 0.0
        if total_volume > 0.0:
            vwap = weighted_price / total_volume

        return vwap
        
    
    
