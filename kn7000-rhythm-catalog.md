---
layout: page
title: KN7000 Music Stylist Catalog
permalink: /kn7000-rhythm-catalog/
---

# Technics SX-KN7000 — built-in Music Stylist catalog

The complete list of the KN7000's built-in **Music Stylist** subcategories, recovered
directly from the program ROM. MUSIC STYLIST &rarr; MUSICAL CATEGORY and ORGAN STYLIST
(user's manual pp. 61–63) group their one-touch setups under these headings; the SKIP
buttons jump from one heading to the next.
The names live in a genre&rarr;subcategory table pair rooted at `StyleGenreTable`
(program-ROM `0x4873ACC0`), which the MUSICAL CATEGORY list box
(`AcCtgStyleListBoxProc`) walks. Each 8-byte genre entry points to a genre name
and to that genre's sub-table. Each sub-table entry points to a subcategory name and
to a list of four style numbers, ended by `0xFFFF`, which index the style records of
`StyleRecordTable` (`0x4873BEE8`); the 270 lists use every number from 0 to 1,079
exactly once. Under *Tonewheel Jazz*, for example, sit the styles *Swing Tonewheels*,
*Classic B3 Jazz*, *Block Chord Jazz* and *Straight Swingin*, as the
[ORGAN STYLIST screen]({{ site.baseurl }}/kn7000-table-rom/#the-ui-graphics-are-standard-jpegs)
shows. This page lists the subcategory names only. Extracted by walking the table
structure; **270 subcategories across 11 genres, four styles each (1,080 styles)**
(`tools/kn7000_style_catalog.py` in this repository walks it).

These are not the instrument's built-in rhythms. The user's manual (p. 207) lists
220 rhythms × 4 variations in 14 rhythm groups, whose names come from a
different, still-undumped resource; see
[How the rhythm menu resolves a style name]({{ site.baseurl }}/kn7000-initial-data/#how-the-rhythm-menu-resolves-a-style-name).

## Rock & Pop (58 subcategories)

- Disco Orchestra
- 60s Blues Rock
- 60s PopOrchestra
- Mersey Ballad
- Pacific Pop
- Spiritual Pop
- Pop Imagination
- 60s Soul
- Folk Rock
- Organ RockBallad
- UK Piano Legend
- Straight 8 Beat
- Dance Superstar
- Detroit Ballad
- EZ 16 Beat
- Chart 16
- Studio Pop
- King's Rock
- Let's Rock
- Rock Status
- Leroy's Band
- Cool Old Rock
- Blues Alley
- Heavy Shuffle
- Easy Rock
- Pop Girls
- 90s Top Ten
- 90s Rock & Roll
- Pop Shuffle
- Rock Gig
- Jazzy Grooves
- Pop Love Song
- Blues For Ray
- Superstar Ballad
- 16Beat Standards
- SupergroupBallad
- 80s Movie Ballad
- 50s Smooch Dance
- Twisters
- Ageless 8 Beat
- Evergreen 16
- Chart Reggae
- Piano Blues
- West Coast Funk
- West Indies Cool
- Slow and Flowery
- Funky Town
- Euro Pop/Rock
- Soft Rock
- Poet Rock
- Uptown Swing
- Hip & Smooth
- Ageless 16 Beat
- Pop16
- Slow Feelings
- Groovy 90s
- Yuppie Beat
- Pop Ballad Boys

## Easy Listening (25 subcategories)

- Sweet Pop
- Song Contest
- Ballad Orchestra
- 16 Beat Grooves
- Easy 16 Ballad
- Yesteryear
- SavedByTheBallad
- Dreamy Ballad
- Fifties Smooch
- Daydreams
- Slow & Easy
- Pop Piano Star
- Candlelight Fox
- Hollywood Charm
- Ballad Producer
- Slow Oldies
- Schlager Romance
- Golden Oldie
- Easy Swing Pop
- Cool Waltz
- Smiling 70s
- Chill Out Corner
- OldFashion Dance
- Latin Drawbars
- 70s Covers Band

## Soul & Gospel (19 subcategories)

- 70s Detroit Pop
- Soulful Organ
- Soul Club
- Pop Soul
- Sweet Soul
- Cool & Groovy
- Soul Groove
- 70s Revival
- Sunday Morning
- Sing To The Lord
- Pop Spiritual
- Modern Spirit
- Funky R&B
- Soul Jazz
- Waltzing Church
- Morning Blues
- Soulfood To Go
- Funk 4 Experts
- 70s Funk

## Dance Pop (16 subcategories)

- 90s Boy Groups
- Electric World
- Barbie's Home
- Drumming Beats
- Hip Dance
- Dreamland
- Believe This
- London Subway
- Hip Stuff
- Golden Dancing
- Street Dance
- Retro Disco
- Dance Latin
- The Big Hit
- Steamy Funk
- Hip Club Mixes

## Latin & World (27 subcategories)

- Latino Pop
- Smooth Latin
- Latin Party
- Uptown Cha Cha
- Special Latin
- Jazz Latin
- Acoustic Bossa
- Ballroom Beguine
- Rhumba Party
- Bolero Dance
- Latin Dance Band
- Samba Holiday
- Ballroom Samba
- Amigo Beats
- Latin Tango
- Mexicana
- Dance Lambada
- Greek Dance
- Scottish Dance
- Cumbia Band
- Cut Time Bossa
- Talempong World
- Romantic Waltz
- Dangdut Special
- Indonesian Folk
- Radio Bossa
- Bossa Guitars

## Jazz & Swing (28 subcategories)

- Blue Notes
- LoungeLizardJazz
- Jazz Harmonicity
- Acapella Group
- Manhattan Voices
- Big Band Stomp
- Swing Counting
- Big Band Dance
- Big Band Smooch
- Moonlight Band
- Late Night Jazz
- RatPack LoveSong
- 12 Bar Blues
- Cocktail Jazz
- Scatty Singers
- The Swing Era
- NightClubCabaret
- Bourbon Street
- I Got The Blues
- Casino Show
- Lounge Act
- Tower Of Jazz
- West Coast Jazz
- Sweet & Swingy
- 80s Jazz Band
- Hotelbar Jazz
- Jazz Club Jam
- Jazz Accordion

## Show & Ballroom (29 subcategories)

- Dinner Dance
- Swinging Bert
- Ribbon Foxtrot
- 60s Foxtrot
- Ballroom Dance
- Slow Latin Dance
- Slow Waltzing
- Fast Ballroom
- Euro Tango
- Vienna Ballroom
- Sci-fi Adventure
- Spy Superstar
- Cartoon Ballad
- ProductionNumber
- Choreographic
- Tap Dance Legend
- Legendary Ballad
- Movie Melodrama
- Swing Production
- Breakfast Waltz
- Modern Musical
- Show Tunes
- Show Overture
- Starry Eyed
- Rags to Jazz
- Vegas Cabaret
- Music Hall Joe
- Ballroom Waltz
- Strict Tempo

## Trad & Folk (17 subcategories)

- Standard 3/4
- Franco Americana
- Marching Band
- Stadium Events
- OktoberFest
- Mountain Music
- Zillertal
- Parisian Dance
- Bier Hall
- French Chanson
- Vienna Dance
- Island Dreams
- Waikiki Dance
- Gypsy Party
- Italian Night
- Ceilidh Band
- Modern Folk

## Party Music (12 subcategories)

- Ballermann
- Party R&B
- Party Shuffle
- Party On!
- Summer Fun
- Party Highlights
- German Holiday
- The Last Band
- Samba Nights
- Organ Party
- Party Pop Organ
- Accordion Party

## Country (12 subcategories)

- Barn Dance
- Country Festival
- Nashville Blues
- Country Hit
- 70s Folk
- Foxtrot Country
- Southern Shuffle
- Very Country
- KentuckyLoveSong
- Southern Waltz
- Bluegrass City
- Country Dance

## Organ Stylist (27 subcategories)

- Tonewheel Jazz
- Organ A-Go-Go
- Organ Bossanova
- Latin Holiday
- Samba PartyPiece
- Show Organist
- Love Song Tabs
- NostalgicFoxtrot
- Organ Waltz
- Cinema Organist
- Ballroom Tabs
- Home Organ Latin
- Seaside Ballroom
- Organ Blue Notes
- Waller Wurly
- Home Organ Waltz
- Home Organ Swing
- Time For The T
- Picture Palace
- TheatreOrgan 3/4
- Organ Showcase
- B3 For The 90s
- Tango Organist
- Latin Rhythm Box
- Hula Organ
- Party Tabs
- Jive Organist

*Total: 270 built-in Music Stylist subcategories across 11 genres, each holding four styles (1,080 in all). Names are reproduced verbatim
(fixed 16-character fields in ROM).*