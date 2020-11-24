import statistics
import time

#
# based on theo moving up or down
#
# another iteration would be
# buy when theo > ask
# sell when theo < ask

class PriceListener:
    MAXRANGE = 100

    EDGE = 0.02
    
    MIN_QUANTITY = 0.01

    MIN_SAMPLES = 25

    def __init__(self):
        self.theo_buffer = []
        self.held_price = 0.0
        self.held_quantity = 0.0
        self.price_log = open('price_stat.log', 'w')

    def on_price_update(self, bid, offer):
        theo = self.calc_theo(bid, offer)

        print("Theo = %f" % theo)

        self.on_theo(theo)

    def on_theo(self, theo):
        self.theo_buffer.append(theo)

        if(len(self.theo_buffer) > self.MAXRANGE):
            self.theo_buffer = self.theo_buffer[1:self.MAXRANGE]

        self.check_price(theo)

    def check_price(self, theo):
        if(len(self.theo_buffer) > self.MIN_SAMPLES):
            mean_theo = statistics.mean(self.theo_buffer)
            sdev_theo = statistics.stdev(self.theo_buffer)

            print("mean = %f" % mean_theo)
            print("stdev = %f" % sdev_theo)

            if self.held_quantity > 0.0:
                if theo > self.held_price:
                    delta = (theo - self.held_price)/sdev_theo
                    if delta > self.EDGE:
                        self.price_log.write('SELL, %f, %f, %f, %f\n' % (time.time(), theo, self.held_quantity, delta))
                        self.held_price = 0.0
                        self.held_quantity = 0.0
                    else:
                        print("looking for price >= %f" % (self.held_price+(sdev_theo*self.EDGE)))
                        print("sell delta = %f" % delta)
                else:
                    print('holding at %f' % self.held_price)
            else:
                if theo < mean_theo:
                    delta = (mean_theo - theo)/sdev_theo
                    if delta > self.EDGE:
                        self.price_log.write('BUY, %f, %f, %f, %f\n' % (time.time(), theo, self.MIN_QUANTITY, delta))
                        self.held_price = theo
                        self.held_quantity = self.MIN_QUANTITY
                    else:
                        print("looking for price >= %f" % (theo-(sdev_theo*self.EDGE)))
                        print("buy delta = %f" % delta)
                        

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
        
    
    
