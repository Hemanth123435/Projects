from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import psycopg2
from psycopg2 import sql

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "hemanthram143"
DB_HOST = "localhost"
DB_PORT = "5432"

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    print("Connected to database.")
    cursor = conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS books (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        genre TEXT NOT NULL
    );
    """
    cursor.execute(create_table_query)
    print("Table 'books' created successfully.")
    initial_books = [
        ("To Kill a Mockingbird", "Harper Lee", 1960, "Fiction"),
    ]
    insert_query = sql.SQL("INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s)")
    for book in initial_books:
        cursor.execute(insert_query, book)
    conn.commit()
    print("Sample data inserted into 'books' table.")
except psycopg2.Error as e:
    print("Error connecting to PostgreSQL:", e)

html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book Collection Manager</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f8f9fa;
      padding: 20px;
    }
    .container {
      max-width: 800px;
      margin: auto;
    }
    h1 {
      text-align: center;
      margin-bottom: 20px;
    }
    .form-group {
      margin-bottom: 20px;
    }
    .btn-add {
      margin-top: 10px;
    }
    .book-list {
      margin-top: 30px;
    }
    .book-item {
      border: 1px solid #ccc;
      padding: 10px;
      margin-bottom: 10px;
      position: relative;
    }
    .btn-delete {
      position: absolute;
      top: 10px;
      right: 10px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Book Collection Manager</h1>
    <form id="add-form" action="/add" method="post">
      <div class="form-group">
        <label for="title">Title:</label>
        <input type="text" id="title" name="title" class="form-control" required>
      </div>
      <div class="form-group">
        <label for="author">Author:</label>
        <input type="text" id="author" name="author" class="form-control" required>
      </div>
      <div class="form-group">
        <label for="year">Year:</label>
        <input type="number" id="year" name="year" class="form-control" required>
      </div>
      <div class="form-group">
        <label for="genre">Genre:</label>
        <input type="text" id="genre" name="genre" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary btn-add">Add Book</button>
    </form>
    
    <div class="book-list">
      <h2>Book Collection</h2>
      <div id="books"></div>
    </div>
  </div>
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.3/dist/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  
  <script>
    function loadBooks() {
      fetch('/books.json')
        .then(response => response.json())
        .then(data => {
          const booksContainer = document.getElementById('books');
          booksContainer.innerHTML = '';
          data.forEach(book => {
            const bookItem = document.createElement('div');
            bookItem.classList.add('book-item');
            bookItem.innerHTML = `
              <h3>${book.title}</h3>
              <p><strong>Author:</strong> ${book.author}</p>
              <p><strong>Year:</strong> ${book.year}</p>
              <p><strong>Genre:</strong> ${book.genre}</p>
              <button class="btn btn-danger btn-delete" data-id="${book.id}">Delete</button>
            `;
            booksContainer.appendChild(bookItem);
          });
          document.querySelectorAll('.btn-delete').forEach(button => {
            button.addEventListener('click', () => {
              const bookId = button.getAttribute('data-id');
              deleteBook(bookId);
            });
          });
        });
    }

    function deleteBook(bookId) {
      fetch(`/delete?id=${bookId}`, { method: 'DELETE' })
        .then(response => {
          if (response.ok) {
            loadBooks();
          } else {
            alert('Failed to delete book.');
          }
        });
    }

    loadBooks();
  </script>
</body>
</html>
'''

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_template.encode())
        elif self.path == '/books.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_books_from_db()).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

    def do_POST(self):
        if self.path == '/add':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            
            if 'title' in parsed_data and 'author' in parsed_data and 'year' in parsed_data and 'genre' in parsed_data:
                title = parsed_data['title'][0]
                author = parsed_data['author'][0]
                year = int(parsed_data['year'][0])
                genre = parsed_data['genre'][0]
                add_book_to_db(title, author, year, genre)
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Bad request - missing parameters')

    def do_DELETE(self):
        if self.path.startswith('/delete'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if 'id' in query_components:
                book_id = int(query_components['id'][0])
                delete_book_from_db(book_id)
                self.send_response(200)
            else:
                self.send_response(400)
            self.end_headers()

def add_book_to_db(title, author, year, genre):
    cursor.execute('''
        INSERT INTO books (title, author, year, genre)
        VALUES (%s, %s, %s, %s)
    ''', (title, author, year, genre))
    conn.commit()

def get_books_from_db():
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    return [{'id': book[0], 'title': book[1], 'author': book[2], 'year': book[3], 'genre': book[4]} for book in books]

def delete_book_from_db(book_id):
    cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
    conn.commit()

def main():
    server = HTTPServer(('localhost', 8000), MyHandler)
    print('Server running at http://localhost:8000/')
    server.serve_forever()

if __name__ == '__main__':
    main()
