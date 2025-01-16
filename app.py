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
    b = ''.join([x for x in string.printable[:90] if x not in '/\\`"\',_!#$%&()*']) + '&()*$%/\\`"\',_!'
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

def drawText(canvasObj, title, artist, x, y, width, maxTitle, maxArtist, fontSize, lineSpacing, showArtists=True):
    """
    Draws the song title (in bold) and artist (in smaller font) inside a square on the bingo card.
    """
    canvasObj.setFont("Helvetica-Bold", fontSize)
    titleLines = wrap(title, width)[:maxTitle]
    titleY = y
    for i, line in enumerate(titleLines):
        lineY = titleY - (i * (fontSize + lineSpacing))
        canvasObj.drawCentredString(x, lineY, line)
    
    if showArtists:
        # Artist in smaller font
        canvasObj.setFont("Helvetica", fontSize - 5)
        artistY = y - (maxTitle * (fontSize + lineSpacing)) - fontSize + 5
        artistLines = wrap(artist, 32)
        if len(artistLines) > maxArtist:
            artistLines = artistLines[:maxArtist - 1] + [artistLines[maxArtist - 1][:29] + "..."]

        for i, artistLine in enumerate(artistLines):
            lineY = artistY - (i * (fontSize + lineSpacing))
            canvasObj.drawCentredString(x, lineY, artistLine)
    
    # Restore bold
    canvasObj.setFont("Helvetica-Bold", fontSize)

def fetchTracks(sp, playlistId):
    """
    Fetches all tracks from a Spotify playlist, handling pagination
    by iterating until there are no more tracks.
    """
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
    """
    Creates a dictionary of unique tracks based on trimmed titles + artist.
    Returns a shuffled list of these unique track dicts, each with keys {title, artist}.
    """
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
    """
    Generates the requested number of Bingo cards. Each card is a list of 25 items
    (with the middle item set to "FREE").
    """
    cards = []
    pool = uniqueTracks[:]
    random.shuffle(pool)
    index = 0

    for i in range(numCards):
        if index + 24 > len(pool):
            pool = uniqueTracks[:]
            random.shuffle(pool)
            index = 0

        chunk = pool[index:index+24]
        index += 24

        # Insert the 'FREE' space in the center
        chunk.insert(12, {"title": "FREE", "artist": ""})
        cards.append(chunk)

    return cards

def analyzeDuplicates(cards):
    """
    Creates a 5x5 grid that counts how many times a position is repeated across multiple cards.
    """
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
    """
    Uses Seaborn to generate a heatmap image from the 2D array of duplicates.
    Returns a BytesIO buffer of the PNG image.
    """
    plt.figure(figsize=(6, 6))
    sns.heatmap(
        duplicateHeatMap,
        annot=True,
        fmt="d",
        cmap="coolwarm",
        cbar=True,
        linewidths=0.5,
        linecolor='gray',
        xticklabels=['B','I','N','G','O'],
        yticklabels=['1','2','3','4','5']
    )
    plt.title("Duplicate Position Heatmap")
    plt.xlabel("Bingo Columns")
    plt.ylabel("Bingo Rows")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='PNG')
    plt.close()
    buf.seek(0)
    return buf

