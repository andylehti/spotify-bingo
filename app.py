from math import factorial
import string
import numpy as np
from textwrap import wrap
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import random
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns

def getBase(c, e=0):
    b = ''.join([x for x in string.printable[:90] if x not in '/\\`"\',_!#$%&()*']) + '&()*$%/\\`"\',_!#'
    return b[e:c+e]

def fromBase(s, b=87, e=0):
    c = getBase(b, e)
    return sum(c.index(d) * b**i for i, d in enumerate(reversed(s)))

def calcKey(r):
    a = ['badd','6666','0e66','fc75','f4ec','7d78','1e12','4f9c',
           '4582','4fad','b740','a29d','4ddd','b86b','96b9','2e4d','84ad']
    n, h = len(a), a
    r -= 1
    a = sorted(a)
    t = []
    for i in range(n):
        fac = factorial(n - 1 - i)
        x = r // fac
        t.append(a.pop(x))
        r %= fac

    p = t.index(h[1])
    a = t[:p]
    b = t[p+1:]
    return "".join(a), "".join(b)

def extractPlaylist(url):
    pattern = r"(?:spotify:playlist:|playlist/)([A-Za-z0-9]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def trimTitle(title, delimiters, trimFirst):
    pattern = f"[{''.join(map(re.escape, delimiters))}]"
    title = title.strip()
    if trimFirst:
        parts = re.split(pattern, title, maxsplit=1)
        return parts[0].strip() if len(parts) > 1 else title.strip()
    else:
        return re.sub(pattern + r".*", "", title).strip()

def drawText(canvasObj, title, artist, x, y, width, maxTitle, maxArtist, fontSize, lineSpacing):
    canvasObj.setFont("Helvetica-Bold", fontSize)
    titleLines = wrap(title, width)[:maxTitle]
    titleY = y
    for i, line in enumerate(titleLines):
        lineY = titleY - (i * (fontSize + lineSpacing))
        canvasObj.drawCentredString(x, lineY, line)
    
    canvasObj.setFont("Helvetica", fontSize - 5)
    artistY = y - (maxTitle * (fontSize + lineSpacing)) - fontSize + 5
    artistLines = wrap(artist, 32)
    if len(artistLines) > maxArtist:
        artistLines = artistLines[:maxArtist - 1] + [artistLines[maxArtist - 1][:29] + "..."]

    for i, artistLine in enumerate(artistLines):
        lineY = artistY - (i * (fontSize + lineSpacing))
        canvasObj.drawCentredString(x, lineY, artistLine)
    
    canvasObj.setFont("Helvetica-Bold", fontSize)

def fetchTracks(sp, playlistId):
    tracks = []
    limit = 100
    offset = 0
    while True:
        results = sp.playlist_items(playlistId, limit=limit, offset=offset)
        tracks.extend(results["items"])
        if not results["next"]:
            break
        offset += limit
    return tracks

def prepareTracks(playlistTracks, delimiters, trimFirst):
    trackDict = {}
    for item in playlistTracks:
        track = item["track"]
        if track is None:
            continue
        originalTitle = track["name"]
        trimmed = trimTitle(originalTitle, delimiters, trimFirst)
        artist = ", ".join(a["name"] for a in track["artists"])
        key = f"{trimmed} - {artist}"
        trackDict[key] = {"title": trimmed, "artist": artist}
    uniqueTracks = list(trackDict.values())
    random.shuffle(uniqueTracks)
    return uniqueTracks

