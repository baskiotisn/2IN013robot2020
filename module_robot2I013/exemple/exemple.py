from robot2I013 import Robot2I013
import time
import numpy as np
import io
import socket
import struct
from PIL import Image
import threading

class TestControler(object):
    def __init__(self,fps=10.):
        """ Initialise le controleur et un robot """
        self.robot = Robot2I013()
        self.cpt = 0
        self.fps = fps
    def set_led(self,col):
        """ Allume les leds du robot au triplet col=(r,g,b) """
        self.robot.set_led(self.robot.LED_LEFT_EYE+self.robot.LED_RIGHT_EYE,*col)
    def set_speed(self,lspeed,rspeed):
        """ Fait tourner les moteurs a la vitesse lspeed pour le moteur gauche, rspeed pour le moteur droit """
        self.robot.set_motor_dps(self.robot.MOTOR_LEFT,lspeed)
        self.robot.set_motor_dps(self.robot.MOTOR_RIGHT,rspeed)
    def forward(self,speed):
        """ Avant le robot a la vitesse speed """
        self.robot.set_motor_dps(self.robot.MOTOR_LEFT+self.robot.MOTOR_RIGHT,speed)

    def update(self):
        """ Exemple de fonction update : 
            Pour 50 pas fait avancer le robot, puis le tourne pour 20 pas puis s'arrete.
            Affiche la distance et enregistre une image tous les 10 pas, tourne la tete a gauche et a droite. 
        """
        self.cpt+=1
        if (self.cpt % 10)==0:
            print("Distance : ", self.robot.get_distance()," Position des roues : ", self.robot.get_motor_position())
            #self.robot.get_image().save("/tmp/Img_"+str(self.cpt)+".jpg")
            if (self.cpt % 20) == 0:
                self.robot.servo_rotate(30)
            else:
                self.robot.servo_rotate(120)

        if self.cpt<50:
            self.set_led((0,255,0))
            self.forward(100)
            return
        if self.cpt<70:
            self.set_speed(0,100)
            return
        self.set_led((255,0,0))
        self.set_speed(0,0)
    def stop(self):
        return self.cpt>80

    def run(self,verbose=True):
        """ 
            Boucle principale du robot. Elle appelle controler.update() fps fois par seconde 
            et s'arrete quand controler.stop() rend vrai.

            :verbose: booleen pour afficher les messages de debuggages
        """
        if verbose:
            print("Starting ... (with %f FPS  -- %f sleep)" % (self.fps,1./self.fps))
        ts=time.time()
        tstart = ts
        cpt = 0
        try:
            while not self.stop():
                ts = time.time()
                self.update()
                time.sleep(1./self.fps)
                if verbose:
                    print("Loop %d, duree : %fs " % (cpt,time.time()-ts))
                cpt+=1
        except Exception as e:
            print("Erreur : ",e)
        self.robot.stop()
        if verbose:
            print("Stoping ... total duration : %f (%f /loop)" % (time.time()-tstart,(time.time()-tstart)/cpt))


class StreamThread(threading.Thread):
    def __init__(self,clientsocket,controler):
        threading.Thread.__init__(self)
        self.clientsocket = clientsocket
        self.sock = clientsocket.makefile('wb')
        self.controler = controler
    def run(self):
        self.controler.robot.camera.start_preview()
        self.controler.robot.camera.start_recording(self.sock,format="h264")
    def stop(self):
        self.controler.robot.camera.stop_recording()
        self.clientsocket.close()

class ListenSock(threading.Thread):
    def __init__(self,controler):
        threading.Thread.__init__(self)
        self.socket = socket.socket()
        self.socket.bind(('0.0.0.0',8000))
        self.socket.listen(0)
        self.controler = controler
        self._stop = False
    def run(self):
        self.cur = None
        while not self.stop():
            (connection,address) = self.socket.accept()
            if self.cur is not None:
                self.cur.stop()
                time.sleep(1)
                self.cur = None
                print("End streaming... ready to new streaming")

            print("connection "+str(connection)+" from "+str(address))
            try:
                self.cur = StreamThread(connection,self.controler)
                self.cur.start()
            except Exception as e:
                print(e)
    def stop(self):
        self._stop = True


def start_stream(ctrl):
    conn = ListenSock(ctrl)
    conn.start()
    return conn

if __name__=="__main__":
    ctrl = TestControler()
    ctrl.start()