def computeSongStats(cards, numCards):
    """
    For each track (title + first-seen artist), collects:
      - Freq: how many times total it appears across all cards
      - PosFreq: sum of overlaps in the same (row,col)
      - Dup: 1 if it appears >1 time on the same card
      - MaxFreq: largest number of times in any single (row,col)
      - Dist%: (Freq / numCards) * 100
      - Rndm: 100 * (1 - (MaxFreq / Freq))
    """
    stats = {}
    positionUsage = {}

    for card in cards:
        localCount = {}
        for idx, trackInfo in enumerate(card):
            title = trackInfo["title"]
            artist = trackInfo["artist"]
            if title == "FREE":
                continue

            if title not in stats:
                stats[title] = {
                    "Artist": artist,
                    "Freq": 0,
                    "PosFreq": 0,
                    "Dup": 0,
                    "MaxFreq": 0,
                    "Dist%": 0,
                    "Rndm": 0
                }
            stats[title]["Freq"] += 1

            localCount[title] = localCount.get(title, 0) + 1

            row, col = divmod(idx, 5)
            if title not in positionUsage:
                positionUsage[title] = {}
            positionUsage[title][(row, col)] = positionUsage[title].get((row, col), 0) + 1

        # Mark duplicates if found
        for t, ccount in localCount.items():
            if ccount > 1:
                stats[t]["Dup"] = 1

    # Calculate PosFreq and MaxFreq
    for title, usageMap in positionUsage.items():
        total_overlaps = 0
        max_single = 0
        for (r, c), count in usageMap.items():
            total_overlaps += (count - 1)
            if count > max_single:
                max_single = count
        stats[title]["PosFreq"] = total_overlaps
        stats[title]["MaxFreq"] = max_single

    # Compute Dist% and Rndm
    for title in stats:
        freq = stats[title]["Freq"]
        maxFreq = stats[title]["MaxFreq"]

        # Dist%: (Freq / numCards) / maxFreq
        # Somewhat arbitrary, placeholder
        distVal = freq / (numCards * 24) * 100
        stats[title]["Dist%"] = round(distVal, 3)

        # Rndm: (1 - (maxFreq / freq)) * numCards / 24 
        # Somewhat arbitrary, placeholder
        if freq > 0:  # Avoid division by zero
            rndmVal =  (1 - (maxFreq / freq)) * numCards / 24
            stats[title]["Rndm"] = round(rndmVal, 3)

    return stats

def drawFrequencyTable(canvasObj, stats, pageWidth, pageHeight):
    """
    Creates a seven-column table, aligned left:
      1) Song/Artist (stacked)
      2) Freq
      3) Pos.F
      4) Dup
      5) MaxF
      6) Dist%
      7) Rndm

    If the content exceeds one page, it spills onto new pages.
    """
    # Sort the songs alphabetically
    sortedTitles = sorted(stats.keys(), key=str.lower)

    # Margins
    leftMargin = 0.75 * inch
    rightMargin = 0.75 * inch
    topMargin = pageHeight - 1.5 * inch
    bottomMargin = 1.0 * inch
    usableWidth = pageWidth - leftMargin - rightMargin

    # Column widths (Song/Artist wide, numeric columns thinner)
    colWidths = [
        3.0 * inch,  # Song + Artist
        0.6 * inch,  # Freq
        0.6 * inch,  # Pos.F
        0.5 * inch,  # Dup
        0.7 * inch,  # MaxF
        0.8 * inch,  # Dist%
        0.8 * inch   # Rndm
    ]
    totalTableWidth = sum(colWidths)
    tableLeftX = leftMargin + (usableWidth - totalTableWidth) / 2.0

    # Header row
    headers = ["Song/Artist", "Freq", "Pos.F", "Dup", "MaxF", "Dist%", "Rndm"]
    headerFontSize = 12
    bodyFontSize = 10
    smallArtistFontSize = 8
    lineSpacing = 3
    rowHeight = 0.4 * inch

    # Draw header
    canvasObj.setFont("Helvetica-Bold", headerFontSize)
    currentY = topMargin
    xPos = tableLeftX
    for i, colName in enumerate(headers):
        canvasObj.drawString(xPos + 5, currentY, colName)
        xPos += colWidths[i]
    currentY -= rowHeight

    # Fill in rows
    for title in sortedTitles:
        # If near bottom, go to new page + re-draw header
        if currentY <= bottomMargin:
            canvasObj.showPage()
            canvasObj.setFont("Helvetica-Bold", headerFontSize)
            currentY = topMargin
            xPos = tableLeftX
            for i, colName in enumerate(headers):
                canvasObj.drawString(xPos + 5, currentY, colName)
                xPos += colWidths[i]
            currentY -= rowHeight

        rowData = stats[title]
        artist = rowData["Artist"]
        freqStr = str(rowData["Freq"])
        posFStr = str(rowData["PosFreq"])
        dupStr = str(rowData["Dup"])
        maxFStr = str(rowData["MaxFreq"])
        distStr = f'{rowData["Dist%"]:.2f}'
        rndmStr = f'{rowData["Rndm"]:.2f}'

        # Draw the Song + Artist (stacked)
        canvasObj.setFont("Helvetica-Bold", bodyFontSize)
        xPos = tableLeftX
        canvasObj.drawString(xPos + 5, currentY, title[:50])  # truncated to 50 chars
        canvasObj.setFont("Helvetica", smallArtistFontSize)
        canvasObj.drawString(xPos + 5, currentY - (bodyFontSize + lineSpacing), artist[:50])

        canvasObj.setFont("Helvetica", bodyFontSize)
        xPos += colWidths[0]

        # Column 2: Freq
        canvasObj.drawString(xPos + 5, currentY, freqStr)
        xPos += colWidths[1]

        # Column 3: Pos.F
        canvasObj.drawString(xPos + 5, currentY, posFStr)
        xPos += colWidths[2]

        # Column 4: Dup
        canvasObj.drawString(xPos + 5, currentY, dupStr)
        xPos += colWidths[3]

        # Column 5: MaxF
        canvasObj.drawString(xPos + 5, currentY, maxFStr)
        xPos += colWidths[4]

        # Column 6: Dist%
        canvasObj.drawString(xPos + 5, currentY, distStr)
        xPos += colWidths[5]

        # Column 7: Rndm
        canvasObj.drawString(xPos + 5, currentY, rndmStr)

        currentY -= rowHeight


