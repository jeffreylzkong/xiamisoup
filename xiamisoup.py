#!/usr/bin/env python
# encoding: utf-8
"""
xiamisoup.py - Without WxPython GUI version

Created by Jeffrey Kong on 2012-05-10.
Copyright (c) 2012 __MyCompanyName__. All rights reserved.
"""

# System Libraries
import urllib2
import urllib
import os
import sys

from xml.dom import minidom

# 3rd party Libraries
import eyed3
from BeautifulSoup import BeautifulSoup as bs


def Loadxml(x_id, x_type):
    tracks = []
    if x_type == '3':
        # Collection
        xml_url = 'http://www.xiami.com/song/playlist/id/' + x_id + '/type/3'
    elif x_type == '1':
        # Album
        xml_url = 'http://www.xiami.com/song/playlist/id/' + x_id + '/type/1'
    else:
        print 'not supported type!'
    print 'loading xml from ' + xml_url
    # Download from url
    reqWithHeader = urllib2.Request(
        xml_url, headers={'User-Agent':
                          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; \
                          rv:15.0)  Gecko/20100101 Firefox/15.0.1"})
    xml_req = urllib2.urlopen(reqWithHeader)
    xml_data = xml_req.read().replace('\n', '')
    # parse track info from xml
    #print xml_data
    p = minidom.parseString(xml_data)
    trackList = p.getElementsByTagName('playlist')[0].getElementsByTagName('trackList')[0]    #<DOM Element: trackList at 0x10152db48>
    tracks = trackList.childNodes
    return tracks


# Common procedure to clean up unacceptable char in windows filename
def remove(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '')
    return value


class XiamiDownload():
    def __init__(self, x_id, x_type, albname=''):
        self.x_id = x_id
        self.x_type = x_type     # valid value: 1 - Album; 3 - Collection
        self.x_albname = albname    # Give collection or album a new name
        self.tracks = Loadxml(x_id, x_type)    # tracks = [[0, song0],[1, song1]...]
        self.status = 'idle'    # valid value: ''idle'/'picDidDownload'/'mp3DidDownload'

    """ WxPython version only, WxPython GUI and Download in diff threads
    def Start(self):
        self.status = 'running'
        thread.start_new_thread(self.Run, ())
    """

    def GetCollectName(self):
        collectUrl = 'http://www.xiami.com/collect/' + self.x_id
        # Download from url
        reqWithHeader = urllib2.Request(
            collectUrl, headers={'User-Agent': "Mozilla/5.0 (Macintosh;\
                Intel Mac OS X 10.6; rv:15.0) Gecko/20100101 Firefox/15.0.1"})
        req = urllib2.urlopen(reqWithHeader)
        html = req.read()
        # Parse HTML with BeautifulSoup
        soup = bs(html)
        collectName = soup.find(
            "div", {'class': 'info_collect_main'}).find('h2').text
        return collectName

    # Private method to download one file from a url
    def __download(self, url, folder, filename):
        # Make sure the folder is exist
        if not os.path.exists(folder):
            os.makedirs(folder)
        filelocation = os.path.join(folder, filename)
        print unicode(filelocation)
        # Download file only when it is not exists
        if os.path.exists(filelocation)and(os.path.getsize(filelocation) != 0L):
            print('this file is already downloaded!')
        else:
            # Remove file if exist, this must be a Zero Byte file
            if os.path.exists(filelocation):
                os.remove(filelocation)
                print 'Deleted a 0byte file ---- ' + filename
            # Create file in folder
            f = file(filelocation, 'wb')
            # Download from url
            reqWithHeader = urllib2.Request(
                url, headers={'User-Agent': "Mozilla/5.0 (Macintosh; \
                Intel Mac OS X 10.6; rv:15.0) Gecko/20100101 Firefox/15.0.1"})
            req = urllib2.urlopen(reqWithHeader)
            # Write to file
            f.write(req.read())
            # Close file
            f.close()

    # Private method to add a tag v2.4 into a MP3
    def __addtag(self, folder, s_mp3, s_title, s_album, s_artist, s_jpg):
        audiofile = eyed3.load(os.path.join(folder, s_mp3))
        audiofile.initTag()
        audiofile.tag.title = unicode(s_title)
        audiofile.tag.album = unicode(s_album)
        audiofile.tag.artist = unicode(s_artist)
        # read image into memory
        imagedata = open(os.path.join(folder, s_jpg), "rb").read()
        audiofile.tag.images.set(3, imagedata, "image/jpeg")
        audiofile.tag.save()
        """
        tag = eyeD3.Tag()
        tag.link(os.path.join(folder,s_mp3))
        tag.setVersion([2,4,0])
        tag.setTextEncoding(eyeD3.UTF_8_ENCODING)
        tag.setTitle(s_title)
        tag.setAlbum(s_album)
        tag.setArtist(s_artist)
        tag.addImage(eyeD3.ImageFrame.FRONT_COVER, os.path.join(folder,s_jpg))
        tag.update()
        """

    # Private method to decode xiami mp3 location
    def __decode(self, sourceString):
        # sample: 6hAFat2225272.t%fm%6F5E%63mt21i2%1%8552ppF..F562%E653%%xn1E4F219832ie8%1%59_9
        # decoded to : http://f1.xiami.net/18260/164125/08%201976569_232589.mp3
        factor = int(sourceString[0])   # 6
        s = sourceString[1:]            #
        divide = len(s) / factor        # 76 / 6 = 12
        left = len(s) % factor          # 76 % 6 = 4
        matrix = []
        url = []
        for i in range(factor):
            if i < left:
                x = s[(divide+1)*i: (divide+1)*(i+1)]
            else:
                x = s[(divide+1)*left+(i-left)*divide:
                      (divide+1)*left+(i-left+1)*divide]
            matrix.append(x)
        for i in range(divide):
            for j in range(factor):
                url.append(matrix[j][i])
        for j in range(left):
            url.append(matrix[j][divide])
        urlstring = ''.join(url)
        return urllib.unquote(urlstring).replace('^', '0')

    def Run(self):
        for song in self.tracks:
            s_title = song.getElementsByTagName('title')[0].firstChild.data
            # some songs are not with album, e.g. Demos
            if song.getElementsByTagName('album_name')[0].firstChild:
                s_album = \
                    song.getElementsByTagName('album_name')[0].firstChild.data
            else:
                s_album = 'Demos'
            s_artist = song.getElementsByTagName('artist')[0].firstChild.data
            s_location = \
                song.getElementsByTagName('location')[0].firstChild.data
            # sometimes pic is not available in the playlist
            picList = song.getElementsByTagName('pic')
            if picList:
                s_purl = song.getElementsByTagName('pic')[0].firstChild.data
            else:
                # keep using the last pic...buggy but doesn't matter for now.
                pass
            # decode location to url
            s_surl = self.__decode(s_location)
            # prepare to download
            #     mp3 / pic name = album + artist + title .mp3/.jpg
            s_name = s_title
            # Clean up filename
            s_name = s_name.replace('/', '-')
            # Clean up invalid character in file name ( For Windows, too bad)
            s_name = remove(s_name, '\/:*?"<>|')
            s_mp3 = s_name + '.mp3'
            s_jpg = s_name + '.jpg'
            # Take albumn name as folder name
            folder = self.x_albname
            if self.x_type == '1' and self.x_albname == '':
                folder = s_album
            if self.x_type == '3' and self.x_albname == '':
                folder = self.GetCollectName()
            # download cover picture
            print 'Downloading pic ' + s_title.encode('utf-8') + \
                ' by ' + s_artist.encode('utf-8') + '...'
            self.__download(s_purl, folder, s_jpg)
            # Update Panel information about current song
            # Update image after picture download
            self.status = 'picDidDownload'
            # WxPython version only
            #s_jpg_loc = os.path.join(folder,s_jpg)
            #evt = UpdateDownloadEvent(s_jpg_loc=s_jpg_loc,  s_title=s_title, s_album=s_album, s_artist=s_artist, status=self.status, s_index=index)
            #wx.PostEvent(self.win, evt)
            # download mp3
            print 'Downloading song ' + s_title.encode('utf-8') + \
                ' by ' + s_artist.encode('utf-8') + '...'
            self.__download(s_surl, folder, s_mp3)
            self.__addtag(folder, s_mp3, s_title, folder, s_artist, s_jpg)
            self.status = 'mp3DidDownload'
            # WxPython version only
            #evt = UpdateDownloadEvent(status=self.status, s_index=index)
            #wx.PostEvent(self.win, evt)
        self.status = 'idle'
        # WxPython version only
        #evt = UpdateDownloadEvent(status=self.status)
        #wx.PostEvent(self.win, evt)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print '------------------------------------------------------------------------'
        print 'XiamiSoup - Enjoy Music from www.xiami.com  Version: v1.0  May-10 2012'
        print '------------------------------------------------------------------------'
        print 'Usage: python xiamisoup.py "id_of_album_or_collection" "type_of_album_or_collection"'
        print '     * id_of_album_or_collection: ID shows in the url of an album or collection page;'
        print '         e.g. 27811761 from collection "http://www.xiami.com/song/showcollect/id/27811761"'
        print '         e.g. 65783821 from album "http://www.xiami.com/album/65783821"'
        print '     * type_of_album_or_collection: "1" for Album and "3" for Collection'
        print 'Example 1: python xiamisoup.py 278117611 3 will download collection 小爵士❤拿捏一段慵懒的时光;'
        print 'Example 2: python xiamisoup.py 65783821 1 will download album 致青春'
        sys.exit()
    else:
        x_id = sys.argv[1]
        x_type = sys.argv[2]
        xd = XiamiDownload(str(x_id), str(x_type))
        xd.Run()

