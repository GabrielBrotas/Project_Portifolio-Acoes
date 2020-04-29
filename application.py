
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
# app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    users = db.execute('SELECT cash FROM users WHERE id = :user_id', user_id=session['user_id'])
     
    # nesse ponto criar uma TABLE para onde as acoes vao ficar armazenadas, 'CREATE TABLE IF NOT EXISTS 'transactions' ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'user_id' INTEGER NOT NULL, 'symbol' TEXT NOT NULL, 'shares' INTEGER NOT NULL, 'price_per_share' REAL NOT NULL, 'created_at'  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP  );'
    
    stocks = db.execute('SELECT symbol, SUM(shares) as total_shares, price_per_share FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares > 0', user_id=session['user_id'])


    
    quotes = {}
    total = 0

    for stock in stocks:
        quote = lookup(stock['symbol'])
        quotes[stock['symbol']] = quote
        
        db.execute('UPDATE transactions SET price_per_share = :price_per_share WHERE user_id = :user_id AND symbol = :symbol', price_per_share=quote['price'], user_id=session['user_id'], symbol=stock['symbol'])
        
        total += quote['price'] * stock['total_shares']

    cash_remaining = users[0]['cash']
    cash_remaining_formated = f'{cash_remaining:.2f}'

    total += cash_remaining
    total_formated = f'{total:.2f}'

    return render_template('portfolio.html', quotes=quotes, stocks=stocks, total=total_formated, cash_remaining=cash_remaining_formated)




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Vai criar um dicionario com 'name', 'price e 'symbol' da acao
        quote = lookup(request.form.get("symbol"))
        
        # verificar se o simbolo existe...
        if quote == None:
            return apology("simbolo invalido", 400)

        # verificar se a quantidade é positiva
        try:
            shares = int(request.form.get('shares'))
        
        except:
            return apology('a quantidade deve ser positiva',400)
        
        # verificar se o valor a quantidade é 0
        if shares <=0:
            return apology('a quantidave deve ser maior e igual que 0', 400)
        
        # pegar o banco de dados para consultar o usuario
        rows = db.execute('SELECT cash FROM users WHERE id = :user_id', user_id=session['user_id'])

        # quanto dinheiro ainda tem na conta
        cash_remaining = rows[0]['cash']

        # valor por acao
        price_per_share = quote['price']

        # calcular o preço da açao * a quantidade solicitada
        total_price = price_per_share * shares

        if total_price > cash_remaining:
            return apology('saldo insuficiente, adicione fundos na sua conta')

        # se passar por todas as condicoes entao...

        # atualizar o valor da conta subtraindo pelo preço total da ação
        db.execute('UPDATE users SET cash = cash - :price WHERE id = :user_id', price=total_price, user_id=session['user_id'])

        # adicionar acoes na carteira do usuario
        db.execute('INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES (:user_id, :symbol, :shares, :price)', user_id=session['user_id'], symbol=quote['symbol'], shares=shares, price=price_per_share)

        flash("Comprado!")
        
        return redirect('/')

    else:

        return render_template('buy.html')




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    history = db.execute('SELECT * FROM transactions WHERE user_id = :user_id ORDER BY created_at DESC;', user_id=session['user_id'])
    
    return render_template('history.html', history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method =='POST':
    
        if not request.form.get('symbol'):
            return apology('Informe um valor', 400)

        quote = lookup(request.form.get('symbol'))

        if quote == None:
            return apology('Informa um simbolo valido!', 400)

        symbol = request.form.get('symbol')
        price = quote['price']
        name = quote['name']     

        return render_template('quoted.html', symbol=symbol, price=price, name=name)

    else:

        return render_template('quote.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)
        
        elif request.form.get('password') != request.form.get('confirmation'):
            return apology('senhas divergenetes')
        
        username = username=request.form.get("username")

        checkUsername = db.execute('SELECT username FROM users WHERE username = ?;', username)
        if len(checkUsername) != 0:
            return apology('nome já existe, escolha outro!')

        hash = generate_password_hash(request.form.get("password"))

        new_user_id = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=username, hash=hash)

        session['user_id'] = new_user_id

        flash("Registrado!")

        return redirect('/')

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":

        # pegar a acao
        quote = lookup(request.form.get('symbol'))

        # condicoes...
        if quote == None:
            return apology('Simbolo invalido', 400)
        
        try:
            # quantidade solicitada para venda
            shares = int(request.form.get('shares'))

        except:
            return apology('a quantidade deve ser positiva', 400)
        
        if shares <=0:
            return apology('a quantidade deve ser maior que 0', 400)

        # pegar acao que vai vender
        stock = db.execute('SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id AND symbol = :symbol GROUP BY symbol', user_id=session['user_id'], symbol=request.form.get('symbol'))

        if len(stock) != 1 or stock[0]['total_shares'] <=0 or stock[0]['total_shares'] < shares: 
            return apology('Voce nao pode vender menos que 0 ou mais do que possui!', 400)

        # pegar dados do user_id

        price_per_share = quote['price']

        total_price = price_per_share * shares

        
        # atualizar dados
        db.execute('UPDATE users SET cash = cash + :price WHERE id = :user_id', price=total_price, user_id=session['user_id'])

        db.execute('INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES (:user_id, :symbol, :shares, :price_per_share)', user_id=session['user_id'], symbol=request.form.get('symbol'), shares=-shares, price_per_share=price_per_share)

        flash('Vendido')

        return redirect('/')
    
    else:
        stocks = db.execute('SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares > 0;', user_id=session['user_id'])
        
        return render_template('sell.html', stocks=stocks)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


app.run()
