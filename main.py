from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = 'tajny_klucz'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)


API_KEY = "f50a08ce-5116-4b61-b898-faf0a5a1450b"

def get_crypto_price(symbol):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    params = {
        'symbol': symbol,
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()['data'][symbol]['quote']['USD']['price']
    else:
        return None


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class WalletItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coin_symbol = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



with app.app_context():
    db.create_all()


@app.route('/')
def index():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {
        'start': '1',
        'limit': '10',
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY
    }

    try:
        response = requests.get(url, headers=headers, params=parameters)
        if response.status_code == 200:
            json_data = response.json()
            data = json_data.get('data', [])
        else:
            print("Błąd API:", response.status_code, response.text)
            data = []
    except Exception as e:
        print("Błąd pobierania API:", e)
        data = []

    return render_template('index.html', coins=data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Użytkownik już istnieje.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Rejestracja zakończona sukcesem. Zaloguj się.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('Nieprawidłowy login lub hasło.')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['user']).first()

    if request.method == 'POST':
        symbol = request.form['symbol'].upper()
        amount = float(request.form['amount'])
        item = WalletItem(coin_symbol=symbol, amount=amount, user_id=user.id)
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('dashboard'))

    wallet = WalletItem.query.filter_by(user_id=user.id).all()
    wallet_data = []
    total_value = 0

    for item in wallet:
        price = get_crypto_price(item.coin_symbol)
        if price:
            value = price * item.amount
            total_value += value
            wallet_data.append({
                'id': item.id,
                'symbol': item.coin_symbol,
                'amount': item.amount,
                'price': round(price, 2),
                'value': round(value, 2)
            })

    return render_template('dashboard.html', user=user.username, wallet=wallet_data, total_value=round(total_value, 2))

@app.route('/delete_wallet_item/<int:item_id>')
def delete_wallet_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    item = WalletItem.query.get_or_404(item_id)
    current_user = User.query.filter_by(username=session['user']).first()

    if item.user_id != current_user.id:
        return "Brak dostępu", 403

    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)