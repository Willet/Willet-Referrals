from util.gaesessions import SessionMiddleware
def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)

    # cookie key was generated using os.random(64)
    # as per documentation recommendation
    app = SessionMiddleware(app, 
                            cookie_key="\xef\xcd\xa50\xee3\x06_\x8e\xaa\xa2\xd5G\x98\xa9\x89\xf1\xe5\x18\x8fJ\xa1-\x939\xb2\x1b\x7fe\xf5\xc0\xfc`C\xd2\xc0\xe0vN\x03\x83\xfe`\xa5\x94\xfe\xf0P\xf1p,\xdcc\xael\xf9\xb2V\x83-\xb3\xb0\x16\xc1")
    return app

