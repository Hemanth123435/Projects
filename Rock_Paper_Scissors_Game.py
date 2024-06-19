from http.server import HTTPServer, BaseHTTPRequestHandler
import random
import urllib.parse

html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rock Paper Scissors Game</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f8f9fa;
    }
    .container {
      text-align: center;
      margin-top: 50px;
    }
    .btn-choice {
      font-size: 1.5em;
      margin: 10px;
      padding: 10px 20px;
    }
    #result {
      font-size: 1.5em;
      font-weight: bold;
      margin-top: 20px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Rock Paper Scissors Game</h1>
    <form id="game-form" action="/" method="post">
      <div class="btn-group btn-group-toggle" data-toggle="buttons">
        <label class="btn btn-primary">
          <input type="radio" name="choice" value="rock" autocomplete="off"> Rock
        </label>
        <label class="btn btn-primary">
          <input type="radio" name="choice" value="paper" autocomplete="off"> Paper
        </label>
        <label class="btn btn-primary">
          <input type="radio" name="choice" value="scissors" autocomplete="off"> Scissors
        </label>
      </div>
      <br><br>
      <button type="submit" class="btn btn-primary">Play</button>
    </form>
    <div id="result"></div>
  </div>
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.3/dist/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  <script>
    document.getElementById('game-form').addEventListener('submit', function(event) {
      event.preventDefault();
      var formData = new FormData(event.target);
      var userChoice = formData.get('choice');
      playGame(userChoice);
    });

    function playGame(userChoice) {
      var choices = ['rock', 'paper', 'scissors'];
      var computerChoice = choices[Math.floor(Math.random() * choices.length)];

      var result = determineWinner(userChoice, computerChoice);
      displayResult(result, userChoice, computerChoice);
    }

    function determineWinner(userChoice, computerChoice) {
      if (userChoice === computerChoice) {
        return 'tie';
      } else if (
        (userChoice === 'rock' && computerChoice === 'scissors') ||
        (userChoice === 'paper' && computerChoice === 'rock') ||
        (userChoice === 'scissors' && computerChoice === 'paper')
      ) {
        return 'user';
      } else {
        return 'computer';
      }
    }

    function displayResult(result, userChoice, computerChoice) {
      var resultDiv = document.getElementById('result');
      var resultText = '';

      switch (result) {
        case 'user':
          resultText = 'You chose ' + userChoice + '. Computer chose ' + computerChoice + '. You win!';
          break;
        case 'computer':
          resultText = 'You chose ' + userChoice + '. Computer chose ' + computerChoice + '. Computer wins!';
          break;
        case 'tie':
          resultText = 'You both chose ' + userChoice + '. It\'s a tie!';
          break;
        default:
          resultText = 'Something went wrong.';
          break;
      }

      resultDiv.innerHTML = resultText;
    }
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
        elif self.path.endswith('.png'):
            try:
                with open(self.path[1:], 'rb') as file:
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(file.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'404 Not Found')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

    def do_POST(self):
        if self.path == '/':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            
            if 'choice' in parsed_data:
                user_choice = parsed_data['choice'][0]
                computer_choice = random.choice(['rock', 'paper', 'scissors'])
                result = determine_winner(user_choice, computer_choice)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><body>'.encode())
                self.wfile.write('<h1>Result</h1>'.encode())
                self.wfile.write(f'<p>You chose {user_choice}. Computer chose {computer_choice}.</p>'.encode())
                self.wfile.write(f'<p>{result}</p>'.encode())
                self.wfile.write('</body></html>'.encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Bad request - choice parameter is missing.')

def determine_winner(user_choice, computer_choice):
    if user_choice == computer_choice:
        return "It's a tie!"
    elif (user_choice == 'rock' and computer_choice == 'scissors') or \
         (user_choice == 'paper' and computer_choice == 'rock') or \
         (user_choice == 'scissors' and computer_choice == 'paper'):
        return "You win!"
    else:
        return "Computer wins!"

def main():
    server = HTTPServer(('localhost', 8000), MyHandler)
    print('Server running at http://localhost:8000/')
    server.serve_forever()

if __name__ == '__main__':
    main()