def generateBingo(cards, fileName, pageTitle, numCards, showArtists=True):
    """
    Generates a single PDF with:
      1) Cover + Duplicate Detection Heatmap
      2) Frequency Analysis Table (7 columns)
      3) Bingo Cards
    """
    # 1) Duplicate heatmap
    heatMap = analyzeDuplicates(cards)
    heatMapImage = generateHeatmap(heatMap)
    heatMapReader = ImageReader(heatMapImage)

    # 2) Frequency stats
    stats = computeSongStats(cards, numCards)

    c = canvas.Canvas(fileName, pagesize=letter)
    pageWidth, pageHeight = letter

    # Cover page
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(pageWidth / 2, pageHeight - 1.5 * inch, "Spotify Playlist Bingo")
    c.setFont("Helvetica", 14)
    c.drawCentredString(pageWidth / 2, pageHeight - 2 * inch, "Frequency Cluster Analysis")

    # Draw heatmap
    heatMapWidth = 5 * inch
    heatMapHeight = 5 * inch
    c.drawImage(
        heatMapReader,
        (pageWidth - heatMapWidth) / 2,
        pageHeight - 2.5 * inch - heatMapHeight,
        width=heatMapWidth,
        height=heatMapHeight
    )

    description = """
    Frequency Cluster Analysis:

    This heatmap highlights positions in bingo cards where the same tracks 
    were detected most frequently among all. Higher values indicate more freq in 
    a particular grid position. The heatmap uses a coolwarm color scheme for 
    easy visualization.

    Each bingo card includes unique tracks, with a central 'FREE' space.
    """
    textObject = c.beginText(1 * inch, pageHeight - 2.5 * inch - heatMapHeight - 1.5 * inch)
    textObject.setFont("Helvetica", 10)
    for line in description.strip().split('\n'):
        textObject.textLine(line.strip())
    c.drawText(textObject)

    c.showPage()

    # Frequency Analysis Table page
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pageWidth / 2, pageHeight - 1 * inch, "Song Frequency Analysis")
    c.setFont("Helvetica", 10)
    drawFrequencyTable(c, stats, pageWidth, pageHeight)
    c.showPage()

    # 3) Bingo cards
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
                    fontSize, lineSpacing,
                    showArtists
                )
        c.showPage()

    c.save()