def createCards(uniqueTracks, numCards):
    cards = []
    needed = numCards * 24
    if len(uniqueTracks) < needed:
        pool = (uniqueTracks * ((needed // len(uniqueTracks)) + 1))[:needed]
    else:
        pool = uniqueTracks[:needed]

    for i in range(numCards):
        chunk = pool[i*24 : (i+1)*24]
        chunk.insert(12, {"title": "FREE", "artist": ""})
        cards.append(chunk)
    return cards

def analyzeDuplicates(cards):
    duplicateHeatMap = [[0]*5 for _ in range(5)]
    positionDict = {(r, c): set() for r in range(5) for c in range(5)}

    for card in cards:
        for idx, trackInfo in enumerate(card):
            row, col = divmod(idx, 5)
            trackName = trackInfo["title"] + " - " + trackInfo["artist"]
            if trackName in positionDict[(row, col)]:
                duplicateHeatMap[row][col] += 1
            else:
                positionDict[(row, col)].add(trackName)
    return duplicateHeatMap

def generateHeatmap(duplicateHeatMap):
    plt.figure(figsize=(6, 6))
    sns.heatmap(duplicateHeatMap, annot=True, fmt="d", cmap="coolwarm", cbar=True,
                linewidths=0.5, linecolor='gray', xticklabels=['B','I','N','G','O'],
                yticklabels=['1','2','3','4','5'])
    plt.title("Duplicate Detection Heatmap")
    plt.xlabel("Bingo Columns")
    plt.ylabel("Bingo Rows")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='PNG')
    plt.close()
    buf.seek(0)
    return buf

def generateBingo(cards, fileName, pageTitle):
    heatMap = analyzeDuplicates(cards)
    heatMapImage = generateHeatmap(heatMap)
    heatMapReader = ImageReader(heatMapImage)

    c = canvas.Canvas(fileName, pagesize=letter)
    pageWidth, pageHeight = letter

    # Cover page
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(pageWidth / 2, pageHeight - 1.5 * inch, "Spotify Playlist Bingo")
    c.setFont("Helvetica", 14)
    c.drawCentredString(pageWidth / 2, pageHeight - 2 * inch, "Duplicate Detection Analysis")

    heatMapWidth = 5 * inch
    heatMapHeight = 5 * inch
    c.drawImage(heatMapReader, (pageWidth - heatMapWidth) / 2,
                pageHeight - 2.5 * inch - heatMapHeight,
                width=heatMapWidth, height=heatMapHeight)

    
    description = """
    Duplicate Detection:

    This heatmap highlights positions in bingo cards where duplicate tracks 
    were detected most frequently. Higher values indicate more duplicates in 
    a particular grid position. The heatmap uses a coolwarm color scheme for 
    easy visualization.

    Each bingo card includes unique tracks, with a central 'FREE' space.
    """
    textObject = c.beginText(1 * inch, pageHeight - 2.5 * inch - heatMapHeight - 1.5 * inch)
    textObject.setFont("Helvetica", 10)
    #textObject.setCharSpace(1.5)
    for line in description.strip().split('\n'):
        textObject.textLine(line.strip())
    c.drawText(textObject)

    c.showPage()

    fontSize = 11
    lineSpacing = 4
    gridSize = 5
    cellSize = 1.6 * inch
    gridWidth = cellSize * gridSize
    gridHeight = cellSize * gridSize

    marginLeft = (pageWidth - gridWidth) / 2
    marginTop = (pageHeight + gridHeight) / 2

    charLimit = 16
    maxTitle = 3
    maxArtist = 1

    for cardItems in cards:
        # Draw the user-provided title at the top of each page
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(pageWidth / 2, pageHeight - 1 * inch, pageTitle)

        for row in range(gridSize):
            for col in range(gridSize):
                xPos = marginLeft + (col * cellSize)
                yPos = marginTop - (row * cellSize)

                c.rect(xPos, yPos - cellSize, cellSize, cellSize, stroke=1, fill=0)

                itemIndex = row * gridSize + col
                track = cardItems[itemIndex]
                titleToDraw = track["title"]
                artistToDraw = track["artist"]

                textX = xPos + (cellSize / 2)
                textY = yPos - (cellSize / 2)

                drawText(
                    c, titleToDraw, artistToDraw,
                    textX, textY, charLimit,
                    maxTitle, maxArtist,
                    fontSize, lineSpacing
                )
        c.showPage()

    c.save()

def main():
    st.title("Spotify Playlist Bingo Card Generator")
    st.write("Generate bingo cards using track titles from a Spotify playlist.")

    defaultPlaylist = "https://open.spotify.com/playlist/0So85N4Wfnw98d0FC9sDaR"
    playlistUrl = st.text_input("Enter Spotify playlist URL", value=defaultPlaylist)

    defaultDelims = ["-", "(", "[", "<", ">", "\"", ":"]
    delimitersInput = st.text_input("Custom Delimiters (comma-separated)", value=", ".join(defaultDelims))
    delimiters = [d.strip() for d in delimitersInput.split(",") if d.strip()]

    trimFirst = st.checkbox("Trim all before the first delimiter?", value=True)
    numCards = st.number_input("Number of Bingo Cards:", min_value=16, value=16, step=16)

    pageTitle = st.text_input("Page Title for Each Card", value="Spotify Bingo Title")

    clientCredentials = st.text_input(
        "Enter Client Credentials (client_id<separator>client_secret)",
        help="Separate client_id and client_secret separated by any non-hexadecimal character."
    )

    if "uniqueTracks" not in st.session_state:
        st.session_state.uniqueTracks = None
    if "currentPlaylist" not in st.session_state:
        st.session_state.currentPlaylist = None

    clientId, clientSecret = None, None

    if clientCredentials:
        if len(clientCredentials) < 20:
            sec = clientCredentials
            rVal = fromBase(sec)
            aVal, bVal = calcKey(rVal)
            k = aVal + '+' + bVal
            splitResult = re.split(r'[^0-9a-fA-F]', k)
        else:
            splitResult = re.split(r'[^0-9a-fA-F]', clientCredentials)

        if len(splitResult) >= 2:
            clientId = splitResult[0]
            clientSecret = splitResult[1]
        else:
            st.error("Invalid format for client credentials. Ensure they are separated by a non-hex character.")
            clientId = None
            clientSecret = None

    if playlistUrl and clientId and clientSecret:
        playlistId = extractPlaylist(playlistUrl)
        if playlistId:
            if playlistUrl != st.session_state.currentPlaylist:
                st.session_state.uniqueTracks = None
                st.session_state.currentPlaylist = playlistUrl

            if st.session_state.uniqueTracks is None:
                try:
                    sp = spotipy.Spotify(
                        auth_manager=SpotifyClientCredentials(client_id=clientId, client_secret=clientSecret)
                    )
                except spotipy.SpotifyException as e:
                    st.error(f"Authentication failed: {e}")
                    st.stop()

                allTracks = fetchTracks(sp, playlistId)
                uniqueTracks = prepareTracks(allTracks, delimiters, trimFirst)
                st.session_state.uniqueTracks = uniqueTracks

            uniqueTracks = st.session_state.uniqueTracks

            if len(uniqueTracks) < 24:
                st.warning("The playlist must contain at least 24 distinct tracks.")
            else:
                cards = createCards(uniqueTracks, numCards)
                fileName = "bingo_cards.pdf"
                generateBingo(cards, fileName, pageTitle)

                with open(fileName, "rb") as f:
                    pdfData = f.read()
                st.download_button("Download Bingo PDF", data=pdfData, file_name=fileName)
        else:
            st.warning("Invalid playlist URL. Could not detect a valid playlist ID.")
    elif playlistUrl and (not clientCredentials):
        st.info("Please enter your Spotify client credentials to generate bingo cards.")

if __name__ == "__main__":
    main()
