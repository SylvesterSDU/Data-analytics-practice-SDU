"""SQL part 1: CS50 songs and movies."""
from .common import Num, Text, question, sql, val

S, M = "songs.db", "movies.zip"


def song(n, topic, minutes, prompt, checks, note=None):
    question(f"SQL-SNG-{n:02d}", "SQL", "Songs", S, topic, minutes, prompt, checks, note)


def movie(n, topic, minutes, prompt, checks, note=None):
    question(f"SQL-MOV-{n:02d}", "SQL", "Movies", M, topic, minutes, prompt, checks,
             note or "movies.zip contains movies.db (about 70 MB). Unzip it before opening.")


top3 = sql(S, "SELECT name FROM songs ORDER BY duration_ms DESC LIMIT 3")
song(1, "Sort & top-N", 2,
     "List the names of the three longest songs, longest first. What is the first and the third name?",
     [Text("First song", top3[0][0]), Text("Third song", top3[2][0],
                                            mistakes=[(sql(S, "SELECT name FROM songs ORDER BY duration_ms LIMIT 3")[2][0],
                                                       "That is the third shortest. Sort with DESC.")])])

dev = "SELECT COUNT(*) FROM songs WHERE danceability > 0.6 AND energy > 0.6 AND valence > 0.6"
song(2, "Filter & count", 2,
     "List the names of songs with danceability, energy and valence all greater than 0.6. How many songs are listed?",
     [Num("Number of songs", val(S, dev),
          mistakes=[(val(S, "SELECT COUNT(*) FROM songs WHERE danceability > 0.6 OR energy > 0.6 OR valence > 0.6"),
                     "You used OR. All three conditions must hold, so use AND.")])])

song(3, "Group & aggregate", 2,
     "What is the average tempo of all songs? Give two decimals.",
     [Num("Average tempo", val(S, "SELECT AVG(tempo) FROM songs"), 2)])

drake = sql(S, "SELECT s.name FROM songs s JOIN artists a ON a.id = s.artist_id WHERE a.name = 'Drake' ORDER BY s.name")
song(4, "Joins & lookups", 3,
     "List the names of songs by Drake, without assuming Drake's artist_id. How many songs are there, and which comes first alphabetically?",
     [Num("Number of songs", len(drake)), Text("First alphabetically", drake[0][0])])

pm = sql(S, "SELECT AVG(energy), COUNT(*) FROM songs WHERE artist_id = (SELECT id FROM artists WHERE name = 'Post Malone')", one=True)
song(5, "Multi-step queries", 3,
     "What is the average energy of songs by Post Malone? Use a subquery or join rather than a hard-coded artist_id. Give three decimals.",
     [Num("Average energy", pm[0], 3, mistakes=[(val(S, "SELECT AVG(energy) FROM songs"), "That is the average of all songs. Filter to Post Malone.")])])

top_art = sql(S, "SELECT a.name, COUNT(*) c FROM songs s JOIN artists a ON a.id = s.artist_id GROUP BY a.id ORDER BY c DESC, a.name")
song(6, "Group & aggregate", 3,
     "Which artists have the most songs in the database? Give the highest number of songs per artist and how many artists share that number. How many songs have names that include 'feat.'?",
     [Num("Highest number of songs by one artist", top_art[0][1]),
      Num("Artists with that number", sum(1 for r in top_art if r[1] == top_art[0][1])),
      Num("Songs with 'feat.' in the name", val(S, "SELECT COUNT(*) FROM songs WHERE name LIKE '%feat.%'"))])

movie(1, "Filter & count", 2,
      "List the titles of all movies released in 2007. How many rows does your result have?",
      [Num("Number of movies", val(M, "SELECT COUNT(*) FROM movies WHERE year = 2007"))])

movie(2, "Filter & count", 2,
      "What is Johnny Depp's birth year? And how many movies have an IMDb rating greater than 9.0?",
      [Num("Birth year", val(M, "SELECT birth FROM people WHERE name = 'Johnny Depp'")),
       Num("Movies rated above 9.0", val(M, "SELECT COUNT(*) FROM ratings WHERE rating > 9.0"),
           mistakes=[(val(M, "SELECT COUNT(*) FROM ratings WHERE rating >= 9.0"), "You included movies rated exactly 9.0. The question says greater than (>).")])])

after = sql(M, "SELECT title FROM movies WHERE year >= 2017 ORDER BY title")
movie(3, "Sort & top-N", 3,
      "List the titles of all movies released in 2017 or later, in alphabetical order. How many rows, and what is the first title?",
      [Num("Number of movies", len(after),
           mistakes=[(val(M, "SELECT COUNT(*) FROM movies WHERE year > 2017"), "You excluded 2017. Use >= 2017.")]),
       Text("First title", after[0][0])])

ts = sql(M, "SELECT title, year FROM movies WHERE title LIKE 'Toy Story%' ORDER BY year")
movie(4, "Text functions & extraction", 2,
      "List the titles and release years of all Toy Story movies (titles beginning with 'Toy Story') in chronological order. How many rows, and what is the year of the last one?",
      [Num("Number of movies", len(ts),
           mistakes=[(val(M, "SELECT COUNT(*) FROM movies WHERE title LIKE '%Toy Story%'"),
                      "You matched 'Toy Story' anywhere in the title. Titles must begin with it: LIKE 'Toy Story%'.")]),
       Num("Year of the last movie", ts[-1][1])])

