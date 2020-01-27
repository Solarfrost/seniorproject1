from tkinter import *
from tkinter import ttk
from neopixel import *
import pymysql
#import mysql.connector
import socket
#import sys
import threading
#import socketserver
import sched
import time
import argparse
import signal
import sys
import traceback

# setup SQL connection
conn = pymysql.connect(host="localhost", user="sqlaccess",
						passwd="password", db="buildingdb")
						


LED_COUNT = 50
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 5
LED_INVERT = False
LED_BRIGHTNESS = 75
LED_CHANNEL = 0
LED_STRIP = ws.WS2811_STRIP_GRB



 
 
class Main:
  def __init__(self):
    # GUI setup
    root = Tk()
    root.title('Map Control')
    root.geometry("800x400")
    
    frame = Frame(root)
    frame.pack()
    
    tabBar = ttk.Notebook(root)
    tab1Main = ttk.Frame(tabBar)
    tab2Add = ttk.Frame(tabBar)
    tab3Remove = ttk.Frame(tabBar)
    tab4UDPmon = ttk.Frame(tabBar)
    tabBar.add(tab1Main, text='Main')
    tabBar.add(tab2Add, text='Add Building')
    tabBar.add(tab3Remove, text='Remove Building')
    tabBar.add(tab4UDPmon, text='Incoming UDP')
    tabBar.pack(side="top", fill="both", expand="true")
    
    
    self.fields = {}
    
    
    # tab2Add Code
    
    l = Label(tab2Add, text="Building:")
    l.grid(row=0, column=0)
    self.fields['building'] = Entry(tab2Add)
    self.fields['building'].grid(row=0, column=1)
     
    l = Label(tab2Add, text="LED Number:")
    l.grid(row=2, column=0)
    self.fields['ledNumber'] = Entry(tab2Add)
    self.fields['ledNumber'].grid(row=2, column=1)
        
    submitbtn = Button(tab2Add, text="Insert", command=self.do_insert)
    submitbtn.grid(row=11, column=0)
    
    clearbtn = Button(tab2Add, text="Clear", command=self.do_clear)
    clearbtn.grid(row=11, column=1)
    
    
    # tab3Remove Code
    l = Label(tab3Remove, text='Select building to remove:')
    l.grid(row=0, column=0)
    showConn = conn.cursor()
    showConn.execute("""SELECT * FROM BuildingInfo ORDER BY building""")
    buildingList = list(showConn.fetchall())
    
    buildingListIterator = StringVar(root)
    buildingListIterator.set("Select building")
    #buildingListIterator.set(buildingList[0])
    
    self.buildingSelect = OptionMenu(tab3Remove, buildingListIterator, *buildingList, command=self.setBuilding)
    self.buildingSelect.grid(row=2, column=0)
    
    
    confirmRmvbtn = Button(tab3Remove, text="Confirm Removal", command=self.do_removeBuilding)
    confirmRmvbtn.grid(row=11, column=0)
    
    
    # tab4UDPmon code

    # UDP Listening code
    listen_thread = threading.Thread(target=self.start_server)
    listen_thread.daemon = True
    listen_thread.start()
    
    
    
    # LED code
    
    led_thread = threading.Thread(target=self.led_control)
    led_thread.daemon = True
    led_thread.start()
    
    
    root.mainloop()
 
 
 #button to clear the fields in tab2Add
  def do_clear(self):
    self.fields['building'].delete(0,END)
    self.fields['ledNumber'].delete(0,END)
 
 
 #button to add the values in tab2Add to the SQL db
  def do_insert(self):
	  # This is used for debugging. It prints the querry into the console.
    sql = "INSERT INTO BuildingInfo VALUES ledNumber='%s',building='%s'"%(
          self.fields['ledNumber'].get(),self.fields['building'].get())
    print(sql)
    try:
        addConn = conn.cursor()
        addConn.execute("""INSERT INTO BuildingInfo VALUES (%s,%s,%s)""",(self.fields['ledNumber'].get(), self.fields['building'].get(), "OK"))	
        conn.commit()
	#below is not working
    except IntegrityError as err:
    #except pymysql.connector.IntegrityError as err:
        tkMessageBox.showinfo("Error: Key Already Exists", err.get())
        print("Error: {}".format(err))
    except pymysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Bad username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        elif err.errno == errorcode.ER_DUP_ENTRY:
            print("LED is already in use.")
        else:
            print(err)
            sqlConnection.close()
  
  
  
  
  ##used in tab3Remove to get the building selected in the option menu
  def setBuilding(self, value):
	  global selectedBuilding
	  selectedBuilding = value
	  print(selectedBuilding)
  
  
  #controls UDP listening
  def start_server(self):
      global udp_data
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.bind(("10.160.3.9", 514))
      #sock.bind(("127.0.0.1", 514))
      
      while True:
          udp_data = sock.recvfrom(1024)
          print(udp_data)
          udp_message = udp_data[0].split()
          udp_event = udp_message[7]
          udp_building = udp_message[8]
          udp_event = udp_event.decode("utf-8")
          udp_building = udp_building.decode("utf-8")
          if udp_event.startswith('event="'):
              udp_event = udp_event[7:-1]
          if udp_building.startswith('building="'):
              udp_building = udp_building[10:]
          if udp_building.endswith('"'):
              udp_building = udp_building[:-1]
          print(udp_event)
          print(udp_building)
          try:
              updateConn = conn.cursor()
              updateConn.execute("""UPDATE BuildingInfo SET status = %s WHERE building = %s""",(udp_event, udp_building))
              conn.commit()
              #traceback.print_exc()
          except DataError as err:
              if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                  print("Bad username or password")
      

    #controls the LEDs
  def led_control(self):
      strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
      strip.begin()
      while True:
          ledCursor = conn.cursor()
          ledCursor.execute("""SELECT * FROM BuildingInfo""")
          statusList=ledCursor.fetchall()
          for ledNum, building, ledStatus in statusList:
              #the led strip begins its referencing at 0. Ex: LED 1 is 0 in code, LED 2 is 1 in code
              ledNum = ledNum - 1
              if ledStatus == "Up" or ledStatus == "OK" or ledStatus == "up":
                  #green
                  strip.setPixelColor(ledNum, Color(255,0,0))
              elif ledStatus == "Alarm":
                  #blue
                  strip.setPixelColor(ledNum, Color(0,0,255))
              elif ledStatus == "Warning":
                  #orange
                  strip.setPixelColor(ledNum, Color(165,255,0))
              elif ledStatus == "Critical":
                  #pink
                  strip.setPixelColor(ledNum, Color(105,255,180))
              elif ledStatus == "Down":
                  #red
                  strip.setPixelColor(ledNum, Color(0,255,0))
          strip.show()
          time.sleep(5)
  
  
  
  
  #button to remove the selected building in tab3Remove from the DB
  def do_removeBuilding(self):
    led, building, status = selectedBuilding
    print(led)
    sql = "SELECT * FROM BuildingInfo ORDER BY building"
    print(sql)
    try:
        removeConn = conn.cursor()
        removeConn.execute("""DELETE FROM BuildingInfo WHERE ledNumber = %s""",(led))
        conn.commit()
	#Below isn't working
    except pymysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Bad username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
            sqlConnection.close()

if __name__=="__main__":
    Main()
    
