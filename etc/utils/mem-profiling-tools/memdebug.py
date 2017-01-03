# memdebug.py

from __future__ import absolute_import
import cherrypy
import dowser

def start(port):
    cherrypy.tree.mount(dowser.Root())
    cherrypy.config.update({
        'environment': 'embedded',
        'server.socket_port': port
    })
    #cherrypy.quickstart()
    cherrypy.engine.start()