movie(5, "Joins & lookups", 3,
      "What is the average rating of all movies released in 2013? Give two decimals. How many 2013 movies have a rating?",
      [Num("Average rating", val(M, "SELECT AVG(rating) FROM ratings JOIN movies ON movies.id = ratings.movie_id WHERE year = 2013"), 2),
       Num("2013 movies with a rating", val(M, "SELECT COUNT(*) FROM ratings JOIN movies ON movies.id = ratings.movie_id WHERE year = 2013"),
           mistakes=[(val(M, "SELECT COUNT(*) FROM movies WHERE year = 2013"), "That counts all 2013 movies, including unrated ones. Join to ratings.")])])

y11 = sql(M, "SELECT title, rating FROM movies JOIN ratings ON movies.id = ratings.movie_id WHERE year = 2011 ORDER BY rating DESC, title")
movie(6, "Sort & top-N", 3,
      "List all 2011 movies with their ratings, highest rating first; ties sorted alphabetically by title. Leave out movies without a rating. How many rows, and what is the second title?",
      [Num("Number of rows", len(y11),
           mistakes=[(val(M, "SELECT COUNT(*) FROM movies WHERE year = 2011"), "Unrated movies are included. Use an inner JOIN to ratings.")]),
       Text("Second title", y11[1][0])])

hp = "(SELECT id FROM movies WHERE title = 'Harry Potter and the Sorcerer''s Stone')"
movie(7, "Joins & lookups", 3,
      "List the names of all people who starred in Harry Potter and the Sorcerer's Stone. How many names are listed?",
      [Num("Number of people", val(M, f"SELECT COUNT(*) FROM people WHERE id IN (SELECT person_id FROM stars WHERE movie_id = {hp})"))])

movie(8, "Joins & lookups", 4,
      "List the names of all people who starred in a movie released in 2003, ordered by birth year. Each person should appear only once. How many rows?",
      [Num("Number of people", val(M, "SELECT COUNT(DISTINCT person_id) FROM stars JOIN movies ON movies.id = stars.movie_id WHERE year = 2003"),
           mistakes=[(val(M, "SELECT COUNT(*) FROM stars JOIN movies ON movies.id = stars.movie_id WHERE year = 2003"),
                      "Some people starred in several 2003 movies. Use DISTINCT.")])])

movie(9, "Joins & lookups", 4,
      "List the names of all people who directed a movie with a rating of at least 8.0. Each person only once. How many rows?",
      [Num("Number of directors", val(M, "SELECT COUNT(DISTINCT d.person_id) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating >= 8.0"),
           mistakes=[(val(M, "SELECT COUNT(*) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating >= 8.0"),
                      "Directors with several qualifying movies are counted twice. Use DISTINCT."),
                     (val(M, "SELECT COUNT(DISTINCT d.person_id) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating > 8.0"),
                      "At least 8.0 means >= 8.0.")])])

jd = "(SELECT id FROM people WHERE name = 'Johnny Depp')"
hbc = "(SELECT id FROM people WHERE name = 'Helena Bonham Carter')"
hb = sql(M, f"SELECT title FROM movies JOIN ratings ON movies.id = ratings.movie_id JOIN stars ON stars.movie_id = movies.id WHERE stars.person_id = {hbc} ORDER BY rating DESC, title LIMIT 5")
movie(10, "Multi-step queries", 4,
      "List the titles of all movies starring both Johnny Depp and Helena Bonham Carter. How many are there? Also: what is the highest-rated movie Helena Bonham Carter starred in (ties: first alphabetically)?",
      [Num("Movies with both actors", val(M, f"SELECT COUNT(*) FROM (SELECT movie_id FROM stars WHERE person_id = {jd} INTERSECT SELECT movie_id FROM stars WHERE person_id = {hbc})")),
       Text("Highest-rated Helena Bonham Carter movie", hb[0][0])])

kb = "(SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958)"
all_kb = "(SELECT id FROM people WHERE name = 'Kevin Bacon')"
movie(11, "Multi-step queries", 5,
      "List the names of all people who starred in a movie with Kevin Bacon (the one born in 1958), excluding Kevin Bacon himself. Each person only once. How many rows?",
      [Num("Number of people", val(M, f"SELECT COUNT(DISTINCT person_id) FROM stars WHERE movie_id IN (SELECT movie_id FROM stars WHERE person_id = {kb}) AND person_id <> {kb}"),
           mistakes=[(val(M, f"SELECT COUNT(DISTINCT person_id) FROM stars WHERE movie_id IN (SELECT movie_id FROM stars WHERE person_id = {kb})"),
                      "You included Kevin Bacon himself. Exclude his id."),
                     (val(M, f"SELECT COUNT(DISTINCT person_id) FROM stars WHERE movie_id IN (SELECT movie_id FROM stars WHERE person_id IN {all_kb}) AND person_id NOT IN {all_kb}"),
                      "There are two people named Kevin Bacon. Filter on birth = 1958."),
                     (val(M, f"SELECT COUNT(*) FROM stars WHERE movie_id IN (SELECT movie_id FROM stars WHERE person_id = {kb}) AND person_id <> {kb}"),
                      "Some co-stars appear in several of his movies. Use DISTINCT.")])])
