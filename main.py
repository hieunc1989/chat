import tornado
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import chatroom
import json
import functools
import base64
import authenticator
import time
import pika

def DEBUG(*args,**kwargs):
    print(args, kwargs)


def basic_auth(f):
    @functools.wraps(f)
    def wrap_f(self, *args, **kwargs):
        auth_header = self.request.headers.get('Authorization', None)
        auth_user = None
        if((auth_header != None) and (auth_header.startswith('Basic'))):
            (user, passwd) = base64.decodestring(auth_header[6:]).split(':', 2)
            auth_user = self.USER = authenticator.authenticate(user, passwd)

        if(auth_user == None):
            self.set_header('WWW-Authenticate', 'Basic realm=rabbitornado')
            self.set_header('Location', '/')
            self.set_status(401)
            self.write('Login needed')
            self.finish()
            return False

        return f(self, *args, **kwargs)

    return wrap_f


class CurrentUser(object):
    def get_current_user(self):
        json_user = self.get_secure_cookie("user")
        try:
            user = json.loads(json_user)
            return user
        except Exception:
            return None

class MainHandler(CurrentUser, tornado.web.RequestHandler):
    def initialize(self, rooms_manager):
        self.rooms_manager = rooms_manager

    def handle_message(self, method, header, message):
        if(self.callback):
            self.write("%s(%s);\n" % (self.callback, json.dumps(message)));
        elif(self.format == 'shell'):
            self.write(message + "\n")
        else:
            self.write(message)
        self.flush()

    @tornado.web.asynchronous
    #@basic_auth
    @tornado.web.authenticated
    def get(self, room_name):
        self.callback = self.get_argument('callback', default=None)
        self.format = self.get_argument('format', default=None)

        DEBUG("Looking for room")
        room = self.rooms_manager.find_room(room_name)
        DEBUG("GOT ROOM ", room)
        DEBUG("ADDING MEMBER")
        room.add_member(self)

    @basic_auth
    def post(self, room_name):
        room = self.rooms_manager.find_room(room_name)
        message = self.get_argument('message')
        room.send(message)


class WebSocketHandler(CurrentUser, tornado.websocket.WebSocketHandler):
    def initialize(self, rooms_manager):
        DEBUG("SETTING UP ROOMS MANAGER ")
        self.rooms_manager = rooms_manager

    def handle_message(self, method, header, message):
        print "WS: GOT MESSAGE METHOD ", method, " HEADER ", header, " MESSAGE ", message
        self.write_message(message)

    #@basic_auth
    @tornado.web.authenticated
    def open(self, room_name):
        self.USER = self.get_current_user()
        DEBUG("WebSocket opened room ", room_name)
        self.room_name = room_name
        self.room = self.rooms_manager.find_room('room.' + self.room_name)
        self.room.add_member(self)
        print "USER IS ", self.USER["name"]
        self.room_privmsg = self.rooms_manager.find_room('user.' + self.USER["name"] + '.' + self.room_name )
        self.room_privmsg.add_member(self)

    def on_message(self, message):
        self.room.send(message)

    def on_close(self):
        DEBUG("WebSocket closed")
        self.room.remove_member(self)


class LoginHandler(CurrentUser, tornado.web.RequestHandler):
    def initialize(self, template_dir):
        self.loader = tornado.template.Loader(template_dir)
        self.login_page = self.loader.load('login.html')
        
    def get(self, *args):
        r = self.get_argument("next", self.get_argument("r", "/"))
        self.write(self.login_page.generate(r=r))
        
    def post(self, *args):
        name = self.get_argument("name")
        password = self.get_argument("password")
        user = {
        	"name": name,
            "password": password,
            "ts": time.time()
        }
        self.set_secure_cookie("user", json.dumps(user))
        redir = self.get_argument("r", "/")
        self.redirect(redir)
        
class PagesHandler(CurrentUser, tornado.web.RequestHandler):
    def initialize(self, template_dir, rooms_manager):
        DEBUG("PagesHandler Loading")
        self.rooms_manager = rooms_manager
        self.loader = tornado.template.Loader(template_dir)
        self.pages = dict()
        for i in ['index.html', 'room.html']:
            DEBUG("Loading Template ", i)
            self.pages[i] = self.loader.load(i)

    #@basic_auth
    @tornado.web.authenticated
    def get(self, *args):
        self.USER = self.get_current_user()
        DEBUG("ARGS IS ", args[0])
        DEBUG("LEN IS ", len(args))
        room=None
        if(args[0] == None):
            page = 'index.html'
        elif(len(args) == 1):
            page = args[0]
        elif(len(args) == 2):
            room = args[0]
            if(args[1] == '.html'):
                page = 'room.html'
            
        if(self.pages[page]):
            host = self.request.headers.get('Host', None)
            self.write(self.pages[page].generate(rooms_manager=self.rooms_manager, room=room, user=self.USER, host=host))



amqp_url = 'amqp://guest:guest@localhost:5672/%2F'
rooms_manager = chatroom.RoomsManager(amqp_url, {"tornado": True})


settings = {
    "cookie_secret": "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
    "login_url": "/login",
}

application = tornado.web.Application([
    (r"/ws/(\w+)", WebSocketHandler, dict(rooms_manager=rooms_manager)),
    (r"/room/(\w+)", MainHandler, dict(rooms_manager=rooms_manager)),
    (r"/room", MainHandler, dict(rooms_manager=rooms_manager)),
    (r"/static/(.+\.(html|css|js))", tornado.web.StaticFileHandler, {"path": "./"}),
    (r"/room/(\w+)(.html)", PagesHandler, dict(template_dir='./', rooms_manager=rooms_manager)),
    (r"/(\w+.html)?", PagesHandler, dict(template_dir='./', rooms_manager=rooms_manager)),
    (r"/login", LoginHandler, dict(template_dir='./')),
], **settings)

if __name__ == "__main__":
    application.listen(8888)
    DEBUG("Listening on port http://localhost:8888/")
    tornado.ioloop.IOLoop.instance().start()
    
