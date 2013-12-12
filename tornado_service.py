
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop

## Tornado application, so Angular can call the services

class BaseHandler(RequestHandler):
    # This is so I can talk to myself from http://127.0.0.1:80 and back,
    # While using Auglar and nginx
    def options(self, *args):
        pass
    
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept")


class NewUploadsHandler(BaseHandler):
    def get(self):
        category = self.get_argument("category", None)
        app = Youtube(storage_file = "../oauth2.json", client_secrets_file = "../desktop_app.json")
        new_uploads = app.get_uploads_from_category(category = category)
        self.finish({"new_uploads": new_uploads})

class CategoriesHandler(BaseHandler):
    def get(self):
        app = Youtube(storage_file = "../oauth2.json", client_secrets_file = "../desktop_app.json")
        self.finish(app.get_categories())

class SubscriptionsHandler(BaseHandler):
    def get(self):
        app = Youtube(storage_file = "../oauth2.json", client_secrets_file = "../desktop_app.json")
        self.finish(app.get_subscriptions())

# Where to go to call what classes
application = Application([
    (r"/new_uploads", NewUploadsHandler),
    (r"/categories", CategoriesHandler),
    (r"/subscriptions", SubscriptionsHandler)
])

if __name__ == "__main__":
    application.listen(8080)
    IOLoop.instance().start()