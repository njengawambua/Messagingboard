
from flask import Flask, render_template,request,session,g,current_app,redirect,url_for,make_response
from flask_socketio import SocketIO,join_room,leave_room,rooms
from datetime import  datetime
import json
import sqlite3
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from random import random
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
maindb='maindb.sqlite3'
import os
from threading import Thread
import requests
from requests import Request

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app,async_mode="threading")

def getdb(maindb):
  try:
    db = sqlite3.connect(maindb)
    return db
  except:
    return "db conn failed"


def getUser():
  try:
    db=getdb(maindb)
    cur=db.cursor()
    #got db")
    try:
      #getting user
      u=cur.execute("select * from Account").fetchone()
      if not u:
        #no user in account found
        return False
      else:
        #got user
        us={'Id':u[0],'Name':u[1],'Email':u[2],'DP':u[3],'Role':u[4]} 
        session['User']=us
        return us    
    except:
      #failed to get user
      return False
  except:
    #failed to get db
    return False   

@app.route("/")
def Board():
  if getUser():
    #got session
  else:
    # handle session creation error
  return render_template("board.html")

@sio.on('joinboard',namespace="/post")
def joinboard(data):
  if getUser():
    #got session")
  else:
    #session creation error
  try:
    db=getdb(maindb)
    cur=db.cursor()
    #got db and cursor
    join_room('board',sid=request.sid,namespace="/post")
    try:
      posts=cur.execute("select * from Posts").fetchall()
      if not posts:
        #no posts
        return 
      else:
        #got posts
        for p in posts:
          #loop posts
          #get post creator data
          comte=cur.execute("select * from Account where Id=?",([p[2]])).fetchone()
          if not comte:
            #No creator data
            #pass
          else:
            myp={"PostId":p[0],"Post":p[1],"UserId":p[2],"Date":p[4],'Username':comte[1],"DP":comte[3],'Flagged':p[5]}
            sio.emit("newpost",myp,room=request.sid,namespace="/post")

            #check if post has media attatchments
            postatt=cur.execute("select * from PostAtt where PostId=?",([p[0]])).fetchall()
            if not postatt:     
              myp={"PostId":p[0],"Post":p[1],"UserId":p[2],"Date":p[4],'Username':comte[1],"DP":comte[3]}
              sio.emit("newpost",myp,room=request.sid,namespace="/post")
            else:
              for at in postatt:
                #loop media attatchments
                mat={'Id':at[0],"Name":at[2],'Type':at[3],'Size':at [4],"PostId":at[1]}
                sio.emit("postatt",mat,room=request.sid,namespace="/post")             
            #getting post comments
            comms=cur.execute("select * from PostComments where PostId=? ORDER BY Date asc",([p[0]])).fetchall()
            if not comms:
              #no comment")
              f={'Id':p[0],'Count':0}
              sio.emit("comcount",f,room=request.sid,namespace="/post")
            else:
              #\n got comments
              co=[]            
              f={'Id':p[0],'Count':len(comms)}
              myp['Count']=len(comms)
              sio.emit("comcount",f,room=request.sid,namespace="/post")
              for com in comms:
                ##get commentor
                comt=cur.execute("select * from Account where Id=?",([com[2]])).fetchone()
                if not comt:
                  #no comm")               
                else:
                  #got commentor data
                  c={'Id':com[0],'Comment':com[1],'UserId':com[2],'Date':com[5],"Username":comt[1],"DP":comt[3],"Userid":comt[0],'PostId':p[0]}
                  sio.emit("postcomment",c,room=request.sid,namespace="/post")
        return
    except:
      db.close()
      #failed to get Posts
      return ("failed to get Posts")
  except:
    #failed to get db
    return ("failed db")

@sio.on("postcomment",namespace="/post")
def broadComment(data):
  data['DP']=user['DP']
  PostComment(data)

