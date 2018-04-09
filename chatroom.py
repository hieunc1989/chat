from pika import adapters
import pika
import tornado
import time


class RoomsManager(object):
    def __init__(self, amqp_url, options={}):
        self.amqp_url = amqp_url
        self.rooms = dict()
        self.channel = None
        self.options = options
        self.connection = None
        self.exchange = options['exchange'] if (options.has_key('exchange')) else 'rabbitornado'
        self.tornado_connector = True if((options.has_key('tornado')) and (options['tornado'] == True)) else False
            
        self.connect()
            
    def connect(self):
        parameters = pika.URLParameters(self.amqp_url)
        if(self.tornado_connector):
            self.connection = adapters.TornadoConnection(parameters, on_open_callback=self.on_connected)
        else:
            self.connection = pika.SelectConnection(parameters, self.on_connected, stop_ioloop_on_close=False)

    def on_connected(self, connection):
        # Invoked when the connection is open
        print "connection open ", connection, "\n"
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, new_channel):
        self.channel = new_channel
        print "NEW CHANNEL = ", self.channel
        self.channel.exchange_declare(callback=self.on_exchange_declared, exchange=self.exchange, exchange_type="topic", durable=False, auto_delete=True)
        
    def on_exchange_declared(self, frame):
        print "EXCHANGE DECLARED ", frame
        for i in self.rooms:
            self.rooms[i].channel_opened(self.channel)

    def find_room(self, room_name):
        print "FINDING ROOM FOR ", room_name
        if(not self.rooms.has_key(room_name)):
            print "CREATING ROOM ", room_name
            self.rooms[room_name] = ChatRoom(self.channel, self.exchange, room_name)
        return self.rooms[room_name]

    def get_list(self, prefix=''):
        l = list()
        for i in self.rooms:
            if(i.startswith(prefix)):
                r = self.rooms[i]
                l.append([r.topic, len(r.members)])
        return l

    def start(self):
        if(self.tornado_connector == True):
            tornado.ioloop.IOLoop.instance().start()
        else:
            self.connection.ioloop.start()

    def stop(self):
        if(self.tornado_connector == True):
            tornado.ioloop.IOLoop.instance().start()
        else:
            self.connection.ioloop.stop()


    """
    def add_member(self, member):
        super(TornadoChatRoom, self).add_member(member)
        member.handle_message(None, None, "Hello, welcome to the %s room" % (self.topic))
        member.handle_message(None, None, "There are currently %d clients" % (len(self.members)))
    """

def DEBUG(*args, **kwargs):
    print(args, kwargs)


class ChatRoom(object):
    def __init__(self, channel, exchange, topic):
        print "chatroom init ", channel, " EXCHANGE ", exchange , " topic ", topic
        #self.channel = channel
        self.exchange = exchange
        self.topic = topic
        self.backbuffer = list()
        self.members = list()
        if(channel != None):
            self.channel_opened(channel)
        
    def channel_opened(self, channel):
        self.channel = channel
        self.queue_declare()
        
    def queue_declare(self):
        self.channel.queue_declare(queue=self.topic, durable=False, exclusive=True, auto_delete=True, callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        self.channel.queue_bind(callback=self.on_queue_bound, exchange=self.exchange, queue=self.topic, routing_key=self.topic)

    def on_queue_bound(self, frame):
        self.channel.basic_consume(self.handle_delivery, queue=self.topic)
        while (len(self.backbuffer) > 0):
            msg = self.backbuffer.pop()
            self.send(msg)

    def handle_delivery(self, channel, method, header, body):
        for r in self.members:
            DEBUG("SENDING TO MEMBER ", r, " KEY ", method.routing_key, " BODY ", body)
            r.handle_message(method, header, body)
            
        if(channel != None):
            channel.basic_ack(method.delivery_tag)

        DEBUG("GOT HANDLE DELIVERY ", channel, " METHOD ", method, " HEADER ", header, "\n")
        DEBUG(" BODY ", body)

    def add_member(self, member):
        DEBUG("ADD_MEMBER ", member)
        self.members.append(member)

    def remove_member(self, member):
        DEBUG("REMOVE_MEMBER ", member)
        self.members.remove(member)

    def send(self, message):
        if(self.channel):
            headers = { "Content-Type": "application/json", "X-Server-TS": long(time.time()) }
            self.channel.basic_publish(exchange=self.exchange, routing_key=self.topic, body=message, properties=pika.BasicProperties(headers=headers))
        else:
            DEBUG("CHANNEL NOT OPEN BACK BUFFERING: ", message)
            self.backbuffer.append(message)



        

if __name__ == "__main__":
    class Test(object):
        def handle_message(self, method, header, body):
            print "GOT METHOD ", method, " HEADER ", header, " BODY ", body
            
    try:
        rm = RoomsManager('amqp://guest:guest@localhost:5672/%2F', {"tornado": True})
        # Loop so we can communicate with RabbitMQ
        r = rm.find_room('foobar')
        r.add_member(Test())
        r2 = rm.find_room('barfoo')
        r2.add_member(Test())
        
        r.send("Hello World")
        r2.send("Goodbye World")
        
        rm.start()
        
    except KeyboardInterrupt:
        # Gracefully close the connection
        rm.stop()