def main():
    st.title("Spotify Playlist Bingo Card Generator")
    st.write("Generate bingo cards, plus a styled frequency table, after all fields are filled.")

    defaultPlaylist = "https://open.spotify.com/playlist/2i52cVg3bFzOKCIJfymy4l"
    playlistUrl = st.text_input("Enter Spotify playlist URL", value=defaultPlaylist)

    defaultDelims = ["-", "(", "[", "<", ">", "\"", ":"]
    delimitersInput = st.text_input("Custom Delimiters (comma-separated)", value=", ".join(defaultDelims))
    delimiters = [d.strip() for d in delimitersInput.split(",") if d.strip()]

    trimFirst = st.checkbox("Trim all before the first delimiter?", value=True)
    numCards = st.number_input("Number of Bingo Cards:", min_value=32, value=32, step=32)

    pageTitle = st.text_input("Page Title for Each Card", value="Spotify Bingo Title")

    clientCredentials = st.text_input(
        "Enter Client Credentials (client_id<separator>client_secret)",
        help="Separate client_id and client_secret by any non-hexadecimal character."
    )
    
    # New Checkbox to toggle artist visibility
    showArtists = st.checkbox("Show Artist Names", value=True)

    # We use session_state to manage data across widget interactions
    if "uniqueTracks" not in st.session_state:
        st.session_state.uniqueTracks = None
    if "currentPlaylist" not in st.session_state:
        st.session_state.currentPlaylist = None

    clientId, clientSecret = None, None

    # Attempt to parse credentials only if user provided them
    if clientCredentials:
        if len(clientCredentials) < 20:
            # Possibly encoded credentials
            try:
                rVal = fromBase(clientCredentials)
                aVal, bVal = calcKey(rVal)
                k = aVal + '+' + bVal
                splitResult = re.split(r'[^0-9a-fA-F]', k)
            except:
                splitResult = re.split(r'[^0-9a-fA-F]', clientCredentials)
        else:
            splitResult = re.split(r'[^0-9a-fA-F]', clientCredentials)

        if len(splitResult) >= 2:
            clientId = splitResult[0]
            clientSecret = splitResult[1]

    # Condition to enable "Generate Bingo PDF" button:
    #   Must have a valid playlist URL + client credentials
    fields_filled = (
        playlistUrl and clientId and clientSecret and
        len(playlistUrl.strip()) > 0 and
        len(clientId.strip()) > 0 and
        len(clientSecret.strip()) > 0
    )

    generate_button = st.button("Generate Bingo PDF", disabled=not fields_filled)

    if generate_button and fields_filled:
        # Validate playlist ID
        playlistId = extractPlaylist(playlistUrl)
        if playlistId:
            # Re-fetch tracks if the playlist changed
            if playlistUrl != st.session_state.currentPlaylist:
                st.session_state.uniqueTracks = None
                st.session_state.currentPlaylist = playlistUrl

            # If we don't already have the tracks, fetch them
            if st.session_state.uniqueTracks is None:
                try:
                    sp = spotipy.Spotify(
                        auth_manager=SpotifyClientCredentials(
                            client_id=clientId,
                            client_secret=clientSecret
                        )
                    )
                except spotipy.SpotifyException as e:
                    st.error(f"Authentication failed: {e}")
                    st.stop()

                allTracks = fetchTracks(sp, playlistId)
                uniqueTracks = prepareTracks(allTracks, delimiters, trimFirst)
                st.session_state.uniqueTracks = uniqueTracks
            else:
                uniqueTracks = st.session_state.uniqueTracks

            if len(uniqueTracks) < 24:
                st.warning("The playlist must contain at least 24 distinct tracks.")
            else:
                cards = createCards(uniqueTracks, numCards)
                fileName = "bingo_cards.pdf"
                generateBingo(cards, fileName, pageTitle, numCards, showArtists)

                with open(fileName, "rb") as f:
                    pdfData = f.read()

                # Provide a download button
                st.download_button(
                    "Download Bingo PDF",
                    data=pdfData,
                    file_name=fileName,
                    mime="application/pdf"
                )

                # Option to re-generate
                if st.button("Regenerate"):
                    st.session_state.uniqueTracks = None
                    st.experimental_rerun()

        else:
            st.warning("Invalid playlist URL. Could not detect a valid playlist ID.")
    elif not fields_filled:
        st.info("Please provide a valid playlist URL and Spotify credentials to enable PDF generation.")


if __name__ == "__main__":
    main()