def PostComment(comment):
  user=''
  if session['User']:
    user=session['User']
    #got usr")
    userid=user['Id']
    n=session['User']
    Name=user["Name"]
    comment['Username']=user["Name"]
  else:
    #redirect to login page
  print(userid)
  try:
    #getting db")
    db=getdb(maindb)
    cur=db.cursor()
    try:
      date=datetime.ctime(datetime.now())
      Date=date[:-5]
      comment['Date']=Date
      if comment["Type"]=='Create':
        #got create"
        #create comment id
        pids=int(random()*100000000)
        cur.execute("INSERT into PostComments (Id,Comment,UserId,PostId,Date) values (?,?,?,?,?)",([pids,comment['Comment'],userid,comment['PostId'],Date]))
        db.commit()
        comment['Id']=pids
        sio.emit("postcomment",comment,namespace="/post")
        return
      else:
        try:
          #getting comment
          com=cur.execute("select * from PostComments where Id=? and PostId=?",([comment['Id'],comment['PostId']])).fetchone()
          if not com:
            #comment not found"
            return ("comment not found")
          else:
            if com[2]==userid or user["Role"]=='Admin':
              if comment["Type"]=='Delete':
                #got delete
                cur.execute("DELETE from PostComments where Id=?",([comment['Id']]))
                db.commit()
                db.close()
                sio.emit("managecomment",comment,namespace="/post")
                return
              if comment["Type"]=='Edit':
                #got edit
                cur.execute("UPDATE  PostComments set Comment=?,Date=? where Id=?",([comment['Comment'],date,comment['Id']]))
                db.commit()
                db.close()
                sio.emit("managecomment",comment,namespace="/post")
                return
              if comment["Type"]=='Flag':
                  #got flag")
                  cur.execute("UPDATE PostComments set Flagged=? where Id=?",(["True",comment['Id']]))
                  db.commit()
                  db.close()
                  sio.emit("managecomment",comment,namespace="/post")
                  return
          db.close()
          return
        except :
          db.rollback()
          db.close()
          #unable to get comment and make change")
          return("unable to get comment and make change")
    except:
      db.rollback()
      db.close()
      #unable to change b4 type selection")
      return("unable to change b4 type selection")
  except :
    #unable to get db and cursor")
    return("unable to get db and cursor")

@sio.on("post",namespace="/post" )
def post(da):
  #create new post
  #check if in session
  try:
    #getting db")
    db=getdb(maindb)
    cur=db.cursor()
    cc=cur.execute("select * from Account where Id=?",([userid])).fetchall()
    print(cc)
    if cc:
      date=datetime.ctime(datetime.now())
      ##post id
      msid=int(random()*10000000000)
      print(userid,post,date,msid)
      cur.execute("insert into Posts (Id,Post,UserId,Status,Date) values(?,?,?,?,?)",([msid,da['Post'],user['Id'],'Active',date]))
      db.commit()
      db.close()
      da['Date']=date
      da['UserId']=user['Id']
      da['PostId']=msid
      #message saved")
      if 'File' in da:
        #got file")
        sio.emit('newpost',da,namespace="/post")
        td.run(addpost(da,msid))
      else:
        #no file
        sio.emit('newpost',da,namespace="/post")
  except:
    #db eeeeeeerror")
    db.close()
    return "db error"

def addpost(da,msid):
  #threading ")
  try:
    db=getdb(maindb)
    cur=db.cursor()
    #got db")
    data=da['File']
    for i in data:
      #file name
      n=str(int(random()*100000)) +"."+i['Ext']
      #db id
      atpid=int(random()*100000)
    
      vs="./static/Images/PostPictures/"+n
      fi=open(vs,"wb+")
      fi.write(i['File'])
      fi.flush()
      fi.close()
      cur.execute("insert into PostAtt (Id,Name,PostId,Type) values(?,?,?,?)",([atpid,n,msid,i['Type']]))
      db.commit()
      i['File']=n
      i['AttId']=atpid
      dd=da
      ti=i['Type']
      i.pop('Name')
      dd['File']=i
      print(dd['File'])
      mat={'Id':atpid,"Name":n,'Type':ti,'Size':'',"PostId":msid}
      sio.emit("postatt",mat,room=request.sid,namespace="/post")  
    db.close()
    return 1
  except:
    db.rollback()
    db.close()
    return "failed to save files"

@app.route('/timeline')
def timeline():
  mypost=[]
  try:
    db=getdb(maindb)
    cur=db.cursor()
    #got db and cursor")
    try:
      posts=cur.execute("select * from Posts").fetchall()
      if not posts:
        #no posts")
        return render_template("timeline.html",Posts={  })
      else:
        #got posts",posts)
        for p in posts:
          comte=cur.execute("select * from Users where Id=?",([p[2]])).fetchone()
          if not comte:
            #No commetor")

          else:
            usrn=comte[1]+" "+comte[2]+" "+comte[3]
            postatt=cur.execute("select * from PostAtt where PostId=?",([p[0]])).fetchall()
            myp={"Id":p[0],"Post":p[1],"UserId":p[2],"Date":p[4],'Username':usrn,"DP":comte[9]}
            if not postatt:
              #\n no attatchments")
            else:
              #\n got attachmnets",postatt)
              mas=[]
              for at in postatt:
                mat={'Id':at[0],"Name":at[2],'Type':at[3],'Size':at [4]}
                #mat",mat)
                mas.append(mat)
              myp['Att']=mas
              #mas",mas)
            comms=cur.execute("select * from PostComments where PostId=? ORDER BY Date asc",([p[0]])).fetchall()
            if not comms:
              #no comments")
              myp['Comments']=[]
              myp['Count']=0
            else:
              co=[]
              myp['Count']=len(comms)
              for com in comms:
                ##get commentor
                comt=cur.execute("select * from Users where Id=?",([com[2]])).fetchone()
                if not comt:
                  #no comm")
                else:
                  username=comt[1]+" "+comt[2]+" "+comt[3]
                  c={'Id':com[0],'Comment':com[1],'UserId':com[2],'Date':com[5],"Username":username,"DP":comt[9],"Userid":comt[0]}
                  co.append(c)
              myp['Comments']=co

            mypost.append(myp)
        #\n posts with comments and atts \n",mypost)
        Posts={'Posts':mypost}
        db.close()
        #almaost")
        return render_template("timeline.html",Posts=Posts)
    except:
      db.close()
      #failed to get Posts")
      return ("failed to get Posts")
  except:
    #failed db")
    return ("failed db")

@sio.on("manageposts",namespace="/post")
def ManagePosts(data):
    managePosts(data)
    #done managing posts")

def managePosts(data):
    print(data)
    user=''
    if 'User' in session.keys():
        user=session['User']
    else:
        #not allowed")
        return render_template('signin.html')
    try:
        db=getdb(maindb)
        cur=db.cursor()
        #got db")
        try:
            po=cur.execute("select * from Posts where Id=?",([data['PostId']])).fetchone()
            if not po:
                db.close()
                return
            else:
                if data['Type']=='Flag':
                    #flagging post")
                    try:
                      cur.execute("UPDATE Posts set Flagged=? where Id=?",(["true",data["PostId"]]))
                      db.commit()
                      db.close()
                      #done flagging")
                      sio.emit("postupdate",data,namespace="/post")
                      return ''
                    except:
                      #failed to flag")
                      db.rollback()
                      db.close()
                      return ''
                else:
                    if user[8]!='Admin' or po[2]!=user[0]:
                        ##neither admin nor post creator
                        db.close()
                        return
                    else:
                        if data['Type']=='Edit':
                            #editing post")
                            cur.execute("UPDATE Posts set Post=? where Id=?",([data['Post'],data["Id"]]))
                            db.commit()
                            da={'Id':data['Id'],'Post':data['Post']}
                            sio.emit("manageposts",da,namespace="/post")
                            #post text edited")
                            ##emit new change
                            if "Files" in data:
                                #got files")
                                print(data['Files'])
                                for i in data['Files']:
                                    ##check if they belong to post
                                    print(i)
                                    print(i['Id'])
                                    print(data['Id'])
                                    flil=cur.execute("select * from PostAtt where Id=(?) and PostId=(?)",([i['Id'],data['Id']]))
                                    #got file in atta")
                                    if not flil:
                                        #file not found")
                                        return
                                    else:
                                        #got file in atta")
                                        cur.execute("DELETE from PostAtt where Id=?",([i['Id']]))
                                        db.commit()
                                        da={'Id':data['Id'],'Files':i}
                                        ###emit new ch
                                        sio.emit("manageposts",da,namespace="/post")
                                db.close()
                            else:
                                #no files")
                                db.close()
                                return
                        if data['Type']=='Delete':
                            #got delete")
                            try:
                              ##get all attatchments
                              cur.execute("DELETE  from PostAtt where PostId=?",([data['PostId']]))
                              cur.execute("DELETE  from Posts where Id=?",([data['PostId']]))
                              db.commit()
                              db.close()
                              sio.emit("postupdate",data,namespace="/post")
                              return ''
                            except:
                              #failed to delete")
                              db.rollback()
                              db.close()
                              return ''
        except:
            #unable to make changes",data['Type'])
            db.rollback()
            db.close()
            return
    except:
        #unable to get db")
        return

